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

from playwright.sync_api import Error as BrowserError, expect, sync_playwright


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
    parser.add_argument("--revocation", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "test-harness.py").write_bytes(Path(__file__).read_bytes())
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

    def workspace(page):
        """Open a real workspace despite the application's periodic navigation.

        A native refresh can supersede an explicit navigation. Confirm the actual
        workspace DOM instead of waiting for a network-idle window between polls.
        """
        try:
            page.goto(app, wait_until="domcontentloaded")
        except BrowserError as error:
            if "net::ERR_ABORTED" not in str(error):
                raise
        expect(page.locator("#workspace")).to_be_visible()

    def login(page, name):
        page.goto(app, wait_until="domcontentloaded")
        page.get_by_label("账号", exact=True).fill(name)
        page.get_by_label("密码", exact=True).fill("Trial2026!")
        action(
            page,
            "login-" + name,
            lambda: page.get_by_role("button", name="登录", exact=True).click(),
        )
        expect(page.locator("#workspace")).to_be_visible()

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
            preferences = graph.request.get(args.graph.split("/graph")[0]+"/api/preferences").json()
            write_json(out / "preferences-before.json", preferences)
            def private_view(route):
                nonlocal preferences
                if route.request.method == "POST":
                    preferences = {**route.request.post_data_json, "revision": preferences["revision"]+1}
                route.fulfill(json=preferences)
            # Isolate test-only view edits; business, graph, sources and recording
            # still use the real services. Server-side persistence has its own gate.
            graph.route("**/api/preferences", private_view)
            graph.goto(args.graph)
            graph.wait_for_function("typeof graphDebug !== 'undefined' && graphDebug.graph?.boxes.length>0")
            if graph.locator("#replay-timeline").get_attribute("aria-pressed") != "true":
                graph.locator("#replay-timeline").click()
            graph.wait_for_function(
                "typeof graphDebug !== 'undefined' && graphDebug.timeline?.geometry"
            )
            if graph.locator("#layered-toggle").get_attribute("aria-pressed") == "true":
                graph.locator("#layered-toggle").click()
                # Spatial diagnostics retain the cached 3D scene after leaving it.
                # The mode button describes the currently active renderer.
                graph.wait_for_function(
                    "document.querySelector('#layered-toggle').getAttribute('aria-pressed') === 'false' && !graphDebug.layoutBusy"
                )
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
            workspace(owner)
            own.get_by_role("combobox").select_option(label="Member Two")
            action(
                owner, "share", lambda: own.get_by_role("button", name="共享", exact=True).click()
            )
            expect(own).to_contain_text("共享消息待投递", timeout=2500)
            owner.screenshot(path=str(out / "03-share-wait.png"))
            denied = action(recipient, "download-before-delivery", lambda: recipient.goto(download))
            assert denied.status == 403
            expect(own).to_contain_text("共享已生效", timeout=18000)
            workspace(recipient)
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

            if args.revocation:
                # Revoke an active grant and exercise the administrator's
                # independent authority through the actual download button.
                revoke = own.locator('form[action="/command/revoke"]')
                action(
                    owner,
                    "revoke-active",
                    lambda: revoke.get_by_role("button", name="撤销共享", exact=True).click(),
                )
                expect(own).to_contain_text("共享已撤销", timeout=2500)
                denied = action(recipient, "download-revoked", lambda: recipient.goto(download))
                assert denied.status == 403
                workspace(admin)
                with admin.expect_download() as authorized:
                    action(
                        admin,
                        "administrator-after-revoke",
                        lambda: file_card(admin, filename)
                        .get_by_role("link", name="下载", exact=True)
                        .click(),
                    )
                admin_destination = out / "administrator-download.txt"
                authorized.value.save_as(str(admin_destination))
                assert admin_destination.read_bytes() == payload
                workspace(recipient)
                notice = (
                    recipient.locator("article.message-row")
                    .filter(has_text=filename)
                    .filter(has_text="Sharing was revoked")
                )
                expect(notice).to_be_visible(timeout=18000)
                recipient.screenshot(path=str(out / "07-active-revoked.png"))

                # A second real file reaches notification wait. Cancel its
                # grant before delivery, then observe the later notification.
                pending_name = "pending-" + filename
                pending_file = out / pending_name
                pending_file.write_bytes(payload)
                owner.locator('input[type="file"]').set_input_files(str(pending_file))
                action(
                    owner,
                    "upload-pending-case",
                    lambda: owner.get_by_role("button", name="上传并提交审核", exact=True).click(),
                )
                pending_card = file_card(owner, pending_name)
                expect(pending_card).to_be_visible()
                pending_id = (
                    pending_card.get_by_role("link", name="文件信息", exact=True)
                    .get_attribute("href")
                    .rsplit("/", 1)[1]
                )
                workspace(admin)
                pending_review = admin.locator('form[action="/command/review"]').filter(
                    has=admin.locator(f'input[name="file_id"][value="{pending_id}"]')
                )
                action(
                    admin,
                    "approve-pending-case",
                    lambda: pending_review.get_by_role("button", name="通过", exact=True).click(),
                )
                expect(file_card(admin, pending_name)).to_contain_text("审核通过", timeout=18000)
                workspace(owner)
                pending_card.get_by_role("combobox").select_option(label="Member Two")
                action(
                    owner,
                    "share-pending-case",
                    lambda: pending_card.get_by_role("button", name="共享", exact=True).click(),
                )
                expect(pending_card).to_contain_text("共享消息待投递", timeout=2500)
                action(
                    owner,
                    "revoke-pending-case",
                    lambda: pending_card.get_by_role("button", name="撤销共享", exact=True).click(),
                )
                expect(pending_card).to_contain_text("共享已撤销", timeout=2500)
                pending_download = app + "/api/files/" + pending_id + "/download"
                denied = action(
                    recipient, "download-pending-revoked", lambda: recipient.goto(pending_download)
                )
                assert denied.status == 403
                workspace(recipient)
                pending_notice = (
                    recipient.locator("article.message-row")
                    .filter(has_text=pending_name)
                    .filter(has_text="Sharing was revoked")
                )
                expect(pending_notice).to_be_visible(timeout=18000)
                denied = action(
                    recipient,
                    "download-after-old-notice-deadline",
                    lambda: recipient.goto(pending_download),
                )
                assert denied.status == 403
                owner.screenshot(path=str(out / "08-pending-revoked.png"))
                checks.append(
                    "Active and pending sharing revoke immediately; administrator authority remains; recipient stays denied after notification delivery"
                )

            # Keep the native three-second refresh running during settlement.
            # This deliberately exercises the continuous-load defect of the prior run.
            for business_page in (owner, admin, recipient):
                workspace(business_page)
            # The submitted-prefix barrier owns settlement. A bounded live-history
            # window is not an acknowledgement of every earlier native response.
            # Exact HTTP response matching below still checks the saved evidence.
            stop_started = time.monotonic()
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
            write_json(out / "stop-settlement.json", {"elapsed_s": time.monotonic()-stop_started,
                "producer": recording["producer_settlement"], "native_pages_open": 3})
            assert not recording.get("gaps"), recording["gaps"]
            assert recording["producer_settlement"]["flushed"]
            assert recording["context"]["project_structure"]["loaded_nodes"] > 0
            for business_page in (owner, admin, recipient):
                business_page.close()
            graph.locator("#analysis-view").select_option("project")
            graph.wait_for_function("graphDebug.displayGraph.boxes.some(b=>b.node.code_role==='directory') && graphDebug.presentation.glyphs.size>0")
            assert not graph.locator("#empty").is_visible()
            graph.locator("#expand").click()
            graph.wait_for_function("graphDebug.displayGraph.boxes.some(b=>b.node.code_role==='file') && graphDebug.displayGraph.edges.length>0")
            graph.locator("#arrange").click()
            graph.wait_for_function("!graphDebug.layoutBusy")
            graph.screenshot(path=str(out / "09-recorded-project-tree.png"))
            graph.locator("#analysis-view").select_option("overview")
            graph.locator("#arrange").click()
            graph.wait_for_function("!graphDebug.layoutBusy")
            hierarchy = graph.locator("#replay-events option").evaluate_all(
                "options=>({nested:options.filter(o=>Number(o.dataset.depth)>0).length, layers:[...new Set(options.map(o=>o.dataset.layer).filter(Boolean))],colored:options.filter(o=>o.style.color).length})")
            write_json(out / "step-hierarchy.json", hierarchy)
            assert hierarchy["nested"] > 0 and len(hierarchy["layers"]) > 3

            configurations = recording["final"]["machine"]["configurations"]
            instance_ids = [cfg.get("snapshot_instance") for cfg in configurations]
            assert all(instance_ids) and len(set(instance_ids)) == len(instance_ids)
            assert all(cfg.get("native_instance_id") for cfg in configurations)
            # A caller can own several independent machines. Check the replay's
            # actual comparator, beyond cursor counts and native HTTP responses.
            semantics = graph.evaluate(
                """async id => {
                    const recording = await (await fetch('/api/recordings/' + id)).json();
                    const { boFacts } = await import('./replay-steps.js');
                    const { timeline } = await import('./recording.js');
                    const facts = boFacts(recording, timeline(recording));
                    return {
                        finalBusinessChanges: facts.changes.at(-1).filter(r => r.kind==='business'),
                        stateChanges: facts.changes.flat().filter(r => r.kind==='business').length,
                        instances: recording.final.machine.configurations.map(c => ({
                            id:c.snapshot_instance, native:c.native_instance_id,
                            caller:c.attempt, state:c.phase
                        }))
                    };
                }""",
                record_id,
            )
            write_json(out / "state-instance-comparison.json", semantics)
            assert semantics["finalBusinessChanges"] == [], semantics
            assert semantics["stateChanges"] > 0, "No actual state transitions were presented"
            checks.append(
                "Interleaved state instances retain distinct identities and no false final transition"
            )
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
            # Static source expansion belongs to the current source projection.
            # Return to live before requesting a slice absent from the recording.
            graph.locator("#record-list").select_option("")
            graph.wait_for_function("!graphDebug.view.replay")
            graph.locator("#analysis-view").select_option("code")
            graph.wait_for_function("graphDebug.view.code_structure?.loaded_nodes > 0")
            layers = graph.evaluate(
                """() => ({
                nodes: [...graphDebug.graph.all.values()].map(n => ({
                    id:n.id, layer:n.layer, kind:n.kind, code_role:n.code_role,
                    data_role:n.data_role, source:n.source, semantic_role:n.semantic_role,
                    capture_owner_role:n.capture_owner_role, execution_role:n.execution_role,
                    origin:n.origin, reference_scope:n.reference_scope
                })),
                edges: graphDebug.graph.rawEdges,
                code_summary: Object.fromEntries(
                    ['loaded_nodes','total_nodes','loaded_edges','omitted_nodes','omitted_edges','boundary_nodes','errors','revision']
                    .map(k => [k, graphDebug.view.code_structure?.[k]])
                )
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
                    "state_instances": len(instance_ids),
                    "state_changes": semantics["stateChanges"],
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
