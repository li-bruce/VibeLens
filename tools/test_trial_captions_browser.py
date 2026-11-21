"""Check real bilingual graph labels, node selection and on-demand full source.

The specification contains reviewed names and one current source binding. Browser
actions use the normal search and context menu; no graph data is injected and no
personal configuration is restored. Each run writes a new evidence directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import traceback
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright


READY = """() => window.graphDebug?.graph && !graphDebug.sourceBusy &&
    !graphDebug.layoutBusy && !graphDebug.geometryBusy"""


def settle(page):
    page.wait_for_function(READY, timeout=60000)


def reveal(page, identity):
    """Use the visible search result to unfold the node's actual ancestry."""
    page.fill("#node-search", identity)
    results = page.locator("#search-results button")
    results.first.wait_for(state="visible")
    # Partial text search may legitimately return guard_prepare_download beside
    # prepare_download. Read the result's identity instead of guessing from its
    # translated caption or shared source symbol.
    identities = results.evaluate_all("buttons => buttons.map(b => b.dataset.resultId)")
    assert identities.count(identity) == 1, (identity, identities)
    results.nth(identities.index(identity)).click()
    settle(page)
    assert identity in page.evaluate("graphDebug.selectedNodes"), identity
    page.click("#fit")
    settle(page)
    point = page.evaluate(
        """id => {
      const e=[...document.querySelectorAll('#semantic [data-node-id]')]
        .find(e=>e.dataset.nodeId===id);
      return e ? {x:+e.dataset.screenX,y:+e.dataset.screenY,caption:e.textContent} : null;
    }""",
        identity,
    )
    assert point, identity
    return point


def open_menu(page, identity, action):
    point = reveal(page, identity)
    page.mouse.click(point["x"], point["y"], button="right")
    assert identity in page.evaluate("graphDebug.selectedNodes"), identity
    page.click(action)
    page.locator("#node-details").wait_for(state="visible")
    return point


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", required=True)
parser.add_argument("--project", type=Path, required=True)
parser.add_argument("--spec", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
args.out.mkdir(parents=True, exist_ok=False)
report = {"valid": False, "checks": [], "errors": [], "source_responses": []}


def source_response(response):
    if (
        urlsplit(response.url).path in {"/api/source", "/api/code/source"}
        and response.ok
    ):
        report["source_responses"].append(
            {"url": response.url, "data": response.json()}
        )


try:
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
            args=["--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        page.on("response", source_response)
        for locale in ("zh-CN", "en"):
            page.goto(
                args.url.split("?")[0] + "?lang=" + locale,
                wait_until="domcontentloaded",
            )
            settle(page)
            if page.locator("#name-mode").get_attribute("aria-checked") != "true":
                page.click("#name-mode")
                settle(page)
            for mode in ("2D", "3D"):
                if page.locator("#layered-toggle").inner_text() != mode:
                    page.click("#layered-toggle")
                    settle(page)
                for index, target in enumerate(spec["targets"]):
                    page.select_option("#analysis-view", target["preset"])
                    settle(page)
                    page.click("#collapse")
                    settle(page)
                    point = open_menu(page, target["id"], "#details")
                    title = page.locator("#detail-title").inner_text()
                    expected = target["labels"][locale]
                    assert title == point["caption"] == expected, (
                        target["id"],
                        locale,
                        mode,
                        title,
                        point,
                    )
                    screenshot = f"{locale}-{mode}-{index}.png"
                    page.screenshot(path=str(args.out / screenshot))
                    report["checks"].append(
                        {
                            "id": target["id"],
                            "locale": locale,
                            "mode": mode,
                            "caption": title,
                            "screenshot": screenshot,
                        }
                    )
                    page.click("#close-detail")

        source = spec["source"]
        page.select_option("#analysis-view", source["preset"])
        settle(page)
        if page.locator("#layered-toggle").inner_text() != "2D":
            page.click("#layered-toggle")
            settle(page)
        open_menu(page, source["node"], "#source")
        mark = (
            page.locator("#source-code mark")
            .filter(has_text=source["declaration"])
            .first
        )
        mark.wait_for(state="attached")
        expected = (args.project / source["path"]).read_text(encoding="utf-8")
        response = next(
            item
            for item in report["source_responses"]
            if parse_qs(urlsplit(item["url"]).query).get("path") == [source["path"]]
        )
        assert response["data"]["source"] == expected
        mark.scroll_into_view_if_needed()
        box, panel = mark.bounding_box(), page.locator("#node-details").bounding_box()
        assert (
            box
            and panel
            and box["y"] >= panel["y"]
            and box["y"] + box["height"] <= panel["y"] + panel["height"]
        )
        page.screenshot(path=str(args.out / "source-visible.png"))
        page.locator("#node-details").screenshot(
            path=str(args.out / "source-panel.png")
        )
        report["source"] = {
            **source,
            "full_file_loaded": True,
            "highlight": mark.inner_text(),
            "sha256": hashlib.sha256(expected.encode()).hexdigest(),
            "bounds": box,
            "panel": panel,
        }
        assert not report["errors"], report["errors"]
        report["valid"] = True
        browser.close()
except Exception as error:
    report["failure"] = str(error)
    report["traceback"] = traceback.format_exc()
finally:
    for item in report["source_responses"]:
        content = item["data"].pop("source", "")
        item["source_sha256"] = hashlib.sha256(content.encode()).hexdigest()
    (args.out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
print(
    json.dumps(
        {
            "valid": report["valid"],
            "checks": len(report["checks"]),
            "failure": report.get("failure"),
        }
    )
)
raise SystemExit(not report["valid"])
