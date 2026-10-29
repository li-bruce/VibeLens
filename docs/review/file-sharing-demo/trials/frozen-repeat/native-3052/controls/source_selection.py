"""Supplement the scripted business controls with an explicit native source-node check."""
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
activation = read(OUT / "activation-private.json")["result"]
recording = read(OUT.parent / "browser-native/capture-report.json")["recording_id"]
inventory = read(OUT / "inventory.json")["result"]
view = read(OUT / "view-before.json")
candidates = [node for node in view["model"]["nodes"] if node.get("origin") == "source-ast"
              and node.get("parent") == "download" and node.get("label") == "FileService.authorise"]
assert len(candidates) == 1
node = candidates[0]
assert any(row["id"] == node["id"] and row.get("parent") == "download" for row in inventory["nodes"])
spec = {"action": "view", "label": "Technical explicit source selection", "anchors": [node["id"]],
        "depth": 0, "direction": "both", "nodes": ["business", "function"],
        "edges": ["call"], "layout": "layered", "max_nodes": 30}
(OUT / "source.spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
report = {"status": "running", "provenance": "Agent-authored technical scripted user check within authorized native-control acceptance; not human confirmation",
          "actual_source_node": node, "scope": "Canonical source-ast node must enable advanced details and expand its actual business parent."}

def command(action, message, name, spec_name=None):
    args = [sys.executable, "-B", "-X", "utf8", str(ROOT / "observer_runtime/bo_control.py"), action,
            "--root", str(ROOT), "--url", GRAPH, "--conversation", THREAD, "--message", message]
    if spec_name:
        args.extend(["--spec", str(OUT / (spec_name + ".spec.json"))])
    if spec_name == "replay":
        args.extend(["--recording", recording])
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
    (OUT / (name + ".stdout.json")).write_text(result.stdout, encoding="utf-8")
    (OUT / (name + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
    value = json.loads(result.stdout)
    assert result.returncode == 0 and value["valid"], value
    return value["result"]

def apply(page, message, spec_name, name):
    plan = command("plan", message, name + ".plan", spec_name)
    published = command("apply", message, name + ".apply", spec_name)
    assert published["plan"] == plan
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        page.wait_for_timeout(850)
        status = command("status", message, name + ".status")
        if status["revision"] == published["revision"] and status.get("result"):
            assert status["result"]["status"] == "applied", status["result"]
            expect(page.locator("body")).to_have_attribute("data-control-plan", plan["id"])
            actual = page.locator("[data-node-id]").evaluate_all("els=>els.map(el=>el.dataset.nodeId)")
            assert set(plan["node_ids"]) <= set(actual)
            return plan, actual
    raise AssertionError("Actual native browser acknowledgement was not received")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-proxy-server"])
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        try:
            before = page.request.get(GRAPH + "/api/view").json()
            global_before = page.request.get(GRAPH + "/api/preferences").json()
            page.goto(activation["graph_url"], wait_until="domcontentloaded")
            page.wait_for_function("document.querySelectorAll('[data-node-id]').length>0", timeout=20000)
            message = "/vibelens 显示下载动作下实际的 FileService.authorise 源码调用节点"
            plan, visible = apply(page, message, "source", "source-native")
            expect(page.locator("#analysis-details")).to_have_attribute("aria-pressed", "true")
            expect(page.locator('[data-node-id="download"]')).to_have_attribute("aria-expanded", "true")
            page.screenshot(path=str(OUT / "source-native.png"))
            report.update(requested_nodes=plan["node_ids"], all_requested_visible=True,
                          parent_expanded=True, advanced_details_enabled=True)
            replay_message = read(OUT / "provenance.json")["replay_input"]
            restored, visible = apply(page, replay_message, "replay", "source-restore-replay")
            expect(page.locator("#replay-loop")).to_be_checked()
            report["last_authorized_replay_restored"] = True
            final = page.request.get(GRAPH + "/api/view").json()
            report["observer_control_business_event_delta"] = len(final["events"]) - len(before["events"])
            assert report["observer_control_business_event_delta"] == 0
            assert page.request.get(GRAPH + "/api/preferences").json() == global_before
            report["status"] = "passed"
        finally:
            browser.close()
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    (OUT / "source-selection-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "error": report.get("error", "")}))
