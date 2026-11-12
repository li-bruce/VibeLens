"""Exercise a real collector and multi-model probes through the desktop viewer.

The in-process server lets the test interleave native operations with actual Web
record/start/stop controls. No API response or graph state is mocked in the browser.
"""

import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get("VIBELENS_TEST_SKILL", ROOT / "skills/vibelens"))
sys.path[:0] = [str(ROOT / "tests"), str(SKILL / "scripts")]
from bo_observer.service import GraphSession, make_server
from bo_observer.adapters.python.bo_probe import BOProbe
from test_model_networks import write_project


def main():
    out = ROOT / os.environ.get(
        "BO_MODEL_NETWORK_EVIDENCE", "docs/review/model-networks-20261112/browser"
    )
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / ".validation").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
        root = Path(folder)
        project = write_project(root)
        native = runpy.run_path(str(root / "app.py"))
        session = GraphSession(root)
        assert session.web.assets.resolve() == (SKILL / "assets/stategraph-viewer").resolve()
        probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
        session.bo_bind_capture(
            scope_setter=probe.bo_set_scope,
            flush_capture=lambda: probe.flush(3),
            health=probe.bo_health,
        )
        server = make_server(session, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors, checks = [], []
        try:
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    headless=True, executable_path=os.environ.get("BO_BROWSER_EXECUTABLE")
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: (
                        errors.append("console: " + message.text)
                        if message.type == "error"
                        else None
                    ),
                )
                page.goto(f"http://127.0.0.1:{server.server_port}/graph?lang=en")
                try:
                    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
                except BrowserTimeout:
                    page.screenshot(path=str(out / "startup-failure.png"))
                    raise AssertionError(
                        {"errors": errors, "body": page.locator("body").inner_text()}
                    )
                # Live observation polls continuously; a quiet network is optional.
                try:
                    page.wait_for_load_state("networkidle", timeout=2000)
                except BrowserTimeout:
                    page.wait_for_function("window.graphDebug?.view && !graphDebug.sourceBusy")
                options = page.locator("#analysis-view option").evaluate_all(
                    "items => items.map(item => ({id:item.value, label:item.textContent}))"
                )
                network_views = [
                    option for option in options if option["id"].startswith("network-")
                ]
                assert len(network_views) == 2, {
                    "options": options,
                    "assets": str(session.web.assets),
                    "models": page.evaluate(
                        "({machines:graphDebug.view.model.machines, networks:graphDebug.view.model.networks})"
                    ),
                    "profiles": page.evaluate(
                        "async () => (await import('/analysis.js')).networkProfiles(graphDebug.view)"
                    ),
                }
                for mode in ("2D", "3D"):
                    if page.locator("#layered-toggle").inner_text() != mode:
                        page.click("#layered-toggle")
                    for network in network_views:
                        page.select_option("#analysis-view", network["id"])
                        page.wait_for_function("!graphDebug.layoutBusy && !graphDebug.sourceBusy")
                        ids = page.evaluate(
                            "[...graphDebug.presentation.glyphs].filter(id => graphDebug.graph.all.get(id)?.kind === 'state')"
                        )
                        model_id = "file" if "file" in network["label"] else "approval"
                        assert set(ids) == {model_id + ":idle", model_id + ":ready"}, (mode, ids)
                        checks.append({"mode": mode, "network": network["label"], "states": ids})
                    page.select_option("#analysis-view", "states")
                    page.wait_for_function("!graphDebug.layoutBusy")
                    if mode == "3D":
                        page.wait_for_function("graphDebug.spatial?.webgl")
                    page.screenshot(path=str(out / (mode.lower() + ".png")))

                page.click("#record-start")
                page.wait_for_function("!document.querySelector('#record-stop').disabled")
                for model_id, revision in (
                    ("file", 0),
                    ("approval", 0),
                    ("file", 1),
                    ("approval", 1),
                ):
                    state = native[model_id + "_advance"]() if revision else "idle"
                    event = probe.record(
                        model_id + ":advance",
                        "change",
                        lambda: {"outputs": {"state": state}},
                        entity="1",
                        attempt="same",
                        revision=revision,
                    )
                    assert probe.snapshot(
                        "1",
                        state,
                        {},
                        revision,
                        event,
                        state_model_id=model_id,
                        event="advance" if revision else None,
                    )
                    assert probe.flush(3)
                page.wait_for_function("graphDebug.view.machine.configurations.length === 2")
                page.click("#record-stop")
                page.wait_for_function("graphDebug.timeline?.lifecycles?.length >= 4")
                trace = page.evaluate("graphDebug.timeline")
                page.screenshot(path=str(out / "recording.png"))
                checks.append(
                    {
                        "runtime_models": [
                            cfg["state_model_id"]
                            for cfg in session.view()["machine"]["configurations"]
                        ],
                        "timeline": trace,
                    }
                )
                assert probe.bo_health()["errors"] == 0, probe.bo_health()
                page.click("#replay-live")
                # Change the authored network catalog through the real project
                # file/reload path. Polling must update the menu without reload.
                project["model"]["networks"].append(
                    {
                        "id": "review-actions",
                        "layer": "business",
                        "label": "Review actions",
                        "nodes": ["approval:advance"],
                    }
                )
                (root / "bo_stategraph/project.json").write_text(
                    json.dumps(project), encoding="utf-8"
                )
                assert server.bo_reload()
                page.wait_for_function(
                    "[...document.querySelectorAll('#analysis-view option')].filter(option => option.value.startsWith('network-')).length === 3"
                )
                page.select_option("#analysis-view", network_views[0]["id"])
                page.wait_for_function("!graphDebug.layoutBusy && !graphDebug.sourceBusy")
                page.wait_for_function(
                    "document.querySelector('#layout-status')?.textContent.includes('saved')"
                )
                page.reload()
                page.wait_for_function(
                    "window.graphDebug?.graph && !graphDebug.layoutBusy && !graphDebug.sourceBusy"
                )
                assert page.input_value("#analysis-view") == network_views[0]["id"]
                ids = page.evaluate(
                    "[...graphDebug.presentation.glyphs].filter(id => graphDebug.graph.all.get(id)?.kind === 'state')"
                )
                assert set(ids) == {"file:idle", "file:ready"}, ids
                page.screenshot(path=str(out / "iteration.png"))
                checks.append(
                    {
                        "automatic_catalog_refresh": 3,
                        "restored_network": network_views[0]["label"],
                        "states": ids,
                    }
                )
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)
            probe.close()
            session.close()
            (out / "result.json").write_text(
                json.dumps({"checks": checks, "page_errors": errors}, indent=2), encoding="utf-8"
            )
        print(json.dumps({"valid": True, "checks": len(checks), "evidence": str(out)}))


if __name__ == "__main__":
    main()
