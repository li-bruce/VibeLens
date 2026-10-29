"""Real native scoped controls; scripted user provenance, no patched runtime or fake events."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
GRAPH = "http://127.0.0.1:8841"
THREAD = "01a18512-6617-7791-aa29-f2aeb9312859"
assert os.environ.get("CODEX_THREAD_ID") == THREAD
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

activation = read(OUT / "activation-private.json")["result"]
TOKEN = activation["session"]
URL = activation["graph_url"]
provenance = read(OUT / "provenance.json")
capture = read(OUT.parent / "browser-native/capture-report.json")
RECORDING = capture["recording_id"]
raw_path = ROOT / "bo_stategraph/data/recordings" / (RECORDING + ".json")
raw_hash = sha(raw_path)
report = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
          "provenance": "scripted user; authorized isolated-project simulation, not human confirmation",
          "actual_conversation": THREAD, "session_fingerprint": hashlib.sha256(TOKEN.encode()).hexdigest(),
          "checks": [], "privacy": "Local raw evidence. Private session/config must be redacted or excluded from public archives."}

def native(command, message, name, spec=None):
    args = [sys.executable, "-B", "-X", "utf8", str(ROOT / "observer_runtime/bo_control.py"),
            command, "--root", str(ROOT), "--conversation", THREAD,
            "--url", GRAPH, "--message", message]
    if spec:
        args.extend(["--spec", str(OUT / (spec + ".spec.json"))])
    if spec == "replay":
        args.extend(["--recording", RECORDING])
    process = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
    (OUT / (name + ".stdout.json")).write_text(process.stdout, encoding="utf-8")
    (OUT / (name + ".stderr.txt")).write_text(process.stderr, encoding="utf-8")
    value = json.loads(process.stdout)
    return process.returncode, value

def visible(page):
    return page.locator("[data-node-id]").evaluate_all("els=>els.map(el=>el.dataset.nodeId)")

def verify_nodes(page, plan, label):
    actual = visible(page)
    missing = sorted(set(plan["node_ids"]) - set(actual))
    write(label + ".dom.json", {"requested": plan["node_ids"], "visible": actual,
          "missing": missing, "edges": page.locator("[data-edge-id]").evaluate_all("els=>els.map(el=>({...el.dataset}))")})
    assert not missing, "Requested nodes absent from actual semantic DOM: " + ", ".join(missing)
    return actual

def apply(page, name, message):
    code, preview = native("plan", message, name + ".plan", name)
    assert code == 0 and preview["valid"], preview
    plan = preview["result"]
    code, published = native("apply", message, name + ".apply", name)
    assert code == 0 and published["valid"], published
    assert published["result"]["plan"] == plan
    revision = published["result"]["revision"]
    deadline = time.monotonic() + 55
    status = None
    while time.monotonic() < deadline:
        page.wait_for_timeout(850)
        code, value = native("status", message, name + ".status")
        assert code == 0 and value["valid"], value
        status = value["result"]
        if status["revision"] == revision and status.get("result"):
            break
    write(name + ".actual-status-private.json", status)
    assert status and status.get("result"), "Native apply was never acknowledged by the real browser"
    assert status["result"]["status"] == "applied", status["result"]
    assert set(plan["node_ids"]) <= set(status["result"]["nodes"])
    expect(page.locator("body")).to_have_attribute("data-control-plan", plan["id"])
    actual = verify_nodes(page, plan, name)
    assert not plan["limits_hit"]
    row = {"name": name, "status": "applied", "requested_nodes": len(plan["node_ids"]),
           "visible_nodes": len(actual), "requested_edges": len(plan["edge_ids"]), "all_requested_visible": True,
           "plan_id": plan["id"], "revision": revision}
    report["checks"].append(row)
    page.screenshot(path=str(OUT / (name + ".png")))
    return plan, row

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
        context = browser.new_context(viewport={"width": 1600, "height": 1100})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            initial = page.request.get(GRAPH + "/api/view").json()
            global_before = page.request.get(GRAPH + "/api/preferences").json()
            report["build_id"] = initial["manifest"]["build_id"]
            assert report["build_id"] == capture["build_id"]
            write("view-before.json", initial)
            model = initial["model"]
            nodes = {node["id"]: node for node in model["nodes"]}
            edges = {edge["id"]: edge for edge in model["edges"]}
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_function("document.querySelectorAll('[data-node-id]').length>0", timeout=20000)
            main_plan, main_row = apply(page, "main", provenance["main_input"])
            main_row["nested_policy_boundary_visible"] = "policy:access_allowed" in visible(page)

            permission_plan, permission_row = apply(page, "permission", provenance["permission_input"])
            expect(page.locator('[data-node-id="policy:network"]')).to_have_attribute("aria-expanded", "true")
            ancestors = set()
            for node_id in permission_plan["node_ids"]:
                parent = nodes[node_id].get("parent")
                while parent and parent in nodes:
                    ancestors.add(parent)
                    parent = nodes[parent].get("parent")
            for ancestor in sorted(ancestors):
                expect(page.locator('[data-node-id="' + ancestor + '"]')).to_have_attribute("aria-expanded", "true")
            semantic = page.locator("[data-edge-id]").evaluate_all("els=>els.map(el=>({...el.dataset}))")
            expected = [edges[key] for key in permission_plan["edge_ids"]]
            missing_edges = [edge["id"] for edge in expected if not any(
                actual["from"] == edge["from"] and actual["to"] == edge["to"] and
                actual["relationType"] == edge["type"] for actual in semantic)]
            assert not missing_edges, missing_edges
            fields = page.evaluate("""async ({view,selected})=>{
                const {graphInventory}=await import('/graph-inventory.js');
                const {all}=graphInventory(view);
                return [...all.values()].filter(n=>n.origin==='capture-field' && selected.includes(n.event_node)
                    && n.analysis_level!=='advanced').map(n=>({id:n.id,owner:n.event_node,parent:n.parent,field:n.field}));
            }""", {"view": initial, "selected": permission_plan["node_ids"]})
            actual = visible(page)
            missing_fields = [field["id"] for field in fields if field["id"] not in actual]
            write("permission.capture-fields.json", {"fields": fields, "missing": missing_fields})
            assert fields and not missing_fields, missing_fields
            permission_row.update(ancestors_expanded=sorted(ancestors), actual_relations_retained=len(expected),
                                  generated_capture_fields_visible=len(fields))
            saved = page.request.get(GRAPH + "/api/preferences?vl_session=" + TOKEN).json()
            write("permission.saved-preferences-private.json", saved)
            assert saved["entries"], "Scoped preferences were not persisted"
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("id=>document.body.dataset.controlPlan===id", arg=permission_plan["id"], timeout=20000)
            verify_nodes(page, permission_plan, "permission.reloaded")
            expect(page.locator('[data-node-id="policy:network"]')).to_have_attribute("aria-expanded", "true")
            permission_row["reload_passed"] = True

            before_negative = page.request.get(GRAPH + "/api/preferences?vl_session=" + TOKEN).json()
            code, rejected = native("apply", "只看主要业务流程", "missing-prefix", "main")
            assert code != 0 and not rejected["valid"] and "explicit /vibelens prefix" in rejected["error"]
            after_negative = page.request.get(GRAPH + "/api/preferences?vl_session=" + TOKEN).json()
            assert before_negative == after_negative, "Rejected unprefixed apply wrote scoped view preferences"
            write("missing-prefix.view-write-check.json", {"status": "passed", "exit_code": code,
                "error": rejected["error"], "preferences_byte_equivalent": True, "revision": after_negative["revision"]})
            report["missing_prefix_rejected_without_view_write"] = True

            replay_plan, replay_row = apply(page, "replay", provenance["replay_input"])
            assert replay_plan["recording"]["id"] == RECORDING
            raw = read(raw_path)
            selected_events = [event["id"] for event in raw["events"] if event["node"] in replay_plan["node_ids"]]
            assert selected_events == replay_plan["recording"]["event_ids"]
            assert 0 < len(selected_events) < len(raw["events"])
            page.locator("#replay-grain").select_option("events")
            expect(page.locator("#replay-loop")).to_be_checked()
            checked = page.locator("#replay-step-list input:checked").evaluate_all("els=>els.map(el=>el.dataset.eventId)")
            assert set(checked) == set(selected_events)
            cursor = page.locator("#replay-position").get_attribute("data-event-id")
            assert cursor in selected_events
            page.locator("#replay-next").click()
            next_cursor = page.locator("#replay-position").get_attribute("data-event-id")
            assert next_cursor in selected_events and next_cursor != cursor
            replay_row.update(recording_id=RECORDING, total_events=len(raw["events"]),
                              selected_events=len(selected_events), checked_events=len(checked), loop=True,
                              native_next_stayed_in_filter=True)
            page.locator("#layered-toggle").click()
            expect(page.locator("#legend-mode")).to_have_text("3D")
            verify_nodes(page, replay_plan, "replay.3d")
            page.screenshot(path=str(OUT / "replay.3d.png"))
            page.locator("#layered-toggle").click()
            expect(page.locator("#legend-mode")).to_have_text("2D")
            verify_nodes(page, replay_plan, "replay.2d")
            write("replay.saved-preferences-private.json", page.request.get(GRAPH + "/api/preferences?vl_session=" + TOKEN).json())
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("id=>document.body.dataset.controlPlan===id", arg=replay_plan["id"], timeout=20000)
            verify_nodes(page, replay_plan, "replay.reloaded")
            expect(page.locator("#replay-loop")).to_be_checked()
            page.locator("#replay-grain").select_option("events")
            checked_again = page.locator("#replay-step-list input:checked").evaluate_all("els=>els.map(el=>el.dataset.eventId)")
            assert set(checked_again) == set(selected_events)
            replay_row.update(two_and_three_dimensions=True, reload_passed=True)
            assert sha(raw_path) == raw_hash
            final = page.request.get(GRAPH + "/api/view").json()
            report["observer_control_business_event_delta"] = len(final["events"]) - len(initial["events"])
            assert report["observer_control_business_event_delta"] == 0
            assert page.request.get(GRAPH + "/api/preferences").json() == global_before
            report.update(global_preferences_unchanged=True, raw_recording_unchanged=True,
                          raw_recording_sha256=raw_hash, browser_errors=errors)
            assert not errors, errors
            report["status"] = "passed"
        finally:
            page.screenshot(path=str(OUT / "final-local.png"))
            browser.close()
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    write("report.json", report)
    print(json.dumps({"status": report["status"], "completed_controls": len(report["checks"]),
                      "error": report.get("error", "")}))
