"""Observe real scoped view controls without touching application or recording data."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

TRIAL = Path(
    r"C:/Users/Lvi_P/Documents/Work/CF/平台软著/VibeLensTrials/graph-quality-dialogue-20261104-01"
)
OUT = Path(__file__).resolve().parent
EVIDENCE = TRIAL / "review/remark-v2/results/remark-control"
URL = json.loads((EVIDENCE / "activate.json").read_text(encoding="utf-8"))["result"]["graph_url"]
TOKEN = parse_qs(urlsplit(URL).query)["vl_session"][0]
PRIVATE = TRIAL / "bo_stategraph/config/views/conversations" / (TOKEN + ".json")
DEFAULT = TRIAL / "bo_stategraph/config/views/local.json"
PROTECTED = json.loads((EVIDENCE / "protected-before.json").read_text(encoding="utf-8"))
paths = {name for name in PROTECTED if (TRIAL / name).is_file()}
paths.update(
    p.relative_to(TRIAL).as_posix()
    for p in (TRIAL / "bo_stategraph/data/recordings").glob("*.json")
)
paths.update(
    p.relative_to(TRIAL).as_posix() for p in (TRIAL / "bo_stategraph/data").glob("events.jsonl*")
)
paths.update(
    p.relative_to(TRIAL).as_posix()
    for p in (TRIAL / "bo_stategraph/config/views").rglob("*.json")
    if p != PRIVATE
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {name: digest(TRIAL / name) for name in sorted(paths)}


result = {
    "kind": "native-scoped-browser-preference-isolation",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "checks": {},
    "errors": [],
    "preference_requests": [],
    "actions": [],
}
before = snapshot()
private_before = digest(PRIVATE)
(OUT / "protected-before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
(OUT / "default-before.json").write_bytes(DEFAULT.read_bytes())

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1800, "height": 1200}, device_scale_factor=1)
    page.on(
        "pageerror", lambda error: result["errors"].append(str(error).replace(TOKEN, "[session]"))
    )

    def response(response):
        parts = urlsplit(response.url)
        if parts.path != "/api/preferences":
            return
        scoped = parse_qs(parts.query).get("vl_session", [None])[0] == TOKEN
        item = {
            "method": response.request.method,
            "status": response.status,
            "exact_session_scope": scoped,
        }
        try:
            item["revision"] = response.json().get("revision")
        except Exception:
            pass
        result["preference_requests"].append(item)

    page.on("response", response)
    try:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy", timeout=60000)
        result["checks"]["url_has_original_session"] = (
            parse_qs(urlsplit(page.url).query).get("vl_session", [None])[0] == TOKEN
        )
        result["initial"] = page.evaluate(
            "({view:document.querySelector('#analysis-view').value,layers:graphDebug.layers,camera:graphDebug.spatial?.camera})"
        )
        result["checks"]["private_custom_view_restored"] = result["initial"]["view"].startswith(
            "custom-vl-"
        )
        assert result["checks"]["private_custom_view_restored"]
        if page.locator("#recording-timeline").is_visible():
            page.locator(".trace-close").click()
            result["actions"].append("Close the private timeline panel")

        ruler = page.locator("#layer-controls canvas")
        bounds = ruler.bounding_box()
        order = page.evaluate("graphDebug.layers.order")
        row = order.index("rules")
        page.mouse.click(bounds["x"] + 22, bounds["y"] + 40 + row * 34 + 15)
        result["actions"].append("Toggle Rules through the native layer ruler")
        page.wait_for_function(
            "!graphDebug.layers.visible.includes('rules') && !graphDebug.layoutBusy", timeout=60000
        )
        if page.locator("#layered-toggle").inner_text().strip() == "2D":
            page.locator("#layered-toggle").click()
        page.wait_for_function(
            "graphDebug.spatial?.perspective && !graphDebug.layoutBusy", timeout=60000
        )
        page.locator("#fit").click()
        page.wait_for_function("!graphDebug.layoutBusy", timeout=60000)
        result["camera_before"] = page.evaluate("graphDebug.spatial.camera")
        canvas = page.locator(".spatial-canvas")
        box = canvas.bounding_box()
        x, y = box["x"] + box["width"] * 0.15, box["y"] + box["height"] * 0.65
        result["gesture_hit"] = page.evaluate(
            "p=>({tag:document.elementFromPoint(p.x,p.y)?.tagName,cls:document.elementFromPoint(p.x,p.y)?.className,nearest:Math.min(...[...document.querySelectorAll('button[data-node-id]')].map(e=>Math.hypot(Number(e.dataset.screenX)-p.x,Number(e.dataset.screenY)-p.y)))})",
            {"x": x, "y": y},
        )
        assert result["gesture_hit"]["cls"] == "spatial-canvas"
        assert result["gesture_hit"]["nearest"] > 80
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 180, y - 160, steps=20)
        page.mouse.up()
        page.wait_for_function(
            "previous=>JSON.stringify(graphDebug.spatial.camera)!==JSON.stringify(previous)",
            arg=result["camera_before"],
            timeout=15000,
        )
        result["actions"].append("Orbit the private3D camera using a verified blank canvas drag")
        result["camera_after"] = page.evaluate("graphDebug.spatial.camera")
        page.screenshot(path=str(OUT / "scoped-private-3d.png"), full_page=True)
        page.locator("#layered-toggle").click()
        page.wait_for_function(
            "document.querySelector('#layered-toggle').textContent.trim()==='2D' && !graphDebug.layoutBusy",
            timeout=60000,
        )
        page.locator("#fit").click()
        page.wait_for_function(
            "document.querySelector('#layout-status').textContent.includes('已保存') || document.querySelector('#layout-status').textContent.includes('saved')",
            timeout=30000,
        )
        result["final"] = page.evaluate(
            "({view:document.querySelector('#analysis-view').value,layers:graphDebug.layers,camera:graphDebug.camera})"
        )
        result["checks"]["native_private_visibility_changed"] = (
            "rules" not in result["final"]["layers"]["visible"]
        )
        result["checks"]["native_private_camera_changed"] = (
            result["camera_before"] != result["camera_after"]
        )
    except Exception as error:
        result["errors"].append(str(error).replace(TOKEN, "[session]"))
        page.screenshot(path=str(OUT / "failure.png"), full_page=True)
    finally:
        browser.close()

after = snapshot()
(OUT / "protected-after.json").write_text(json.dumps(after, indent=2), encoding="utf-8")
(OUT / "default-after.json").write_bytes(DEFAULT.read_bytes())
result["changed_protected"] = [name for name in before if before[name] != after[name]]
result["protected_file_count"] = len(before)
result["original_protected_file_count"] = sum((TRIAL / name).is_file() for name in PROTECTED)
result["recording_file_count"] = len(list((TRIAL / "bo_stategraph/data/recordings").glob("*.json")))
result["checks"]["all_protected_bytes_unchanged"] = not result["changed_protected"]
result["checks"]["default_bytes_unchanged"] = (
    before["bo_stategraph/config/views/local.json"]
    == after["bo_stategraph/config/views/local.json"]
)
result["checks"]["private_file_persisted_native_changes"] = private_before != digest(PRIVATE)
result["checks"]["all_preference_requests_exactly_scoped"] = bool(
    result["preference_requests"]
) and all(item["exact_session_scope"] for item in result["preference_requests"])
result["checks"]["scoped_preferences_get_and_post_successful"] = all(
    any(
        item["method"] == method and item["status"] == 200 for item in result["preference_requests"]
    )
    for method in ("GET", "POST")
)
result["finished_at"] = datetime.now(timezone.utc).isoformat()
result["valid"] = all(result["checks"].values()) and not result["errors"]
(OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "valid": result["valid"],
            "checks": result["checks"],
            "errors": result["errors"],
            "protected_files": len(before),
            "preference_requests": len(result["preference_requests"]),
        },
        ensure_ascii=False,
    )
)
assert result["valid"]
