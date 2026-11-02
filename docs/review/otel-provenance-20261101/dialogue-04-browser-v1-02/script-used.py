"""Exercise a running trial through its actual UI and compare native HTTP facts.

Caller-supplied W3C trace IDs join browser responses to recorded HTTP boundaries.
They identify technical requests and never supply an authenticated actor. The
script changes synthetic business data and viewer preferences, not project code.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_card(page, name):
    return page.locator("article.file-row").filter(
        has=page.get_by_role("heading", name=name, exact=True)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    app = args.app.rstrip("/")
    errors, responses, actions, checks = [], [], [], []
    started = time.time()
    filename = f"browser-{int(started)}.txt"
    payload = b"Actual browser upload, committed notice, sharing and download.\n"
    fixture = out / filename
    fixture.write_bytes(payload)

    def collect(response):
        request = response.request
        path = urlsplit(response.url).path
        if urlsplit(response.url).netloc != urlsplit(app).netloc:
            return
        if request.method != "POST" and not path.endswith("/download"):
            return
        header = request.headers.get("traceparent", "")
        responses.append(
            {
                "method": request.method,
                "path": path,
                "status": response.status,
                "trace_id": header.split("-")[1] if header else None,
            }
        )

    def action(page, name, callback):
        trace_id, parent_id = secrets.token_hex(16), secrets.token_hex(8)
        actions.append({"name": name, "trace_id": trace_id, "external_parent_span": parent_id})
        page.context.set_extra_http_headers({"traceparent": f"00-{trace_id}-{parent_id}-01"})
        try:
            return callback()
        finally:
            page.context.set_extra_http_headers({})

    def login(page, name):
        page.goto(app)
        page.wait_for_load_state("networkidle")
        page.get_by_label("账号", exact=True).fill(name)
        page.get_by_label("密码", exact=True).fill("Trial2026!")
        action(
            page,
            "login-" + name,
            lambda: page.get_by_role("button", name="登录", exact=True).click(),
        )
        page.wait_for_load_state("networkidle")

    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, executable_path=args.browser)
        try:

            def page():
                opened = browser.new_page(
                    viewport={"width": 1520, "height": 1060}, accept_downloads=True
                )
                opened.on("pageerror", lambda error: errors.append(str(error)))
                opened.on("response", collect)
                return opened

            graph, owner, admin, recipient = page(), page(), page(), page()
            graph.goto(args.graph)
            graph.wait_for_function(
                "typeof graphDebug !== 'undefined' && graphDebug.timeline?.geometry"
            )
            if graph.locator("#layered-toggle").get_attribute("aria-pressed") == "true":
                graph.locator("#layered-toggle").click()
                graph.wait_for_function("!graphDebug.spatial?.perspective")
            graph.screenshot(path=str(out / "00-live-graph.png"))
            assert graph.locator("#record-stop").is_disabled(), "A previous recording is active"
            graph.locator("#record-start").click()
            graph.wait_for_function("graphDebug.timeline?.source === 'recording'")
            login(owner, "member1")
            owner.locator('input[type="file"]').set_input_files(str(fixture))
            action(
                owner,
                "upload",
                lambda: owner.get_by_role("button", name="上传并提交审核", exact=True).click(),
            )
            owner.wait_for_load_state("networkidle")
            own = file_card(owner, filename)
            expect(own).to_be_visible()
            identity = (
                own.get_by_role("link", name="文件信息", exact=True)
                .get_attribute("href")
                .rsplit("/", 1)[1]
            )
            owner.screenshot(path=str(out / "01-uploaded.png"))
            download = app + "/api/files/" + identity + "/download"
            login(recipient, "member2")
            denied = action(recipient, "download-before-approval", lambda: recipient.goto(download))
            assert denied.status == 403
            login(admin, "admin1")
            form = admin.locator('form[action="/command/review"]').filter(
                has=admin.locator(f'input[name="file_id"][value="{identity}"]')
            )
            action(
                admin,
                "approve",
                lambda: form.get_by_role("button", name="通过", exact=True).click(),
            )
            expect(file_card(admin, filename)).to_contain_text("审核结果待投递", timeout=2500)
            admin.screenshot(path=str(out / "02-review-wait.png"))
            expect(file_card(admin, filename)).to_contain_text("审核通过", timeout=18000)
            owner.reload(wait_until="networkidle")
            own.get_by_role("combobox").select_option(label="Member Two")
            action(
                owner, "share", lambda: own.get_by_role("button", name="共享", exact=True).click()
            )
            expect(own).to_contain_text("共享消息待投递", timeout=2500)
            owner.screenshot(path=str(out / "03-share-wait.png"))
            denied = action(recipient, "download-before-delivery", lambda: recipient.goto(download))
            assert denied.status == 403
            expect(own).to_contain_text("共享已生效", timeout=18000)
            recipient.goto(app)
            received = file_card(recipient, filename)
            expect(received).to_be_visible()
            assert received.get_by_role("button", name="共享", exact=True).count() == 0
            with recipient.expect_download() as pending:
                action(
                    recipient,
                    "download-active",
                    lambda: received.get_by_role("link", name="下载", exact=True).click(),
                )
            destination = out / "downloaded.txt"
            pending.value.save_as(str(destination))
            assert destination.read_bytes() == payload
            recipient.screenshot(path=str(out / "04-recipient.png"))
            checks.append(
                "Real input, review/share waits, actual 403 responses and byte-identical authorized download"
            )

            # Wait for the last completed request before closing capture. Reading
            # a stale live poll would falsely classify a delivered event as lost.
            final_trace = actions[-1]["trace_id"]
            graph.wait_for_function(
                "id => graphDebug.view.events.some(e => e.trace?.trace_id===id && e.outputs?.status===200)",
                arg=final_trace,
            )
            graph.locator("#record-stop").click()
            graph.wait_for_function("graphDebug.timeline?.source === 'saved'")
            graph.wait_for_function(
                "graphDebug.view.replay?.id && document.querySelector('#record-list').value === graphDebug.view.replay.id"
            )
            record_id = graph.locator("#record-list").input_value()
            response = graph.request.get(
                args.graph.split("/graph")[0] + "/api/recordings/" + record_id
            )
            assert response.ok, "Saved-recording response: " + response.text()
            recording = response.json()
            assert recording.get("id") == record_id and "events" in recording
            write_json(out / "recording.json", recording)
            graph.locator(".trace-scope").select_option("all")
            graph.locator("#replay-grain").select_option("events")
            canvas = graph.locator("#recording-timeline canvas")
            canvas.focus()
            graph.keyboard.press("End")
            graph.wait_for_function(
                "graphDebug.view.replay?.event?.id === 'end' || graphDebug.timeline.eventId === 'end'"
            )
            timeline = graph.evaluate("graphDebug.timeline")
            assert timeline["lifecycles"], "Timeline has no lifecycle intervals"
            assert timeline["flows"] > 0, "Timeline has no causal relations"
            graph.screenshot(path=str(out / "05-recorded-2d.png"))
            raw = timeline["raw"]
            graph.locator("#layered-toggle").click()
            graph.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
            spatial_raw = graph.evaluate("graphDebug.timeline.raw")
            write_json(out / "cursor-comparison.json", {"two_d": raw, "three_d": spatial_raw})
            assert spatial_raw == raw
            graph.screenshot(path=str(out / "06-recorded-3d.png"))
            checks.append(
                "Recorded graph/Timeline share raw cursor and causal lifecycle intervals in 2D/3D"
            )
            graph.locator("#analysis-view").select_option("code")
            graph.wait_for_function("graphDebug.view.code_structure?.loaded_nodes > 0")
            layers = graph.evaluate(
                """() => ({
                nodes: [...graphDebug.graph.all.values()].map(n => ({
                    id:n.id, layer:n.layer, kind:n.kind, code_role:n.code_role,
                    data_role:n.data_role, source:n.source, semantic_role:n.semantic_role
                })),
                edges: graphDebug.graph.rawEdges
            })"""
            )
            write_json(out / "layer-projection.json", layers)
            graph.locator("#analysis-view").select_option("overview")
            comparisons = []
            for native in responses:
                matches = [
                    e
                    for e in recording["events"]
                    if e.get("trace", {}).get("trace_id") == native["trace_id"]
                    and e["phase"] == "return"
                    and e.get("inputs", {}).get("path") == native["path"]
                    and e.get("outputs", {}).get("status") == native["status"]
                ]
                comparisons.append({**native, "matching_event_ids": [e["id"] for e in matches]})
            write_json(out / "http-comparisons.json", comparisons)
            assert comparisons and all(
                len(row["matching_event_ids"]) == 1 for row in comparisons
            ), comparisons
            checks.append(
                "Every exercised native command/download response joins exactly one captured HTTP boundary by W3C trace identity and path"
            )
            assert not errors, errors
            write_json(
                out / "result.json",
                {
                    "passed": True,
                    "app": app,
                    "graph": args.graph,
                    "file_id": identity,
                    "filename": filename,
                    "download_sha256": sha256(payload).hexdigest(),
                    "checks": checks,
                    "page_errors": errors,
                    "actions": actions,
                    "http_comparisons": len(comparisons),
                    "recording": record_id,
                    "events": len(recording["events"]),
                    "gaps": recording.get("gaps", []),
                    "timeline": {
                        k: timeline.get(k) for k in ("source", "flows", "raw", "rows", "lifecycles")
                    },
                    "elapsed_s": round(time.time() - started, 3),
                },
            )
            print(
                json.dumps(
                    {
                        "passed": True,
                        "events": len(recording["events"]),
                        "http_comparisons": len(comparisons),
                        "output": str(out),
                    }
                )
            )
        except BaseException as error:
            for index, context in enumerate(browser.contexts):
                for offset, opened in enumerate(context.pages):
                    opened.screenshot(path=str(out / f"failure-{index}-{offset}.png"))
            write_json(
                out / "failure.json",
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "responses": responses,
                    "actions": actions,
                    "checks": checks,
                    "page_errors": errors,
                },
            )
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
