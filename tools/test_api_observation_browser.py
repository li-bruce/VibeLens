"""Verify exact API graph/timeline replay using serialized native event evidence.

The isolated browser fixture supplies deterministic observations, not a running
business application. Backend tests separately validate selector registration.
"""

from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
import test_graph_quality_browser as fixture

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "BO_API_OBSERVATION_EVIDENCE", ROOT / ".validation/api-observation-browser"
    )
).resolve()


def main():
    """Seek original GET/POST events and inspect rendered API state and durations."""
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "results.json").exists():
        raise FileExistsError("Choose a fresh BO_API_OBSERVATION_EVIDENCE directory")
    environment = {**os.environ, "BO_API_RECORDING": str(OUT / "native-recording.json")}
    subprocess.run(
        ["node", "tools/test_api_observation.mjs"],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    saved = json.loads((OUT / "native-recording.json").read_text(encoding="utf-8"))
    base = deepcopy(fixture.recording)
    base.update(saved, build_id="build", gaps=[], capture={"mode": "all"})
    for name in ("context", "final"):
        snapshot = deepcopy(fixture.view)
        snapshot.update(saved[name])
        snapshot["authority"] = {
            **fixture.view["authority"],
            **saved[name]["authority"],
            "entity": "entity",
            "parameters": {"attempt": "attempt"},
        }
        snapshot["model"] = {
            **fixture.view["model"],
            **saved[name]["model"],
            "project_id": "api-observation-browser",
        }
        snapshot["available_cases"] = ["live"]
        snapshot["historical"] = False
        snapshot["machine"] = {"current": None, "journal": [], "configurations": []}
        snapshot["manifest"]["model_hash"] = "api-observation-fixture"
        base[name] = snapshot
    base["final"]["events"] = saved["events"]
    fixture.view = base["final"]
    fixture.preferences = {
        "schema": 1,
        "project_id": "api-observation-browser",
        "revision": 1,
        "entries": {},
        "conflicts": [],
    }

    class Handler(fixture.Handler):
        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/api/recordings":
                return self.json(
                    {
                        "active": None,
                        "recordings": [{**base, "events": len(base["events"])}],
                    }
                )
            if route == "/api/recordings/" + base["id"]:
                return self.json(base)
            return super().do_GET()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors, checks = [], []
    result = {
        "basis": "serialized exact HTTP observation fixture; native browser controls"
    }
    with sync_playwright() as p:
        default_chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("BO_BROWSER_EXECUTABLE")
            or (str(default_chrome) if default_chrome.is_file() else None),
            args=["--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(
                f"http://127.0.0.1:{server.server_port}/graph?lang=en",
                wait_until="domcontentloaded",
            )
            page.wait_for_function(
                "() => window.graphDebug?.graph && !graphDebug.layoutBusy"
            )
            assert page.evaluate(
                "graphDebug.graph.all.has('endpoint:files')"
            ), "API snapshot must load without enabling optional code structure"
            page.select_option("#record-list", base["id"])
            page.wait_for_function("() => graphDebug.timeline?.source === 'saved'")
            page.select_option("#analysis-view", "api")
            page.wait_for_function(
                "() => !graphDebug.layoutBusy && graphDebug.timeline?.rows.some(r=>r.layer==='entry' && r.members.includes('endpoint:files'))"
            )
            page.select_option("#replay-grain", "events")
            page.select_option("#replay-events", "2")
            page.wait_for_function("() => graphDebug.timeline.eventId === 'get-enter'")
            state = page.evaluate(
                "({ api:graphDebug.graph.byId.get('endpoint:files')?.state, archive:graphDebug.graph.byId.get('endpoint:archive')?.state, timeline:graphDebug.timeline })"
            )
            assert state["api"] == "active", state
            assert state["archive"] == "declared", state
            intervals = [
                slice
                for slice in state["timeline"]["lifecycles"]
                if slice["node"] == "endpoint:files"
            ]
            assert [slice["duration"] for slice in intervals] == [60, 30], intervals
            assert not any(
                slice["node"] in ["endpoint:archive", "code:files"]
                for slice in state["timeline"]["lifecycles"]
            )
            page.screenshot(path=str(OUT / "01-get-active-api-view.png"))
            checks.append(
                "Recorded API view loads retained snapshot; exact GET interval activates only /files"
            )
            page.select_option("#replay-events", "6")
            page.wait_for_function("() => graphDebug.timeline.eventId === 'post-enter'")
            assert (
                page.evaluate("graphDebug.graph.byId.get('endpoint:files').state")
                == "active"
            )
            page.select_option("#replay-events", "7")
            page.wait_for_function(
                "() => graphDebug.timeline.eventId === 'post-return'"
            )
            rows = page.evaluate("graphDebug.graph.byId.get('endpoint:files').rows")
            assert any(row["text"] == "status: 403" for row in rows), rows
            assert (
                page.evaluate("graphDebug.graph.byId.get('endpoint:archive').state")
                == "declared"
            )
            page.screenshot(path=str(OUT / "02-post-return-values.png"))
            checks.append(
                "POST reuses endpoint identity with its own interval and recorded HTTP 403 value"
            )
            page.select_option("#analysis-view", "overview")
            # Cross-concern replay is an explicit detailed view. The normal
            # overview intentionally hides implementation internals.
            page.locator("#layers-all").evaluate("button => button.click()")
            page.click("#expand")
            page.wait_for_function("() => !graphDebug.layoutBusy")
            page.select_option("#replay-events", "3")
            page.wait_for_function(
                "() => graphDebug.timeline.eventId === 'store-enter'"
            )
            trace = page.evaluate("graphDebug.timeline")
            assert trace["flows"] > 0, trace
            assert any(
                row["layer"] == "entry" and "endpoint:files" in row["members"]
                for row in trace["rows"]
            )
            assert any(
                trace["rows"][route["fromRow"]]["layer"] == "entry"
                and trace["rows"][route["toRow"]]["layer"] == "symbols"
                and route["key"] == "2:3:3:call"
                for route in trace["routes"]
            ), trace
            assert any(
                trace["rows"][route["toRow"]]["layer"] == "entry"
                and route["key"] == "4:2:4:return"
                and route["type"] == "return"
                for route in trace["routes"]
            ), trace
            assert any(
                trace["rows"][route["fromRow"]]["layer"] == "business"
                and trace["rows"][route["toRow"]]["layer"] == "entry"
                and route["key"] == "1:2:2:call"
                for route in trace["routes"]
            ), trace
            page.screenshot(path=str(OUT / "03-cross-layer-causality.png"))
            result["timeline"] = trace
            checks.append(
                "Overview retains the original cursor and business-to-entry-to-execution causal links"
            )
            assert not errors, errors
            result["passed"] = True
        except Exception as error:
            result["error"] = repr(error)
            result["debug"] = page.evaluate(
                "window.graphDebug ? {timeline:graphDebug.timeline, nodes:graphDebug.graph?.boxes.map(b=>({id:b.id,state:b.state,rows:b.rows}))} : null"
            )
            page.screenshot(path=str(OUT / "failure.png"))
            raise
        finally:
            result.update(errors=errors, checks=checks)
            (OUT / "results.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            browser.close()
            server.shutdown()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
