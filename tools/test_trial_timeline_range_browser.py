"""Check a nonempty time selection against an actual recording's event identities.

The interval comes from measured event times, rather than a fixed fraction of the
recording duration. A long idle tail must not turn this into an empty-range test.
Only pointer/toolbar controls change the viewer; source events remain untouched.
"""

import argparse
import json
from pathlib import Path
import traceback

from playwright.sync_api import sync_playwright


def run(url, recording, output):
    """Retain the source points, actual brush bounds and exact selected identities."""
    output.mkdir(parents=True, exist_ok=False)
    result = {"valid": False, "recording": recording, "page_errors": []}
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                channel="chrome", headless=True, args=["--enable-unsafe-swiftshader"]
            )
            page = browser.new_page(viewport={"width": 1600, "height": 1050})
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function(
                "id => [...document.querySelector('#record-list').options]"
                ".some(option => option.value === id)",
                arg=recording,
                timeout=60000,
            )
            page.select_option("#record-list", recording)
            page.wait_for_function(
                "id => graphDebug.view?.replay?.id === id", arg=recording, timeout=60000
            )
            if not page.locator("#recording-timeline").is_visible():
                page.click("#replay-timeline")
            page.select_option("#replay-grain", "events")
            page.select_option(".trace-scope", "all")
            page.select_option(".trace-depth", "all")
            if page.locator(".trace-single").get_attribute("aria-pressed") == "true":
                page.click(".trace-single")
            if page.locator(".trace-clear").is_enabled():
                page.click(".trace-clear")
            page.click(".trace-fit")
            page.wait_for_function("graphDebug.timeline?.geometry && !graphDebug.timeline.zooming")
            before = page.evaluate("graphDebug.timeline")
            points = before["points"]
            times = sorted({point["time"] for point in points})
            assert len(times) >= 4, "Recording needs distinct measured event times"
            lower, upper = times[len(times) // 4], times[3 * len(times) // 4]
            assert upper > lower
            bounds = page.locator("#recording-timeline canvas").bounding_box()
            window = before["window"]
            geometry = before["geometry"]

            def screen_x(value):
                return (
                    bounds["x"]
                    + geometry["left"]
                    + geometry["plot"]
                    * ((value - window["start"]) / (window["end"] - window["start"]))
                )

            page.keyboard.down("Shift")
            page.mouse.move(screen_x(lower), bounds["y"] + 38)
            page.mouse.down()
            page.mouse.move(screen_x(upper), bounds["y"] + 38, steps=16)
            page.mouse.up()
            page.keyboard.up("Shift")
            selected = page.evaluate("graphDebug.timeline")
            assert selected["range"], "Pointer drag did not create a time interval"
            low, high = sorted(selected["range"])
            expected = sorted(point["raw"] for point in points if low <= point["time"] <= high)
            assert len(expected) > 1, "This check must select multiple actual events"
            assert len(expected) < len(points), "The selected interval must exclude other events"
            page.click(".trace-loop")
            assert page.locator("#replay-loop").is_checked()
            actual = page.evaluate("graphDebug.timeline")
            actual_ids = sorted(point["raw"] for point in actual["points"])
            result.update(
                measured_points=points,
                requested_time_range=[lower, upper],
                pointer_time_range=[low, high],
                expected_raw_indices=expected,
                actual_raw_indices=actual_ids,
                source_event_count=len(points),
            )
            assert actual_ids == expected, "Loop includes unrelated events or omits selected events"
            page.screenshot(path=str(output / "selected-native-interval.png"))
            page.click(".trace-clear")
            assert not page.locator("#replay-loop").is_checked()
            restored = page.evaluate("graphDebug.timeline.points")
            assert restored == points, "Clearing selection did not restore the recorded points"
            assert not result["page_errors"], result["page_errors"]
            browser.close()
        result["valid"] = True
    except Exception as error:
        result.update(failure=str(error), traceback=traceback.format_exc())
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--recording", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.url, args.recording, args.out)
    print(
        json.dumps(
            {
                "valid": report["valid"],
                "failure": report.get("failure"),
                "selected_events": len(report.get("actual_raw_indices", [])),
            }
        )
    )
    raise SystemExit(not report["valid"])
