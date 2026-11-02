"""Observe two real logins on one native session without editing the trial.

Session and user rows establish identity at the exact domain-function entry.
Request-entry identity is retained separately because the handler clears it.
Only a new isolated synthetic SQLite database is used; no active app data changes.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
TRIAL = ROOT.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-03"
sys.path.insert(0, str(TRIAL))
from tests.scenarios import Trial
from integrations.bo_integration import BOIntegration
from flask import session as native_session


def source_hashes():
    """Reject a final conclusion if the trial changes while the check is running."""
    cfg = json.loads((TRIAL / "sync.json").read_text(encoding="utf-8"))
    paths = {"sync.json", cfg["model"], cfg["manifest"], *cfg["code_files"]}
    return {path: sha256((TRIAL / path).read_bytes()).hexdigest() for path in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    folder = args.out or Path(__file__).resolve().parent / "dialogue-03-reauthentication"
    if folder.exists():
        raise FileExistsError("Preserve the previous reproduction; choose a new --out directory")
    before_sources = source_hashes()
    trial = Trial()
    observer = BOIntegration(TRIAL, trial.store)
    trial.service.bo = observer
    observer.attach_flask(trial.app)
    client = trial.app.test_client()
    facts = []
    function_entries = []
    original = trial.service.sign_in

    def native_entry(*args, **kwargs):
        identity = native_session.get("user_id")
        rows = (
            trial.store.read("SELECT id FROM users WHERE id=?", (identity,), observe=False)
            if identity
            else []
        )
        function_entries.append({"id": rows[0]["id"], "kind": "user"} if rows else None)
        return original(*args, **kwargs)

    trial.service.sign_in = native_entry
    try:
        for username in ("admin1", "member1"):
            with client.session_transaction() as session:
                identity = session.get("user_id")
            native = (
                trial.store.read("SELECT id,role FROM users WHERE id=?", (identity,), observe=False)
                if identity
                else []
            )
            before = {"id": native[0]["id"], "kind": "user"} if native else None
            response = client.post(
                "/api/login", json={"username": username, "password": "Trial2026!"}
            )
            with client.session_transaction() as session:
                after = session.get("user_id")
            facts.append(
                {
                    "native_principal_before": before,
                    "native_status": response.status_code,
                    "native_principal_after": after,
                }
            )
        if not observer.probe.flush(10):
            raise RuntimeError("actual producer did not flush")
        events = [
            event
            for event in observer.session.current_events()
            if event["run_id"] == observer.probe.bo_run
        ]
        entries = [
            event for event in events if event["node"] == "sign_in" and event["phase"] == "enter"
        ]
        checks = [
            {
                "native": principal,
                "recorded": event.get("provenance", {}).get("actor"),
                "event": event["id"],
                "matches": "actor" in event.get("provenance", {})
                and principal == event["provenance"]["actor"],
            }
            for principal, event in zip(function_entries, entries)
        ]
        after_sources = source_hashes()
        stable = before_sources == after_sources
        result = {
            "passed": stable and len(entries) == 2 and all(item["matches"] for item in checks),
            "source_stable": stable,
            "source_hashes": before_sources,
            "scope": "Session principal read at actual sign_in entry through a read-only test wrapper; no source patch or business behavior change.",
            "build_id": observer.probe.bo_build,
            "native": facts,
            "checks": checks,
            "probe_health": observer.health(),
            "raw_event_count": len(events),
        }
        folder.mkdir(parents=True)
        for name, value in (("result.json", result), ("raw-events.json", events)):
            (folder / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "passed": result["passed"],
                    "source_stable": stable,
                    "checks": checks,
                    "raw_events": len(events),
                    "probe_errors": result["probe_health"]["errors"],
                }
            )
        )
        raise SystemExit(not result["passed"])
    finally:
        observer.close()


if __name__ == "__main__":
    main()
