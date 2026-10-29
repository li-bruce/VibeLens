"""Exercise engineering structure in the actual 2D/3D viewer and save evidence.

Requires Python Playwright and a local Chromium executable (--browser). The
synthetic source fixture is isolated; viewer requests must produce zero events.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "tools"), str(ROOT / "skills/vibelens/scripts")]
from test_engineering_structure import fixture
from bo_observer.service import GraphSession, make_server
from bo_observer.code_graph.index import identity


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--out", default=".validation/engineering-browser")
    args = parser.parse_args()
    output = (ROOT / args.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / "temp"
    temporary.mkdir(exist_ok=True)
    os.environ["TMP"] = os.environ["TEMP"] = str(temporary)
    checks, errors = {}, []
    with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
        root = Path(folder)
        fixture(root)
        session = GraphSession(root)
        server = make_server(session, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=args.browser,
                    args=["--enable-unsafe-swiftshader"])
                page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=1)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/graph?lang=en")
                page.wait_for_function("window.graphDebug?.graph?.boxes.length > 0")
                # The live viewer polls continuously; use actual graph/layout readiness.
                page.wait_for_function("!graphDebug.layoutBusy")

                def select(key):
                    page.locator("#semantic [data-node-id]").evaluate_all(
                        "(items, id) => items.find(item => item.dataset.nodeId === id).click()", key)

                def expand(key):
                    select(key)
                    page.click("#selection-menu")
                    page.click("#node-expand")
                    page.wait_for_function("!graphDebug.layoutBusy")

                def shot(name):
                    page.screenshot(path=str(output / (name + ".png")), full_page=True)

                page.select_option("#analysis-view", "project")
                page.wait_for_function("graphDebug.view.code_structure?.projection === 'project'")
                page.wait_for_function("!graphDebug.layoutBusy")
                page.wait_for_function("graphDebug.camera.scale < 0.9 && !graphDebug.layoutBusy")
                checks["first_project_view_fits_automatically"] = True
                checks["engineering_projection"] = page.evaluate("({nodes: graphDebug.view.code_structure.nodes.length, edges: graphDebug.view.code_structure.edges.length})")
                assert page.evaluate("graphDebug.view.code_structure.nodes.every(node => !['function','class','parameter'].includes(node.code_role))")
                shot("01-project-tree")
                expand(identity("directory", "src"))
                page.click("#fit")
                assert page.locator(f'#semantic [data-node-id="{identity("file", "src/routes.py")}"]').count() == 1
                shot("02-files-and-dependencies")
                select(identity("file", "src/routes.py"))
                page.click("#selection-menu")
                page.click("#source")
                page.wait_for_function("document.querySelector('#source-code').textContent.includes('def share')")
                assert "from .access import allow" in page.locator("#source-code").inner_text()
                shot("03-source-file")
                page.keyboard.press("Escape")
                checks["source_file"] = True
                page.click("#layered-toggle")
                page.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
                checks["three_dimensional"] = page.evaluate("({webgl: graphDebug.spatial.webgl, planes: graphDebug.spatial.layerPlanes})")
                assert checks["three_dimensional"]["webgl"]
                shot("04-project-3d")
                page.select_option("#analysis-view", "code")
                page.wait_for_function("graphDebug.view.code_structure?.projection === 'all'")
                page.wait_for_function("!graphDebug.layoutBusy")
                expand(identity("file", "src/routes.py"))
                page.click("#fit")
                page.wait_for_function("!graphDebug.layoutBusy")
                assert page.locator(f'#semantic [data-node-id="{identity("symbol", "src/routes.py::share")}"]').count() == 1
                plane_ids = page.evaluate("graphDebug.spatial.layerPlanes.map(layer => layer.id)")
                assert "project" in plane_ids and "code" in plane_ids
                checks["cross_layer_planes"] = plane_ids
                canvas = page.locator(".spatial-canvas").bounding_box()
                page.mouse.move(canvas["x"] + canvas["width"] * 0.88, canvas["y"] + canvas["height"] * 0.60)
                page.mouse.down()
                page.mouse.move(canvas["x"] + canvas["width"] * 0.78, canvas["y"] + canvas["height"] * 0.35, steps=20)
                page.mouse.up()
                page.wait_for_function("Math.abs(graphDebug.spatial.camera.position[0] - graphDebug.spatial.camera.target[0]) > 10")
                checks["pointer_camera_rotation"] = True
                checks["cross_layer"] = page.evaluate("graphDebug.view.code_structure.edges.some(edge => edge.code_relation === 'defines')")
                assert checks["cross_layer"]
                shot("05-files-to-code-symbols")
                page.click("#layered-toggle")
                page.select_option("#analysis-view", "project")
                page.wait_for_function("graphDebug.view.code_structure?.projection === 'project'")
                page.wait_for_function("!graphDebug.layoutBusy")
                revision = page.evaluate("graphDebug.view.code_structure.revision")
                before = page.evaluate("graphDebug.graph.boxes.map(b => ({id:b.id,x:b.x,y:b.y}))")
                (root / "src/added.py").write_text("def added(value): return value\n")
                page.wait_for_function("revision => graphDebug.view.code_structure?.revision !== revision", arg=revision)
                page.wait_for_function("!graphDebug.layoutBusy")
                assert page.evaluate("graphDebug.view.code_structure.nodes.some(n => n.project_path === 'src/added.py')")
                after = page.evaluate("graphDebug.graph.boxes.map(b => ({id:b.id,x:b.x,y:b.y}))")
                positions = {item["id"]: (item["x"], item["y"]) for item in after}
                assert all(positions.get(item["id"]) == (item["x"], item["y"]) for item in before)
                checks["automatic_refresh_keeps_positions"] = True
                shot("06-after-code-update")
                page.reload()
                page.wait_for_function("graphDebug.view?.code_structure?.projection === 'project'")
                page.wait_for_function("!graphDebug.layoutBusy")
                checks["expanded_after_reload"] = page.locator(f'#semantic [data-node-id="{identity("file", "src/routes.py")}"]').count() == 1
                assert checks["expanded_after_reload"]
                expand(identity("directory", "src"))
                page.get_by_text("View saved to project", exact=True).wait_for()
                page.reload()
                page.wait_for_function("window.graphDebug?.view?.code_structure?.projection === 'project'")
                page.wait_for_function("!graphDebug.layoutBusy")
                checks["collapsed_after_reload"] = page.locator(f'#semantic [data-node-id="{identity("file", "src/routes.py")}"]').count() == 0
                assert checks["collapsed_after_reload"]
                expand(identity("directory", "src"))
                page.select_option("#language", "zh-CN")
                page.wait_for_function("document.documentElement.lang === 'zh-CN'")
                page.wait_for_function("graphDebug.view?.code_structure?.projection === 'project'")
                assert page.locator('#analysis-view option[value="project"]').inner_text() == "工程结构"
                checks["chinese_interface"] = True
                shot("07-project-chinese")
                checks["observer_events"] = session.sequence
                assert session.sequence == 0
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            session.close()
            (output / "report.json").write_text(json.dumps({"checks": checks, "errors": errors}, indent=2))
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
