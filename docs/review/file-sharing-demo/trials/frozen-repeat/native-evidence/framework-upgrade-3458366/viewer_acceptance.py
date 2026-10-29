"""Exercise native viewer fixes using real stopped evidence, never synthetic events."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
OUT = BASE / "browser-native"
GRAPH = "http://127.0.0.1:8841"
capture = json.loads((OUT / "capture-report.json").read_text(encoding="utf-8"))
assert capture["status"] == "captured"
recording = json.loads((OUT / "recording.json").read_text(encoding="utf-8"))
assert not recording["gaps"] and recording["status"] == "stopped"
report = {**capture, "status": "running", "checks": list(capture["checks"]),
          "page_errors": [], "console_errors": [], "viewer_source": "Native b78f03a assets; no shim."}
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
attempt = OUT / ("viewer-attempt-" + stamp + ".json")
original_preferences = json.loads((BASE / "preferences-original.json").read_text(encoding="utf-8"))
raw_path = ROOT / "bo_stategraph/data/recordings" / (recording["id"] + ".json")
raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
timeline_input = {key: recording[key] for key in ("events", "commands", "status", "started_at", "ended_at")}

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="no-preference")
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
            page.goto(GRAPH + "/graph", wait_until="domcontentloaded")
            expect(page.locator("#canvas-host canvas")).to_be_visible(timeout=20000)
            page.wait_for_function("document.querySelector('#semantic').children.length > 0", timeout=20000)
            before = page.request.get(GRAPH + "/api/view").json()
            assert before["binding_status"]["status"] == "current"
            assert before["manifest"]["build_id"] == recording["build_id"]
            count = len(before["events"])
            model = before["model"]
            policy_ids = [node["id"] for node in model["nodes"] if node.get("origin") == "policy-definition"]
            guards = [edge for edge in model["edges"] if edge.get("origin") == "policy-definition"
                      and edge["type"] == "guard" and edge["id"].startswith("policy:dependency:")]
            proof = page.evaluate("""async ({recording,model}) => {
                const {transferEdges,timeline}=await import('/recording.js');
                const all=new Map(model.nodes.map(n=>[n.id,n]));
                const edges=model.edges.filter(e=>e.origin==='policy-definition' && e.type==='guard')
                    .map(e=>({...e,members:[e]}));
                const byId=new Map(recording.events.map(e=>[e.id,e]));
                const rows=[];
                for(const event of recording.events){
                    if(!['all','any','not'].includes(all.get(event.node)?.operator))continue;
                    const actual=transferEdges(event,recording.events,edges,all);
                    const expected=edges.filter(edge=>edge.to===event.node && (event.depends||[]).some(dep=>{
                        const source=byId.get(dep.event);
                        return dep.type==='data' && source?.node===edge.from &&
                            source.inputs.bo_check===event.inputs.bo_check &&
                            source.inputs.bo_basis===event.inputs.bo_basis;
                    })).map(e=>e.id);
                    const observed=new Set(recording.events.filter(e=>e.inputs?.bo_check===event.inputs?.bo_check &&
                        e.inputs?.bo_basis===event.inputs?.bo_basis).map(e=>e.node));
                    const skipped=edges.filter(e=>e.to===event.node && !observed.has(e.from)).map(e=>e.from);
                    const forbidden=edges.filter(e=>e.to===event.node && skipped.includes(e.from)).map(e=>e.id);
                    rows.push({id:event.id,node:event.node,value:event.outputs.value,status:event.outputs.status,
                        check:event.inputs.bo_check,basis:event.inputs.bo_basis,actual,expected,skipped,forbidden});
                }
                return {rows,indices:Object.fromEntries(timeline(recording).map((e,i)=>[e.id,i]))};
            }""", {"recording": recording, "model": model})
            assert proof["rows"]
            report["native_rule_transfers"] = proof["rows"]
            for row in proof["rows"]:
                assert sorted(row["actual"]) == sorted(row["expected"]), row
                assert not set(row["actual"]) & set(row["forbidden"]), row
            positive = next(row for row in proof["rows"] if row["node"] == "policy:share_allowed"
                            and row["value"] is True and len(row["actual"]) == 3)
            negative = next(row for row in proof["rows"] if row["node"] == "policy:share_allowed"
                            and row["value"] is False and len(row["actual"]) == 1 and len(row["forbidden"]) == 2)
            report["native_rule_transfers"] = proof["rows"]
            report["positive_rule_witness"] = positive
            report["skipped_rule_witness"] = negative
            report["checks"].append("Native transferEdges matches actual Boolean data dependencies by explicit event/check/basis and excludes declared child rules that have no same-check execution or dependency. No skipped result event is invented.")

            page.locator("#record-list").select_option(recording["id"])
            expect(page.locator("#replay")).to_be_visible(timeout=15000)
            page.locator("#replay-grain").select_option("events")
            page.locator("#analysis-view").select_option("permission")
            if page.locator("#analysis-details").get_attribute("aria-pressed") != "true":
                page.locator("#analysis-details").click()
            page.locator("#expand").click()
            page.wait_for_function("document.querySelector('[data-node-id=\"policy:share_allowed\"]') !== null", timeout=20000)
            visible = page.locator("[data-node-id]").evaluate_all("nodes=>nodes.map(n=>n.dataset.nodeId)")
            assert set(policy_ids) <= set(visible), sorted(set(policy_ids) - set(visible))
            incoming = page.locator("[data-edge-id]").evaluate_all("nodes=>nodes.map(n=>({...n.dataset}))")
            for edge in guards:
                assert any(item["from"] == edge["from"] and item["to"] == edge["to"] for item in incoming), edge
            report["authorization_preset"] = {"visible_policy_nodes": policy_ids, "visible_guard_relations": len(guards)}
            report["checks"].append("The actual authorization preset renders every native policy node and declared Boolean guard relation.")

            def select_rule(witness):
                epoch = int(page.locator("#renderer").get_attribute("data-animation-epoch") or 0)
                page.locator("#replay-events").select_option(str(proof["indices"][witness["id"]]))
                expect(page.locator("#replay-position")).to_have_attribute("data-event-id", witness["id"])
                page.wait_for_function("epoch=>Number(document.querySelector('#renderer').dataset.animationEpoch)>epoch", arg=epoch, timeout=15000)
                animated = json.loads(page.locator("#renderer").get_attribute("data-animated-edges") or "[]")
                semantic = page.locator("[data-edge-id]").evaluate_all("nodes=>nodes.map(n=>({...n.dataset}))")
                by_id = {item["edgeId"]: item for item in semantic}
                actual_pairs = {(by_id[identity]["from"], by_id[identity]["to"])
                                for identity in animated if identity in by_id}
                expected_edges = [edge for edge in guards if edge["id"] in witness["actual"]]
                for edge in expected_edges:
                    assert (edge["from"], edge["to"]) in actual_pairs, (edge, animated, actual_pairs)
                for edge in guards:
                    if edge["id"] in witness["forbidden"]:
                        assert (edge["from"], edge["to"]) not in actual_pairs, (edge, actual_pairs)
                return {"event_id": witness["id"], "animated_edge_ids": animated,
                        "guard_pairs": sorted([list(pair) for pair in actual_pairs if pair[1] == witness["node"]]),
                        "animation_epoch": page.locator("#renderer").get_attribute("data-animation-epoch")}

            if page.locator("#legend-mode").inner_text() != "2D":
                page.locator("#layered-toggle").click()
            expect(page.locator("#legend-mode")).to_have_text("2D")
            positive_2d = select_rule(positive)
            page.wait_for_function("document.querySelector('#renderer').dataset.animationActive==='true'", timeout=3000)
            page.screenshot(path=str(OUT / "boolean-transfer-2d.png"), full_page=True)
            negative_2d = select_rule(negative)
            page.screenshot(path=str(OUT / "skipped-guards-2d.png"), full_page=True)
            page.locator("#layered-toggle").click()
            expect(page.locator("#legend-mode")).to_have_text("3D")
            positive_3d = select_rule(positive)
            page.wait_for_function("document.querySelector('#renderer').dataset.animationActive==='true'", timeout=10000)
            assert set(policy_ids) <= set(page.locator("[data-node-id]").evaluate_all("nodes=>nodes.map(n=>n.dataset.nodeId)"))
            page.screenshot(path=str(OUT / "boolean-transfer-3d.png"), full_page=True)
            page.locator("#layered-toggle").click()
            expect(page.locator("#legend-mode")).to_have_text("2D")
            negative_again = select_rule(negative)
            report["ui_animation_witnesses"] = {"positive_2d": positive_2d, "skipped_2d": negative_2d,
                                                "positive_3d": positive_3d, "skipped_after_3d": negative_again}
            report["checks"].append("Actual raw-event replay animates the three used guard edges in 2D/3D; the anonymous short-circuit step animates only signed_in and never its two skipped children.")

            node = page.locator('[data-node-id="revoke"]')
            node.focus()
            page.locator("#selection-menu").click()
            expect(page.locator("#source")).to_be_enabled()
            page.locator("#source").click()
            expect(page.locator("#source-code")).to_contain_text("def revoke", timeout=15000)
            expect(page.locator("#source-code")).to_contain_text("DELETE FROM shares")
            page.screenshot(path=str(OUT / "source-navigation.png"), full_page=True)
            page.locator("#close-detail").click()
            position = page.locator("#replay-position").get_attribute("data-event-id")
            page.locator("#replay-next").click()
            assert page.locator("#replay-position").get_attribute("data-event-id") != position
            page.locator("#replay-play").click()
            expect(page.locator("#replay-play")).to_have_attribute("data-icon", "pause")
            page.locator("#replay-play").click()
            page.locator("#replay-live").click()
            expect(page.locator("#replay")).to_be_hidden()
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#semantic').children.length > 0", timeout=20000)
            after = page.request.get(GRAPH + "/api/view").json()
            assert after["binding_status"]["status"] == "current"
            assert len(after["events"]) == count, "Viewer controls must not generate business events."
            assert not report["page_errors"] and not report["console_errors"], report
            report["checks"].append("Bound source file viewing, next/play/pause, return-to-live and rendered reload pass with zero business events from observer controls.")
            report["status"] = "passed"
        finally:
            browser.close()
            client = playwright.request.new_context()
            try:
                for _ in range(3):
                    current = client.get(GRAPH + "/api/preferences").json()
                    restored = {**original_preferences, "revision": current["revision"]}
                    response = client.post(GRAPH + "/api/preferences", data=restored)
                    if response.status == 200:
                        break
                    assert response.status == 409, response.text()
                assert response.status == 200
                final_preferences = client.get(GRAPH + "/api/preferences").json()
                assert final_preferences["entries"] == original_preferences["entries"]
                report["personal_preferences"] = {"entries_preserved": len(final_preferences["entries"]),
                    "entry_values_identical": True, "revision": final_preferences["revision"],
                    "restoration": "Native revision-checked preferences API after closing the test browser."}
            finally:
                client.dispose()
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_hash
    assert hashlib.sha256((OUT / "recording.json").read_bytes()).hexdigest() == capture["recording_sha256"]
    report["raw_recording_unchanged"] = True
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "review/browser-latest.json").write_text(json.dumps({"report": str(OUT / "report.json"), "status": "passed"}, indent=2), encoding="utf-8")
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    attempt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "attempt": str(attempt)}))
