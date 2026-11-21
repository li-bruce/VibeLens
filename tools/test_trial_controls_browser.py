"""Exercise viewer controls against an actual trial, without response fixtures.

Changes are limited to personal view preferences. Native business effects and
recording completeness are verified separately. Every run needs a new directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import traceback
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument(
    "--interaction-only",
    action="store_true",
    help="Diagnose UI interactions without claiming live producer exclusion acceptance",
)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
result = {"valid": False, "checks": [], "page_errors": []}
result["scope"] = (
    "interaction_diagnosis" if args.interaction_only else "native_control_acceptance"
)
result["native_exclusion_status"] = (
    "not_checked" if args.interaction_only else "pending"
)
READY = """() => window.graphDebug?.graph && !graphDebug.sourceBusy &&
    !graphDebug.layoutBusy && !graphDebug.geometryBusy"""


def settle(page):
    """Wait for the source index, layout and accessible coordinates together."""
    try:
        page.wait_for_function(READY, timeout=60000)
    except Exception:
        result["failure_ui"] = page.evaluate(
            """() => ({url:location.href,
            sourceBusy:window.graphDebug?.sourceBusy, layoutBusy:window.graphDebug?.layoutBusy,
            geometryBusy:window.graphDebug?.geometryBusy, spatial:window.graphDebug?.spatial,
            view:document.querySelector('#analysis-view')?.value,
            connection:document.querySelector('#connection')?.textContent})"""
        )
        page.screenshot(path=str(args.out / "failure.png"))
        raise


def view(page, name):
    page.select_option("#analysis-view", name)
    settle(page)
    page.click("#collapse")
    page.click("#fit")
    settle(page)


def point(page, identity):
    """Return the actual rendered hit point; do not guess world coordinates."""
    return page.wait_for_function(
        """id => {
        const el = [...document.querySelectorAll('#semantic [data-node-id]')]
            .find(item => item.dataset.nodeId === id);
        const x=Number(el?.dataset.screenX), y=Number(el?.dataset.screenY);
        return el && Number.isFinite(x) && Number.isFinite(y) ? {x,y} : false;
    }""",
        arg=identity,
    ).json_value()


def drag(page, start, end):
    page.mouse.move(start["x"], start["y"])
    page.mouse.down()
    page.mouse.move(end["x"], end["y"], steps=14)
    page.mouse.up()
    settle(page)


def preferences(page):
    """Read the project's acknowledged settings, not only in-memory UI state."""
    response = page.request.get(args.url.split("/graph")[0] + "/api/preferences")
    assert response.ok, response.status
    return response.json()


