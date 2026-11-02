"""Reproduce failed-login actor attribution through the unchanged live application."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
APP = "http://127.0.0.1:59262"
GRAPH = "http://127.0.0.1:59263"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def database_summary(username):
    with closing(sqlite3.connect("file:" + (ROOT / "data/sharing.sqlite3").as_posix() + "?mode=ro", uri=True)) as connection:
        return {"requested_username_count": connection.execute("SELECT count(*) FROM users WHERE username = ?", (username,)).fetchone()[0],
                "table_counts": {table: connection.execute("SELECT count(*) FROM " + table).fetchone()[0] for table in ("users", "files", "shares", "messages")}}


def main():
    username = "actor_scope_unknown_" + uuid.uuid4().hex[:16]
    password = secrets.token_urlsafe(20)
    graph_client = requests.Session()
    graph_client.trust_env = False
    before = graph_client.get(GRAPH + "/api/view", timeout=10).json()
    assert before["stage"] == "runtime"
    assert before["model"]["project_id"] == "team-file-sharing-otel-20261101-01"
    assert before["binding_status"]["status"] == "current"
    prior_events = {event["id"] for event in before["events"]}
    source_dir = OUT / "source-snapshots"
    source_dir.mkdir(exist_ok=True)
    names = ["app/domain.py", "app/web.py", "app/ports.py", "integrations/bo_adapter.py"]
    source_hashes = {}
    for name in names:
        raw = (ROOT / name).read_bytes()
        target = source_dir / (name.replace("/", "--") + ".snapshot")
        target.write_bytes(raw)
        source_hashes[name] = hashlib.sha256(raw).hexdigest()
        assert source_hashes[name] == before["manifest"]["files"][name]
    source_response = graph_client.get(GRAPH + "/api/source", params={"path": "app/domain.py"}, timeout=10)
    (OUT / "source-api-response.raw.json").write_bytes(source_response.content)
    native_before = database_summary(username)
    assert native_before["requested_username_count"] == 0
    client = requests.Session()
    client.trust_env = False
    login_page = client.get(APP + "/login", timeout=10)
    csrf = re.search(r'name="csrf" value="([^"]+)"', login_page.text).group(1)
    response = client.post(APP + "/login", data={"csrf": csrf, "username": username, "password": password}, allow_redirects=False, timeout=10)
    (OUT / "native-login-response.raw.html").write_bytes(response.content)
    protected = client.get(APP + "/files", allow_redirects=False, timeout=10)
    native_after = database_summary(username)
    after = None
    matching = []
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        after = graph_client.get(GRAPH + "/api/view", timeout=10).json()
        fresh = [event for event in after["events"] if event["id"] not in prior_events]
        matching = [event for event in fresh if event["node"] == "sign_in" and event.get("inputs", {}).get("username") == username]
        if matching:
            call_ids = {event["call_id"] for event in matching}
            if any(event["node"] == "sign_in" and event["phase"] == "error" and event["call_id"] in call_ids for event in fresh):
                break
        time.sleep(0.1)
    fresh = [event for event in after["events"] if event["id"] not in prior_events]
    write("events.raw.json", fresh)
    call_ids = {event["call_id"] for event in matching}
    auth_events = [event for event in fresh if event["node"] == "sign_in" and event["call_id"] in call_ids]
    write("authentication-events.raw.json", auth_events)
    write("source-bindings.raw.json", {"build_id": before["manifest"]["build_id"],
        "bindings": {key: value for key, value in before["manifest"]["bindings"].items() if value["path"] in names},
        "file_hashes": source_hashes})
    assert source_hashes == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    write("native-authentication-result.json", {"case": "nonexistent account with independent synthetic credentials",
        "username": username, "password": "[NOT RETAINED]", "fresh_client_session": True,
        "login_response": {"status": response.status_code, "content_type": response.headers.get("Content-Type"),
            "invalid_credentials_message_present": "账号或密码不正确" in response.text, "body": "native-login-response.raw.html"},
        "subsequent_protected_request": {"status": protected.status_code, "location": protected.headers.get("Location")},
        "database_before": native_before, "database_after": native_after,
        "scope": "Native HTTP results and independent read-only SQLite facts; no SDK inference is used as authentication authority."})
    misleading = [event for event in auth_events if event.get("provenance", {}).get("actor", {}).get("id") == username]
    business_rejected = response.status_code == 401 and protected.status_code == 302 and protected.headers.get("Location") == "/login" and native_after["requested_username_count"] == 0
    observation_inaccurate = bool(misleading)
    assert business_rejected
    assert observation_inaccurate
    write("result.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(), "project_id": before["model"]["project_id"],
        "build_id": before["manifest"]["build_id"], "username": username,
        "business_rejection": {"status": "confirmed", "http_status": response.status_code, "authenticated_session_established": False},
        "observation_accuracy": {"status": "failed", "reason": "An unverified submitted username was recorded as provenance.actor despite native authentication rejection and no matching account.",
            "misattributed_event_ids": [event["id"] for event in misleading], "phases": [event["phase"] for event in misleading]},
        "raw_events": len(fresh), "authentication_events": len(auth_events),
        "application_source_unchanged": True, "shared_sdk_modified": False,
        "historical_gate_receipt": ".stategraph/initial-v1/accepted.json already existed before this request; no acceptance command was run for this reproduction.",
        "delivery_acceptance": "not granted for actor semantics; user requested stopping after reproduction",
        "next_action": "Stop. Preserve the current implementation and await the user's general capability/Skill repair and a new conversation."})
    print(json.dumps({"business_rejected": business_rejected, "observation_accuracy": "failed", "authentication_events": len(auth_events),
        "misattributed_phases": [event["phase"] for event in misleading], "output": str(OUT)}))


if __name__ == "__main__":
    main()
