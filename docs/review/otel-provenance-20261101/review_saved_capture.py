"""Finish UI review of unchanged captured facts after a harness-only failure.

Native operations are not repeated. Join their saved HTTP evidence, load the same
recording through the real viewer and use its canonical timeline adapter.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from exercise_trial_ui import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    recording = json.loads((args.capture / "recording.json").read_text(encoding="utf-8"))
    original = json.loads((args.capture / "failure.json").read_text(encoding="utf-8"))
    assert not recording["gaps"]
    assert recording["producer_settlement"]["flushed"] is True
    comparisons = []
    for response in original["responses"]:
        matches = [
            e["id"]
            for e in recording["events"]
            if e.get("trace", {}).get("trace_id") == response["trace_id"]
            and e["phase"] == "return"
            and e.get("inputs", {}).get("path") == response["path"]
            and e.get("outputs", {}).get("status") == response["status"]
        ]
        comparisons.append({**response, "matching_event_ids": matches})
    assert len(comparisons) == 18 and all(
        len(row["matching_event_ids"]) == 1 for row in comparisons
    )
    write_json(args.out / "http-comparisons.json", comparisons)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=args.browser)
        try:
            page = browser.new_page(viewport={"width": 1520, "height": 1060})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.graph)
            page.wait_for_function(
                "typeof graphDebug !== 'undefined' && graphDebug.timeline?.geometry"
            )
            page.locator("#record-list").select_option(recording["id"])
            page.wait_for_function("graphDebug.timeline?.source === 'saved'")
            semantics = page.evaluate(
                """async id => {
                    const recording = await (await fetch('/api/recordings/' + id)).json();
                    const { boFacts } = await import('./replay-steps.js');
                    const { timeline } = await import('./recording.js');
                    const facts = boFacts(recording, timeline(recording));
                    return {
                        finalBusinessChanges: facts.changes.at(-1).filter(r => r.kind==='business'),
                        stateChanges: facts.changes.flat().filter(r => r.kind==='business'),
                        instances: recording.final.machine.configurations.map(c => ({
                            id:c.snapshot_instance, native:c.native_instance_id,
                            caller:c.attempt, state:c.phase
                        }))
                    };
                }""",
                recording["id"],
            )
            write_json(args.out / "state-instance-comparison.json", semantics)
            assert semantics["finalBusinessChanges"] == []
            # Two file approvals (two transitions each), delivered-share
            # activation/revoke (two), and pending-share revoke (one).
            assert len(semantics["stateChanges"]) == 7, semantics["stateChanges"]
            ids = [cfg["id"] for cfg in semantics["instances"]]
            assert len(ids) == 4 and len(set(ids)) == 4 and all(ids)
            assert {cfg["state"] for cfg in semantics["instances"]} == {"approved", "revoked_share"}
            page.locator(".trace-scope").select_option("all")
            page.locator("#replay-grain").select_option("events")
            if page.locator("#layered-toggle").get_attribute("aria-pressed") == "true":
                page.locator("#layered-toggle").click()
            canvas = page.locator("#recording-timeline canvas")
            canvas.focus()
            page.keyboard.press("End")
            page.wait_for_function(
                "graphDebug.view.replay?.event?.id === 'end' || graphDebug.timeline.eventId === 'end'"
            )
            timeline = page.evaluate("graphDebug.timeline")
            assert timeline["lifecycles"] and timeline["flows"] > 0
            page.screenshot(path=str(args.out / "05-recorded-2d.png"))
            page.locator("#layered-toggle").click()
            page.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
            assert page.evaluate("graphDebug.timeline.raw") == timeline["raw"]
            page.screenshot(path=str(args.out / "06-recorded-3d.png"))
            page.locator("#record-list").select_option("")
            page.wait_for_function("!graphDebug.view.replay")
            page.locator("#analysis-view").select_option("code")
            page.wait_for_function("graphDebug.view.code_structure?.loaded_nodes > 0")
            projection = page.evaluate(
                """() => ({
                nodes: [...graphDebug.graph.all.values()].map(n => ({
                    id:n.id, layer:n.layer, kind:n.kind, code_role:n.code_role,
                    data_role:n.data_role, source:n.source, semantic_role:n.semantic_role,
                    capture_owner_role:n.capture_owner_role, execution_role:n.execution_role,
                    origin:n.origin, reference_scope:n.reference_scope
                })), edges: graphDebug.graph.rawEdges,
                code_summary: Object.fromEntries(
                    ['loaded_nodes','total_nodes','loaded_edges','omitted_nodes','omitted_edges','boundary_nodes','errors','revision']
                    .map(k => [k, graphDebug.view.code_structure?.[k]]))
            })"""
            )
            write_json(args.out / "layer-projection.json", projection)
            page.locator("#analysis-view").select_option("overview")
            assert not errors
            result = {
                "passed": True,
                "graph": args.graph,
                "capture": args.capture.as_posix(),
                "recording": recording["id"],
                "build_id": recording["build_id"],
                "events": len(recording["events"]),
                "gaps": recording["gaps"],
                "http_comparisons": len(comparisons),
                "state_instances": len(ids),
                "state_changes": len(semantics["stateChanges"]),
                "false_final_changes": 0,
                "timeline": {
                    key: len(timeline[key]) if isinstance(timeline[key], list) else timeline[key]
                    for key in ("raw", "flows", "lifecycles", "rows")
                },
                "page_errors": errors,
                "scope": "Unchanged finite-flow recording; business pages closed after final action and actual queue settlement. Original harness failure is retained.",
            }
            write_json(args.out / "result.json", result)
            print(json.dumps(result))
        except BaseException as error:
            write_json(
                args.out / "failure.json",
                {"type": type(error).__name__, "message": str(error), "page_errors": errors},
            )
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