def native_rows():
    """Fingerprint native persisted rows without recording account/password data."""
    with sqlite3.connect(
        args.database.resolve().as_uri() + "?mode=ro", uri=True
    ) as connection:
        connection.execute("BEGIN")
        tables = sorted(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
        result = {}
        for name in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            rows = sorted(
                json.dumps(row, default=repr)
                for row in connection.execute("SELECT * FROM " + quoted)
            )
            result[name] = {
                "rows": len(rows),
                "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
            }
        return result


def observer_requests(value):
    """Find actual observed HTTP fields for the viewer's own control routes."""
    forbidden = (
        "/api/view",
        "/api/preferences",
        "/api/recordings",
        "/api/source",
        "/api/code",
        "/api/bo",
    )
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in (
                "route",
                "path",
                "http.route",
                "http.url",
                "url.full",
            ) and isinstance(item, str):
                route = urlsplit(item).path
                if any(
                    route == path or route.startswith(path + "/") for path in forbidden
                ):
                    found.append({key: item})
            found.extend(observer_requests(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(observer_requests(item))
    return found


def wait_preference(page, predicate):
    """Watch successful saves and recheck the current server document."""
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/api/preferences" in response.url
        and response.status == 200,
        timeout=30000,
    ) as saved:
        predicate()
    receipt = saved.value.json()
    assert receipt.get("revision", 0) > 0
    return receipt


def menu(page, identity, action):
    p = point(page, identity)
    page.mouse.click(p["x"], p["y"], button="right")
    page.click(action)


try:
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
            args=["--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
        page.goto(args.url, wait_until="domcontentloaded")
        settle(page)
        result["preferences_before"] = preferences(page)
        result["initial_events"] = page.evaluate("graphDebug.view.events.length")
        if not args.interaction_only:
            assert result["initial_events"] > 0, (
                "Native exclusion acceptance requires a collector with actual producer history; "
                "an idle diagnostic observer cannot establish this check"
            )
        result["native_before"] = native_rows()
        if page.locator("#recording-timeline").is_visible():
            page.click("#replay-timeline")
        if page.locator("#layered-toggle").inner_text() == "3D":
            page.click("#layered-toggle")
        view(page, "business")

        # Turning on another layer creates a custom selection, then saves it.
        index = page.evaluate("graphDebug.layers.order.indexOf('entry')")
        assert index >= 0
        ruler = page.locator("#layer-controls canvas").bounding_box()
        page.mouse.click(ruler["x"] + 22, ruler["y"] + 40 + index * 34 + 16)
        settle(page)
        assert page.locator("#analysis-view").input_value() == "custom-draft"
        assert sorted(page.evaluate("graphDebug.layers.visible")) == [
            "business",
            "entry",
        ]
        page.click("#filter-toggle")
        page.fill("#custom-view-name", "P7 — Business and entry points")
        wait_preference(
            page, lambda: page.locator('#save-view button[type="submit"]').click()
        )
        saved_id = page.locator("#analysis-view").input_value()
        page.click("#close-filters")
        page.reload(wait_until="domcontentloaded")
        settle(page)
        assert page.locator("#analysis-view").input_value() == saved_id
        assert sorted(page.evaluate("graphDebug.layers.visible")) == [
            "business",
            "entry",
        ]
        result["checks"].append({"custom_view_save_reload": saved_id})
        page.screenshot(path=str(args.out / "custom-view.png"))

        # The same source identities remain present in both display languages.
        view(page, "api")
        identities = page.evaluate("graphDebug.displayGraph.boxes.map(b=>b.id).sort()")
        captions = {}
        for locale in ("en", "zh-CN"):
            if page.locator("#language").input_value() != locale:
                # The old document can briefly retain graphDebug after the URL
                # changes. Wait for navigation before inspecting new controls.
                with page.expect_navigation(wait_until="domcontentloaded"):
                    page.select_option("#language", locale)
            settle(page)
            assert (
                page.evaluate("graphDebug.displayGraph.boxes.map(b=>b.id).sort()")
                == identities
            )
            if page.locator("#name-mode").get_attribute("aria-checked") != "true":
                wait_preference(page, lambda: page.click("#name-mode"))
            captions[locale] = page.locator("#semantic [data-node-id]").evaluate_all(
                "nodes=>nodes.map(n=>({id:n.dataset.nodeId,text:n.textContent}))"
            )
        before = page.evaluate("graphDebug.graph.boxes.map(b=>[b.id,b.x,b.y])")
        wait_preference(page, lambda: page.click("#name-mode"))
        assert page.locator("#name-mode").get_attribute("aria-checked") == "false"
        assert page.evaluate("graphDebug.graph.boxes.map(b=>[b.id,b.x,b.y])") == before
        wait_preference(page, lambda: page.click("#name-mode"))
        result["checks"].append({"locale_identity_and_label_toggle": captions})

        for mode in ("2D", "3D"):
            if page.locator("#layered-toggle").inner_text() != mode:
                page.click("#layered-toggle")
            view(page, "business")
            canvas = page.locator("#canvas-host").bounding_box()
            page.click("#tool-pan")
            camera_js = "graphDebug.layers.enabled ? graphDebug.spatial.camera : graphDebug.camera"
            old_camera = page.evaluate(camera_js)
            drag(
                page,
                {"x": canvas["x"] + 350, "y": canvas["y"] + 300},
                {"x": canvas["x"] + 410, "y": canvas["y"] + 330},
            )
            assert page.evaluate(camera_js) != old_camera, (
                mode + " pan did not move camera"
            )
            page.click("#fit")
            settle(page)
            page.click("#tool-select")
            points = page.locator("#semantic [data-node-id]").evaluate_all(
                """nodes=>nodes
                .map(n=>({id:n.dataset.nodeId,x:+n.dataset.screenX,y:+n.dataset.screenY}))"""
            )
            visible = [
                p
                for p in points
                if canvas["x"] + 200 < p["x"] < canvas["x"] + canvas["width"] - 240
                and canvas["y"] + 60 < p["y"] < canvas["y"] + canvas["height"] - 100
            ]
            assert len(visible) >= 2, (
                mode,
                "fewer than two unobscured business nodes",
                points,
            )
            drag(
                page,
                {
                    "x": min(p["x"] for p in visible) - 35,
                    "y": min(p["y"] for p in visible) - 35,
                },
                {
                    "x": max(p["x"] for p in visible) + 35,
                    "y": max(p["y"] for p in visible) + 35,
                },
            )
            group = page.evaluate("graphDebug.selectedNodes")
            assert len(group) >= 2, mode + " marquee failed"
            positions = """ids=>Object.fromEntries(ids.map(id=>[id,graphDebug.layers.enabled
                ? graphDebug.spatialPositions[id] : {x:graphDebug.graph.byId.get(id).x,
                y:graphDebug.graph.byId.get(id).y}]))"""
            old = page.evaluate(positions, group)
            p = point(page, group[0])
            drag(page, p, {"x": p["x"] + 40, "y": p["y"] + 18})
            current = page.evaluate(positions, group)
            deltas = [current[i]["x"] - old[i]["x"] for i in group]
            assert abs(deltas[0]) > 1 and all(abs(d - deltas[0]) < 0.01 for d in deltas)
            assert page.evaluate("getSelection().toString()") == ""
            result["checks"].append(
                {"mode": mode, "pan": True, "group_drag": group, "delta": deltas[0]}
            )
            page.screenshot(path=str(args.out / ("drag-" + mode + ".png")))

        # Personal notes and alias identity survive a reload and later iteration.
        view(page, "business")
        identity = page.evaluate("[...graphDebug.presentation.glyphs][0]")
        assert identity
        menu(page, identity, "#annotate")
        note = "P7 review: inspect the native entry and its downstream effects."
        page.fill("#node-note", note)
        page.check("#node-core")
        wait_preference(
            page, lambda: page.locator('#annotation-form button[type="submit"]').click()
        )
        if page.locator("#node-details").is_visible():
            page.click("#close-detail")
        page.reload(wait_until="domcontentloaded")
        settle(page)
        menu(page, identity, "#annotate")
        assert page.locator("#node-note").input_value() == note
        assert page.locator("#node-core").is_checked()
        page.screenshot(path=str(args.out / "retained-annotation.png"))
        page.click("#close-detail")
        result["checks"].append({"retained_annotation_node": identity, "note": note})
        result["preferences_after"] = preferences(page)
        result["final_events"] = page.evaluate("graphDebug.view.events.length")
        # Normal worker polling can add legitimate read observations. A raw
        # event-count equality would confuse those with viewer self-observation.
        result["native_after"] = native_rows()
        result["observer_requests"] = observer_requests(
            page.evaluate("graphDebug.view.events")
        )
        assert (
            result["native_after"] == result["native_before"]
        ), "Viewer actions changed native data"
        assert not result[
            "observer_requests"
        ], "Viewer control requests leaked into business observations"
        if not args.interaction_only:
            result["native_exclusion_status"] = "passed"
        assert not result["page_errors"]
        browser.close()
    result["valid"] = True
except Exception as error:
    result.update(failure=str(error), traceback=traceback.format_exc())
    try:
        result["failure_ui"] = page.evaluate(
            """() => ({url:location.href,
            sourceBusy:window.graphDebug?.sourceBusy, layoutBusy:window.graphDebug?.layoutBusy,
            geometryBusy:window.graphDebug?.geometryBusy, spatial:window.graphDebug?.spatial,
            view:document.querySelector('#analysis-view')?.value,
            connection:document.querySelector('#connection')?.textContent})"""
        )
        page.screenshot(path=str(args.out / "failure.png"))
    except Exception as inspection_error:
        result["inspection_error"] = str(inspection_error)
(args.out / "result.json").write_text(
    json.dumps(result, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({k: v for k, v in result.items() if not k.startswith("preferences")}))
raise SystemExit(not result["valid"])
