"""Exercise canonical graph assets in Chrome using an isolated HTTP fixture.

The fixture supplies geometry and preference data only. Its screenshots are UI
acceptance evidence, not application-runtime or business-correctness evidence.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse, unquote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "BO_GRAPH_QUALITY_EVIDENCE", ROOT / ".validation/graph-quality-browser"
    )
).resolve()
ASSETS = ROOT / "skills/vibelens/assets/stategraph-viewer"
KEY = "business-observer.layout.v2:graph-quality-browser"
LAYERS = [
    "business",
    "state",
    "rules",
    "api",
    "execution",
    "project",
    "code",
    "operations",
    "data",
]
NODES = [
    {"id": "share", "kind": "function", "layer": "business", "label": "Share a file"},
    {
        "id": "notify",
        "kind": "function",
        "layer": "business",
        "label": "Notify recipient",
    },
    {
        "id": "store",
        "parent": "share",
        "kind": "function",
        "label": "Save sharing",
        "source": {"path": "sharing.py", "symbol": "save_share"},
    },
    {
        "id": "database",
        "parent": "share",
        "kind": "data",
        "data_role": "store",
        "label": "Team files",
        "data_store": "files",
        "data_key": "store",
    },
    {
        "id": "files",
        "parent": "database",
        "kind": "data",
        "data_role": "dataset",
        "label": "Files",
        "data_key": "files",
    },
    {
        "id": "shares",
        "parent": "database",
        "kind": "data",
        "data_role": "dataset",
        "label": "Shares",
        "data_key": "shares",
    },
    {
        "id": "file_id",
        "parent": "files",
        "kind": "data",
        "data_role": "column",
        "label": "id",
        "data_key": "id",
    },
    {
        "id": "file_name",
        "parent": "files",
        "kind": "data",
        "data_role": "column",
        "label": "name",
        "data_key": "name",
    },
]
EDGES = [
    {
        "id": "share-notify",
        "from": "share",
        "to": "notify",
        "type": "flow",
        "label": "Notify",
    },
    {
        "id": "store-shares",
        "from": "store",
        "to": "shares",
        "type": "data",
        "label": "Write shares",
    },
]
CENTERS = {
    "share": (-2600, -2300),
    "notify": (640, 20),
    "store": (220, -190),
    "database": (-2100, -2500),
    "files": (50, 20),
    "shares": (330, 30),
    "file_id": (0, 15),
    "file_name": (100, 15),
}
layout = {
    "schema": 2,
    "positions": {
        name: {"x": x - 70, "y": z - 31, "pinned": name == "file_id"}
        for name, (x, z) in CENTERS.items()
    },
    "expanded": ["share", "database", "files"],
    "spatial": {
        "positions": {
            name: {"x": x, "y": 0, "z": z, "pinned": name == "file_id"}
            for name, (x, z) in CENTERS.items()
        }
    },
    "algorithm": "cluster",
    "annotations": {},
    "focus": None,
}
analysis = {
    "selected": "overview",
    "advanced": True,
    "layers": {
        "schema": 2,
        "enabled": False,
        "visible": LAYERS,
        "gap": 260,
        "projections": True,
    },
    "layerVisibility": {"overview": LAYERS},
    "routing": "curve",
}
preferences = {
    "schema": 1,
    "project_id": "graph-quality-browser",
    "revision": 1,
    "entries": {KEY: json.dumps(layout), KEY + ":analysis": json.dumps(analysis)},
    "conflicts": [],
}
recording = json.loads(
    (
        ROOT
        / "docs/review/recording-timeline/real-project-completion/v2-recording.json"
    ).read_text(encoding="utf-8")
)
view = {**recording["context"], **recording["final"], "events": []}
view["model"] = {
    **view["model"],
    "project_id": "graph-quality-browser",
    "nodes": NODES,
    "edges": EDGES,
    "source_files": [],
    "presentation": {},
    "machine": {
        "values": [],
        "states": [],
        "events": {},
        "transitions": [],
        "labels": {},
    },
}
view["machine"] = {"journal": [], "configurations": [], "current": None}
view["manifest"] = {**view["manifest"], "bindings": {}}
view["memberships"] = []
view["source_revision"] = "isolated-geometry-fixture"
requests = []


class Handler(BaseHTTPRequestHandler):
    """Serve current repository assets and project-local preference persistence."""

    def log_message(self, *_):
        pass

    def do_GET(self):
        route = urlparse(self.path).path
        requests.append({"method": "GET", "route": route})
        if route == "/api/view":
            return self.json(view)
        if route == "/api/preferences":
            return self.json(preferences)
        if route == "/api/design":
            return self.json({"available": False})
        if route == "/api/recordings":
            return self.json({"active": None, "recordings": []})
        if route.startswith("/api/"):
            return self.json({"error": "Not provided by isolated UI fixture"}, 404)
        target = ASSETS / (
            "index.html" if route in {"/", "/graph"} else unquote(route).lstrip("/")
        )
        if not target.resolve().is_relative_to(ASSETS) or not target.is_file():
            return self.json({"error": "Unknown asset"}, 404)
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(target)[0] or "application/octet-stream",
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global preferences
        if urlparse(self.path).path != "/api/preferences":
            return self.json({"error": "Read-only geometry fixture"}, 405)
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        preferences = {**payload, "revision": preferences["revision"] + 1}
        return self.json(preferences)

    def json(self, value, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())


def main():
    """Keep failure screenshots and timings; assertions inspect actual geometry."""
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "results.json").exists():
        raise FileExistsError(
            "Choose another BO_GRAPH_QUALITY_EVIDENCE directory to retain the previous run"
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/graph?lang=en"
    errors, checks = [], []
    result = {
        "fixture": "isolated nested file-sharing geometry",
        "canonical_assets": str(ASSETS),
        "url": url,
    }
    with sync_playwright() as p:
        default_chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("BO_BROWSER_EXECUTABLE")
            or (str(default_chrome) if default_chrome.is_file() else None),
            args=["--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(
            viewport={"width": 1600, "height": 1100}, device_scale_factor=1
        )
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "console",
            lambda message: (
                errors.append(message.text)
                if message.type == "error"
                and not message.text.startswith("Failed to load resource:")
                else None
            ),
        )

        def ready():
            page.wait_for_function(
                "() => window.graphDebug?.graph && !graphDebug.layoutBusy",
                timeout=45000,
            )
            page.wait_for_timeout(180)

        def layer(name):
            order = page.evaluate("graphDebug.layers.order")
            box = page.locator("#layer-controls canvas").bounding_box()
            page.mouse.click(box["x"] + 17, box["y"] + 40 + order.index(name) * 34 + 17)
            ready()

        try:
            # The live viewer deliberately polls every 400 ms. Await its loaded
            # geometry rather than a 500 ms network-idle interval it never has.
            page.goto(url, wait_until="domcontentloaded")
            ready()
            before = page.evaluate(
                "({ ids:graphDebug.graph.boxes.map(b=>b.id), regions:graphDebug.displayGraph.regions, ports:graphDebug.planarPorts, edges:graphDebug.presentation.edges.map(e=>({id:e.id,from:e.from,to:e.to,members:e.members?.map(m=>m.id)})) })"
            )
            result["initial"] = before
            circle = next(r for r in before["regions"] if r["id"] == "database")
            assert circle["radius"] < 350, circle
            assert set(before["ids"]) == {n["id"] for n in NODES}
            route_id = next(
                e["id"]
                for e in before["edges"]
                if "store-shares" in (e.get("members") or [e["id"]])
            )
            assert any(port["id"] == route_id for port in before["ports"])
            page.screenshot(path=str(OUT / "01-tight-planar.png"))
            checks.append(
                "2D circles fit visible children with distant saved owners unchanged"
            )
            page.click("#layered-toggle")
            ready()
            page.click("#fit")
            ready()
            page.mouse.move(1300, 300)
            page.mouse.down()
            page.mouse.move(1420, 420, steps=12)
            page.mouse.up()
            page.wait_for_timeout(350)
            first = page.evaluate(
                "({ state:graphDebug.spatial, positions:graphDebug.spatialPositions })"
            )
            assert first["state"]["webgl"] and first["state"]["perspective"]
            volume = next(
                v
                for v in first["state"]["volumes"]
                if v["id"] == "database" and not v["projection"]
            )
            assert volume["radius"] < 350, volume
            assert first["positions"]["database"]["x"] == CENTERS["database"][0]
            page.screenshot(path=str(OUT / "02-tight-tilted-3d.png"))
            target = page.evaluate(
                """async () => {
                const T = await import('/spatial-three.vendor.js'),
                    rect = document.querySelector('.spatial-canvas').getBoundingClientRect(),
                    snapshot = graphDebug.spatial.camera,
                    camera = new T.PerspectiveCamera(43, rect.width/rect.height, 1, 100000),
                    volume = graphDebug.spatial.volumes.find(v => v.id==='database' && !v.projection);
                camera.position.fromArray(snapshot.position);
                camera.lookAt(new T.Vector3(...snapshot.target));
                camera.updateMatrixWorld();
                const point = new T.Vector3(volume.center.x, volume.center.y, volume.center.z + volume.radius * .85).project(camera);
                return {x:rect.x+(point.x+1)*rect.width/2,y:rect.y+(1-point.y)*rect.height/2};
            }"""
            )
            page.mouse.move(target["x"], target["y"])
            page.mouse.down()
            page.mouse.move(target["x"] + 70, target["y"] + 25, steps=12)
            page.mouse.up()
            ready()
            moved = page.evaluate("graphDebug.spatialPositions")
            dx = moved["database"]["x"] - first["positions"]["database"]["x"]
            dz = moved["database"]["z"] - first["positions"]["database"]["z"]
            assert abs(dx) + abs(dz) > 1
            for name in ["database", "files", "shares", "file_id", "file_name"]:
                assert abs(moved[name]["x"] - first["positions"][name]["x"] - dx) < 1e-6
                assert abs(moved[name]["z"] - first["positions"][name]["z"] - dz) < 1e-6
            assert moved["file_id"]["pinned"]
            for name in ["share", "notify", "store"]:
                assert moved[name] == first["positions"][name], (
                    "Unrelated branch moved",
                    name,
                )
            captions = page.locator(".spatial-label.region-label:visible").evaluate_all(
                """elements => elements.map(e => {
                const box=e.getBoundingClientRect();
                return {id:e.dataset.spatialRegion,layer:e.dataset.regionLayer,x:box.x,y:box.y,w:box.width,h:box.height};
            })"""
            )
            for index, caption in enumerate(captions):
                for other in captions[index + 1 :]:
                    assert (
                        caption["x"] + caption["w"] <= other["x"]
                        or other["x"] + other["w"] <= caption["x"]
                        or caption["y"] + caption["h"] <= other["y"]
                        or other["y"] + other["h"] <= caption["y"]
                    ), ("Caption overlap", caption, other)
            label = page.locator(
                '[data-spatial-region="database"][data-region-layer="data"]'
            )
            label.hover()
            caption = label.bounding_box()
            hit = page.evaluate(
                """point => document.elementFromPoint(point.x,point.y)?.closest('[data-spatial-region]')?.dataset.spatialRegion""",
                {
                    "x": caption["x"] + caption["width"] / 2,
                    "y": caption["y"] + caption["height"] / 2,
                },
            )
            assert hit == "database", ("Caption intercepted by another owner", hit)
            page.mouse.move(
                caption["x"] + caption["width"] / 2,
                caption["y"] + caption["height"] / 2,
            )
            page.mouse.down()
            page.mouse.move(
                caption["x"] + caption["width"] / 2 + 35,
                caption["y"] + caption["height"] / 2 + 8,
                steps=8,
            )
            page.mouse.up()
            ready()
            after_caption = page.evaluate("graphDebug.spatialPositions")
            for name in ["share", "notify", "store"]:
                assert after_caption[name] == moved[name], (
                    "Caption drag moved wrong owner",
                    name,
                )
            assert abs(after_caption["database"]["x"] - moved["database"]["x"]) > 1
            moved = after_caption
            result["captions"] = captions
            checks.append(
                "Nested circle captions do not overlap; exact caption drag moves only its target owner"
            )
            page.screenshot(path=str(OUT / "03-group-drag.png"))
            result["drag_delta"] = {"x": dx, "z": dz}
            checks.append(
                "Tilted 3D ring drag moves the complete branch by one delta and keeps pins"
            )
            layer("data")
            # The legacy execution facet shares the implementation plane.
            assert (
                page.evaluate(
                    "async () => { const {implementationFacet} = await import('/graph-classification.js'); return implementationFacet(graphDebug.graph.all.get('store')); }"
                )
                == "execution"
            )
            layer("implementation")
            assert page.evaluate("graphDebug.presentation.glyphs.has('share')")
            assert not page.evaluate("graphDebug.presentation.regions.has('share')")
            assert page.locator('[data-spatial-label="share"]').count() == 1
            page.screenshot(path=str(OUT / "04-hidden-children-fallback.png"))
            layer("data")
            layer("implementation")
            restored = page.evaluate("graphDebug.spatialPositions")
            for name in ["database", "files", "shares", "file_id", "file_name"]:
                assert restored[name] == moved[name], (
                    name,
                    restored[name],
                    moved[name],
                )
            checks.append(
                "Layer hide/restore uses same-ID fallback glyphs and restores child positions"
            )
            page.locator('#semantic [data-node-id="shares"]').evaluate("e => e.click()")
            page.locator("#viewport").focus()
            page.keyboard.press("Delete")
            ready()
            assert not page.evaluate("graphDebug.presentation.glyphs.has('shares')")
            page.click("#filter-toggle")
            page.locator("#hidden-elements > div").filter(
                has_text="Shares"
            ).get_by_role("button", name="Show again").click()
            ready()
            assert page.evaluate("graphDebug.presentation.glyphs.has('shares')")
            checks.append(
                "Explicit node exclusion and native restore retain the same identity"
            )
            page.wait_for_timeout(600)
            page.goto("about:blank")
            time.sleep(0.2)
            saved_analysis = json.loads(preferences["entries"][KEY + ":analysis"])
            saved_analysis["layers"]["projections"] = False
            preferences["entries"][KEY + ":analysis"] = json.dumps(saved_analysis)
            page.goto(url, wait_until="domcontentloaded")
            ready()
            assert page.evaluate("graphDebug.layers.projections") is False
            assert page.locator('[data-spatial-region="share"]').count() == 0
            assert page.locator('[data-spatial-label="share"]').count() == 1
            after = page.evaluate(
                "({ spatial:graphDebug.spatial, positions:graphDebug.spatialPositions })"
            )
            route_id = page.evaluate(
                "graphDebug.presentation.edges.find(e => e.id === 'share-notify' || e.members?.some(m=>m.id==='share-notify')).id"
            )
            route = next(
                port for port in after["spatial"]["edgePorts"] if port["id"] == route_id
            )
            point = after["positions"]["share"]
            assert all(
                abs(route["start"][axis] - point[axis]) < 1e-6
                for axis in ["x", "y", "z"]
            )
            page.screenshot(path=str(OUT / "05-projections-hidden.png"))
            checks.append(
                "Saved projection visibility hides projected rings and routes to the same-ID visible glyph"
            )
            assert not errors, errors
            result["passed"] = True
        except Exception as error:
            result["error"] = repr(error)
            page.screenshot(path=str(OUT / "failure.png"))
            result["debug"] = page.evaluate(
                "window.graphDebug ? ({layers:graphDebug.layers,spatial:graphDebug.spatial,positions:graphDebug.spatialPositions,regions:graphDebug.displayGraph?.regions}) : null"
            )
            raise
        finally:
            result.update(checks=checks, errors=errors)
            (OUT / "results.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            (OUT / "preferences.json").write_text(
                json.dumps(preferences, indent=2), encoding="utf-8"
            )
            (OUT / "requests.json").write_text(
                json.dumps(requests, indent=2), encoding="utf-8"
            )
            browser.close()
            server.shutdown()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
