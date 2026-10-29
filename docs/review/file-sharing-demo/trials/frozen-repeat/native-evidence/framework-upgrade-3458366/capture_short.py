"""Collect only the real short chain needed for the changed native viewer build."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "browser-native"
OUT.mkdir(exist_ok=True)
if (OUT / "recording.json").exists():
    raise RuntimeError("Preserve the existing stopped recording; use viewer-only retests.")
APP = "http://127.0.0.1:8840"
GRAPH = "http://127.0.0.1:8841"
report = {"status": "running", "provenance": "Actual native capture; no mocked business events.",
          "started_at": datetime.now(timezone.utc).isoformat(), "checks": [], "drain_progress": []}
content = b"Native framework upgrade witness.\n"
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
        try:
            contexts = [browser.new_context() for _ in range(5)]
            owner, recipient, other, anonymous, graph = [context.new_page() for context in contexts]
            graph.goto(GRAPH + "/graph", wait_until="domcontentloaded")
            expect(graph.locator("#record-start")).to_be_enabled(timeout=20000)
            before = graph.request.get(GRAPH + "/api/view").json()
            assert before["binding_status"]["status"] == "current"
            assert not before["events"], "Use the fresh upgraded producer for exact counts."
            listing = graph.request.get(GRAPH + "/api/recordings").json()
            assert "77ae11709c33488ca6b294097e7d86da" not in json.dumps(listing)
            old = graph.request.get(GRAPH + "/api/recordings/77ae11709c33488ca6b294097e7d86da")
            assert old.status in (400, 404), "Do not replay an obsolete build as current."
            with graph.expect_response(lambda response: response.url.endswith("/api/recordings/start")) as started:
                graph.locator("#record-start").click()
            assert started.value.status == 200
            report["recording_id"] = started.value.json()["id"]
            tokens = {}
            for page, user in ((owner, "linzhou"), (recipient, "xuning"), (other, "zhoulan")):
                result = page.request.post(APP + "/api/login",
                    data={"username": user, "password": "trial-" + user})
                assert result.status == 200
                tokens[page] = result.json()["csrf"]

            def post(page, path, data=None, multipart=None):
                options = {"headers": {"X-CSRF-Token": tokens[page]} if page in tokens else {}}
                options["multipart" if multipart else "data"] = multipart or data or {}
                return page.request.post(APP + path, **options)

            def create(name):
                result = post(owner, "/api/files", multipart={"file": {
                    "name": name, "mimeType": "text/plain", "buffer": content}})
                assert result.status == 201
                return result.json()["id"]

            identity = create("framework-primary-" + uuid.uuid4().hex[:8] + ".txt")
            report["file_id"] = identity
            for user in ("xuning", "zhoulan"):
                assert post(owner, f"/api/files/{identity}/share", {"recipient_id": user}).status == 200
            assert post(other, f"/api/files/{identity}/revoke", {"recipient_id": "xuning"}).status == 403
            assert post(anonymous, f"/api/files/{identity}/revoke", {"recipient_id": "xuning"}).status == 401
            cancelled = post(owner, f"/api/files/{identity}/revoke", {"recipient_id": "xuning"})
            assert cancelled.status == 200 and cancelled.json()["remaining_recipient_ids"] == ["zhoulan"]
            assert recipient.request.get(APP + f"/api/files/{identity}/download").status == 403
            for page in (owner, other):
                assert page.request.get(APP + f"/api/files/{identity}/download").body() == content
            assert post(owner, f"/api/files/{identity}/share", {"recipient_id": "xuning"}).status == 200
            assert recipient.request.get(APP + f"/api/files/{identity}/download").body() == content
            secondary = create("framework-secondary-" + uuid.uuid4().hex[:8] + ".txt")
            report["secondary_file_id"] = secondary
            assert post(owner, f"/api/files/{secondary}/share", {"recipient_id": "xuning"}).status == 200
            cancelled = post(owner, f"/api/files/{secondary}/revoke", {"recipient_id": "xuning"})
            assert cancelled.status == 200 and cancelled.json()["state"] == "private"
            assert cancelled.json()["remaining_recipient_ids"] == []
            assert recipient.request.get(APP + f"/api/files/{secondary}/download").status == 403
            assert owner.request.get(APP + f"/api/files/{secondary}/download").body() == content
            assert post(owner, f"/api/files/{secondary}/share", {"recipient_id": "xuning"}).status == 200
            report["checks"].append("Real owner/nonowner/anonymous policy branches and both revoke state paths execute without new business scope.")
            started_drain = time.monotonic()
            while True:
                response = owner.request.post(APP + "/api/stategraph/flush", data={})
                assert response.status == 200
                state = response.json()
                live = graph.request.get(GRAPH + "/api/view").json()
                sample = {"elapsed_seconds": round(time.monotonic() - started_drain, 3), **state,
                          "accepted_events": len(live["events"]),
                          "accepted_frames": len(live["runtime_frames"]["frames"])}
                report["drain_progress"].append(sample)
                (OUT / "drain-progress.json").write_text(json.dumps(report["drain_progress"], indent=2), encoding="utf-8")
                assert state["errors"] == state["dropped"] == 0, state
                if len(report["drain_progress"]) > 1:
                    previous = report["drain_progress"][-2]
                    assert state["enqueued_events"] == previous["enqueued_events"]
                    assert state["enqueued_snapshots"] == previous["enqueued_snapshots"]
                    assert state["pending_envelopes"] <= previous["pending_envelopes"]
                if state["flushed"]:
                    break
                assert time.monotonic() - started_drain < 900, state
            assert state["pending_envelopes"] == 0
            assert sample["accepted_events"] == state["enqueued_events"]
            assert sample["accepted_frames"] == state["enqueued_snapshots"] == 11
            report["drain_wait_seconds"] = round(time.monotonic() - started_drain, 3)
            report["last_flush_response"] = state
            count = len(live["events"])
            with graph.expect_response(lambda response: response.url.endswith("/api/recordings/stop")) as stopped:
                graph.locator("#record-stop").click()
            assert stopped.value.status == 200
            assert stopped.value.json()["id"] == report["recording_id"]
            recording = graph.request.get(GRAPH + "/api/recordings/" + report["recording_id"]).json()
            assert recording["status"] == "stopped" and not recording["gaps"]
            assert len(recording["events"]) == count
            assert graph.request.get(GRAPH + "/api/view").json()["events"] == live["events"]
            assert recording["build_id"] == json.loads((ROOT / "manifest.json").read_text())["build_id"]
            assert not any(content.decode().strip() in json.dumps(event) for event in recording["events"])
            frames = recording["runtime_frames"]["frames"]
            primary_states = [frame["machine"]["current"] for frame in frames if frame["authority"]["entity"] == identity]
            secondary_states = [frame["machine"]["current"] for frame in frames if frame["authority"]["entity"] == secondary]
            assert primary_states == ["pending", "private", "shared", "shared", "shared", "shared"]
            assert secondary_states == ["pending", "private", "shared", "private", "shared"]
            (OUT / "recording.json").write_text(json.dumps(recording, ensure_ascii=False), encoding="utf-8")
            report.update(status="captured", build_id=recording["build_id"], event_count=count,
                          state_frames=primary_states, secondary_state_frames=secondary_states,
                          recording_sha256=hashlib.sha256((OUT / "recording.json").read_bytes()).hexdigest())
        finally:
            browser.close()
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    (OUT / "capture-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in ("status", "build_id", "event_count", "drain_wait_seconds")}))
