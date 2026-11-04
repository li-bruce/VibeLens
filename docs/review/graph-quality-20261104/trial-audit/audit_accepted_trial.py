"""Compare existing trial evidence without importing, running or changing the trial."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
from urllib.parse import parse_qs, urlparse


HERE = Path(__file__).resolve().parent
DEFAULT_TRIAL = HERE.parents[3].parent / "VibeLensTrials/graph-quality-dialogue-20261104-01"
RECEIPTS = {
    "current": ("final-current-check.json", "current-check.json", "change-check.json"),
    "docs": ("source-docs.json", "source-documentation.json"),
    "api": ("api-observation.json", "api-check.json"),
    "browser": ("browser/results.json", "browser-results.json"),
    "replay": ("browser/replay-results.json", "replay-results.json"),
    "runtime": ("final-runtime-parity.json", "runtime-parity.json", "upgrade-parity.json"),
}


def digest(value):
    """Match the documented JSON receipt digest, independently of trial imports."""
    raw = (
        value
        if isinstance(value, bytes)
        else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    return hashlib.sha256(raw).hexdigest()


class Evidence:
    """Read only named, contained artifacts; omit raw events and source text from output."""

    def __init__(self, root):
        self.root = root.resolve()
        self.files, self.pending = {}, []

    def path(self, name):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Evidence path must stay inside the trial")
        blocked = {".env", "session.key", "cookies.json", "credentials.json", "secrets.json"}
        for part in relative.parts:
            if (
                part.lower() in blocked
                or part.lower().startswith(".env")
                or re.search(r"(^|[-_.])(cookies?|credentials?|secrets?)([-_.]|$)", part.lower())
                or part.lower().endswith((".sqlite", ".sqlite3", ".db", ".key", ".pem"))
            ):
                raise ValueError("Private/runtime content is outside this audit: " + name)
        target = self.root / relative
        for part in (target, *target.parents):
            if not part.is_relative_to(self.root):
                break
            if part.exists():
                info = part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ValueError("Audit will not follow links: " + name)
            if part == self.root:
                break
        return target

    def read(self, name, *, required=True):
        try:
            path = self.path(name)
            if not path.is_file():
                if required:
                    self.pending.append("Missing evidence: " + name)
                return None
            raw = path.read_bytes()
            self.files[name] = {"sha256": digest(raw), "bytes": len(raw)}
            value = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("Evidence must be a JSON object")
            return value
        except (OSError, ValueError, UnicodeError) as error:
            self.pending.append("Unreadable evidence: " + name + " (" + type(error).__name__ + ")")
            return None

    def hashes(self, expected):
        """Hash declared source inputs only; never enumerate uploads or open databases."""
        different, unavailable = [], []
        for name, old in expected.items():
            try:
                path = self.path(name)
                if not path.is_file():
                    unavailable.append(name)
                else:
                    raw = path.read_bytes()
                    self.files[name] = {"sha256": digest(raw), "bytes": len(raw)}
                    if digest(raw) != old:
                        different.append(name)
            except (OSError, ValueError):
                unavailable.append(name)
        return {
            "declared": len(expected),
            "different": different,
            "unavailable_or_private": unavailable,
        }


def receipt_summary(value):
    value = value or {}
    checks = value.get("checks", {})
    booleans = (
        {key: item for key, item in checks.items() if type(item) is bool}
        if isinstance(checks, dict)
        else {}
    )
    return {
        "valid": value.get("valid"),
        "status": value.get("status"),
        "candidate_id": value.get("candidate_id"),
        "build_id": value.get("build_id") or value.get("recording", {}).get("build_id"),
        "revision": value.get("revision"),
        "error_count": len(value.get("errors", [])),
        "boolean_checks": booleans,
        "checked_symbols": len(value.get("checked_symbols", [])),
        "missing_count": len(value.get("missing", [])),
        "api_observed_routes": len(value.get("observed_routes", [])),
        "api_coverage": value.get("coverage"),
        "strict": value.get("strict"),
    }


def model_of(project):
    return (project or {}).get("model", project or {})


def recording_id(receipt):
    """Accept a separate replay receipt or an explicitly combined browser receipt."""
    return (receipt or {}).get("recording_id") or (receipt or {}).get("recording", {}).get("id")


def preference_changes(old, new):
    result = {}
    for key, before in (old or {}).get("entries", {}).items():
        after = (new or {}).get("entries", {}).get(key)
        try:
            a = json.loads(before) if isinstance(before, str) else before
            b = json.loads(after) if isinstance(after, str) else after
            positions = a.get("positions", {})
            result[key] = {
                "entry_retained": after is not None,
                "unchanged": before == after,
                "old_positions": len(positions),
                "retained_positions": sum(
                    node in (b or {}).get("positions", {}) for node in positions
                ),
                "changed_positions": [
                    node
                    for node, position in positions.items()
                    if node in (b or {}).get("positions", {}) and b["positions"][node] != position
                ],
            }
        except (ValueError, AttributeError):
            result[key] = {"entry_retained": after is not None, "needs_review": True}
    return result


def audit(args):
    evidence = Evidence(args.trial)
    phase = ".stategraph/" + args.phase
    cfg = evidence.read("sync.json") or {}
    active = evidence.read(".stategraph/active.json") or {}
    accepted = evidence.read(phase + "/accepted.json") or {}
    verification = evidence.read(phase + "/verification.json") or {}
    envelope = evidence.read(phase + "/checks/observations.json") or {}
    manifest = evidence.read(cfg.get("manifest", "manifest.json")) or {}
    project = evidence.read(cfg.get("model", "bo_stategraph/project.json")) or {}
    model = model_of(project)
    intent = evidence.read(model.get("intent", "intent.json"))
    baseline = evidence.read(".stategraph/source-baseline.json") or {}
    maintenance = evidence.read(".stategraph/maintenance.json") or {}
    code = evidence.read(".stategraph/code-graph.json") or {}
    version = evidence.read("bo_stategraph/runtime-version.json") or {}
    try:
        payload = json.loads(envelope["stdout"])
        if not isinstance(payload, dict):
            raise ValueError("Observation payload must be an object")
    except (KeyError, TypeError, ValueError):
        payload = {}
        evidence.pending.append("No parseable native observation payload for this phase")
    checks = {}
    checks["verification_valid"] = verification.get("valid") if verification else None

    def equal(name, a, b):
        checks[name] = a == b if a is not None and b is not None else None

    equal("active_phase", active.get("change"), phase)
    equal(
        "candidate_verified_and_accepted",
        verification.get("candidate_id"),
        accepted.get("candidate_id"),
    )
    verification_copy = evidence.read(
        "review/" + args.phase + "/results/finalized-verification.json", required=False
    )
    if verification_copy is not None:
        equal(
            "native_review_verification_copy",
            digest(verification_copy),
            digest(verification) if verification else None,
        )
    equal(
        "accepted_verification_digest",
        accepted.get("verification_hash"),
        digest(verification) if verification else None,
    )
    equal(
        "actual_observation_receipt_digest",
        verification.get("observations_hash"),
        digest(envelope) if envelope else None,
    )
    equal("accepted_manifest_build", accepted.get("build_id"), manifest.get("build_id"))
    equal("manifest_model_hash", manifest.get("model_hash"), digest(model) if model else None)
    equal("manifest_intent_hash", manifest.get("intent_hash"), digest(intent) if intent else None)
    equal(
        "build_derived_from_current_declarations",
        manifest.get("build_id"),
        (
            digest({"files": manifest["files"], "model": model, "intent": intent})
            if manifest.get("files") and model and intent
            else None
        ),
    )
    equal("observed_accepted_build", payload.get("build_id"), accepted.get("build_id"))
    equal("maintenance_candidate", maintenance.get("candidate_id"), accepted.get("candidate_id"))
    checks["native_observation_command_exit_zero"] = (
        envelope.get("exit_code") == 0 if envelope else None
    )
    checks["complete_project_root_retained"] = (
        "." in cfg.get("source_scope", {}).get("roots", []) if cfg.get("stategraph") else None
    )
    source_hashes = evidence.hashes(manifest.get("files", {}))
    inventory_hashes = evidence.hashes(baseline.get("files", {}))
    checks["manifest_source_hashes_current"] = (
        not (source_hashes["different"] or source_hashes["unavailable_or_private"])
        if manifest.get("files")
        else None
    )
    checks["accepted_inventory_hashes_current"] = (
        not (inventory_hashes["different"] or inventory_hashes["unavailable_or_private"])
        if baseline.get("files")
        else None
    )
    advisory_inputs = {}
    for name, expected in baseline.get("scope_inputs", {}).items():
        try:
            path = evidence.path(name)
            raw = path.read_bytes() if path.is_file() else None
            actual = digest(raw) if raw is not None else None
            # A declared absent advisory input is testable absence, not unknown.
            checks["advisory_input:" + name] = expected == actual
            advisory_inputs[name] = {
                "accepted_hash": expected,
                "actual_hash": actual,
                "present": raw is not None,
            }
            if raw is not None:
                evidence.files[name] = {"sha256": actual, "bytes": len(raw)}
        except (OSError, ValueError):
            checks["advisory_input:" + name] = None

    receipts, summaries = {}, {}
    overrides = dict(item.split("=", 1) for item in args.receipt)
    for kind, names in RECEIPTS.items():
        candidates = (
            [overrides[kind]]
            if kind in overrides
            else ["review/" + args.phase + "/" + name for name in names]
        )
        name = next((name for name in candidates if evidence.path(name).is_file()), candidates[0])
        receipts[kind] = evidence.read(name)
        summaries[kind] = {"path": name, **receipt_summary(receipts[kind])}
        summary = summaries[kind]
        if summary["build_id"] is not None:
            equal(kind + "_accepted_build", summary["build_id"], accepted.get("build_id"))
        if summary["candidate_id"] is not None:
            equal(
                kind + "_accepted_candidate", summary["candidate_id"], accepted.get("candidate_id")
            )
        if kind in {"api", "docs"}:
            equal(kind + "_source_revision", summary["revision"], code.get("revision"))
        checks[kind + "_receipt_present"] = receipts[kind] is not None
        if kind in {"current", "docs", "api", "runtime"}:
            checks[kind + "_receipt_valid"] = summary["valid"] is True if receipts[kind] else None
        else:
            checks[kind + "_receipt_checks"] = (
                all(summary["boolean_checks"].values())
                and bool(summary["boolean_checks"])
                and summary["error_count"] == 0
                if receipts[kind]
                else None
            )
        if kind == "api":
            checks["api_complete"] = (
                summary["api_coverage"] == "complete" if receipts[kind] else None
            )
        if kind == "current":
            checks["native_current_status"] = (
                summary["status"] == "current" if receipts[kind] else None
            )
    browser_path = Path(summaries["browser"]["path"])
    browser_recording_id = recording_id(receipts["browser"])
    if args.recording:
        recording_path = args.recording
    elif browser_recording_id and re.fullmatch(r"[a-zA-Z0-9_-]+", browser_recording_id):
        recording_path = "bo_stategraph/data/recordings/" + browser_recording_id + ".json"
    else:
        recording_path = (browser_path.parent / "recording.json").as_posix()
    recording = evidence.read(recording_path) or {}
    equal("browser_recording_build", recording.get("build_id"), accepted.get("build_id"))
    equal(
        "browser_recording_identity",
        browser_recording_id,
        recording.get("id"),
    )
    replay_recording = evidence.read(args.replay_recording) if args.replay_recording else recording
    equal(
        "replay_recording_identity",
        recording_id(receipts["replay"]),
        (replay_recording or {}).get("id"),
    )
    equal(
        "replay_recording_build", (replay_recording or {}).get("build_id"), accepted.get("build_id")
    )
    checks["recording_no_gaps"] = not recording.get("gaps") if recording else None
    native = {
        name: {
            "status": report.get("status"),
            "error_count": len(report.get("errors", [])),
            **(
                {"assertions": report["assertions"]}
                if name == "business" and "assertions" in report
                else {}
            ),
        }
        for name, report in verification.get("reports", {}).items()
    }
    nodes = {node["id"]: node for node in model.get("nodes", [])}
    observed, statuses, runs, observer_events, api_returns = Counter(), Counter(), [], [], []
    for run in payload.get("runs", []):
        events = run.get("events", [])
        for event in events:
            if run.get("mode") != "on":
                continue
            node = event.get("node", "")
            observed[node] += 1
            source = nodes.get(node, {}).get("source", {}).get("path", "")
            if source.startswith(("observer_runtime/", "static/graph/")) or node.startswith(
                ("observer:", "bo_observer.")
            ):
                observer_events.append(event.get("id"))
            status = event.get("outputs", {}).get("status")
            if nodes.get(node, {}).get("layer") == "api" and event.get("phase") == "return":
                api_returns.append(type(status) is int and 100 <= status <= 599)
            if (
                nodes.get(node, {}).get("layer") == "api"
                and type(status) is int
                and 100 <= status <= 599
            ):
                inputs = event.get("inputs", {})
                statuses[(inputs.get("method", ""), inputs.get("route", ""), status)] += 1
        health = run.get("probe_health", {})
        diagnostics = run.get("observer_diagnostics", {})
        runs.append(
            {
                "case": run.get("case"),
                "mode": run.get("mode"),
                "events": len(events),
                "event_builds": sorted({event.get("build_id", "") for event in events}),
                "producer_errors": health.get("errors"),
                "dropped": health.get("dropped"),
                "collector_gaps": diagnostics.get("collector_gaps"),
                "data_errors": health.get("data_errors"),
            }
        )
    checks["no_detected_observer_runtime_events"] = not observer_events if payload else None
    checks["observed_event_builds_match"] = (
        all(set(run["event_builds"]) <= {accepted.get("build_id")} for run in runs)
        if runs
        else None
    )
    checks["actual_api_return_statuses_present"] = (
        bool(api_returns) and all(api_returns) if payload else None
    )
    browser_checks = summaries["browser"]["boolean_checks"]
    observer_check = next(
        (
            name
            for name in (
                "viewer_controls_no_business_events",
                "observer_queries_do_not_write_business_data",
            )
            if name in browser_checks
        ),
        None,
    )
    checks["browser_observer_exclusion_receipt"] = browser_checks.get(observer_check)
    if args.observer_receipt:
        # An independent UI-only capture has a different recording identity from
        # the real business operation. Validate both sources without merging them.
        observer = evidence.read(args.observer_receipt) or {}
        start = observer.get("empty_start", {})
        before = observer.get("empty_active_before", {}).get("active", {})
        after = observer.get("empty_active_after", {}).get("active", {})
        stop = observer.get("empty_stop", {})
        saved = observer.get("empty_recording", {})
        identity = saved.get("id")
        observer_path = (
            "bo_stategraph/data/recordings/" + identity + ".json"
            if isinstance(identity, str) and re.fullmatch(r"[a-zA-Z0-9_-]+", identity)
            else None
        )
        actual = evidence.read(observer_path) if observer_path else None
        actual = actual or {}
        boundaries = [start, before, after, stop]
        checks["observer_capture_identity"] = bool(identity) and all(
            value.get("id") == identity for value in [*boundaries, actual]
        )
        checks["observer_capture_build"] = bool(accepted.get("build_id")) and all(
            value.get("build_id") == accepted["build_id"] for value in [*boundaries, actual]
        )
        counts = [value.get("events") for value in [*boundaries, saved]]
        checks["observer_active_capture_delta_zero"] = all(
            type(value) is int and value == 0 for value in counts
        ) and all(value.get("status") == "recording" for value in [start, before, after])
        checks["observer_saved_capture_empty_and_complete"] = (
            actual.get("status") == "stopped"
            and stop.get("status") == "stopped"
            and actual.get("events") == []
            and actual.get("commands") == []
            and all(value.get("gaps") == [] for value in [*boundaries, saved, actual])
            and all(
                value.get("capture", {}).get("mode") == "all" for value in [start, saved, actual]
            )
            and actual.get("capture_filtered") == 0
        )
        equal(
            "observer_saved_capture_digest",
            saved.get("raw_sha256"),
            evidence.files.get(observer_path, {}).get("sha256"),
        )
        settlement = saved.get("producer_settlement", {})
        checks["observer_capture_fully_drained"] = (
            settlement.get("flushed") is True
            and type(settlement.get("pending")) is int
            and settlement["pending"] == 0
            and all(
                type(settlement.get(key)) is int for key in ("target", "completed", "submitted")
            )
            and settlement.get("target")
            == settlement.get("completed")
            == settlement.get("submitted")
        )
        ack = observer.get("empty_save_ack", {})
        posts = observer.get("preference_posts", [])
        graph_url = urlparse((receipts["browser"] or {}).get("graph_url", ""))
        sessions = parse_qs(graph_url.query).get("vl_session", [])
        request_shape = bool(posts) and all(
            urlparse(post.get("url", "")).netloc == graph_url.netloc
            and urlparse(post.get("url", "")).path.endswith("/preferences")
            and post.get("status") == 200
            for post in posts
        )
        checks["observer_preferences_save_acknowledged"] = (
            request_shape
            and ack.get("acknowledged") is True
            and all(type(ack.get(key)) is int for key in ("submitted_revision", "server_revision"))
            and ack.get("server_revision", -1) >= ack.get("submitted_revision", 0)
            and any(
                post.get("submitted_revision") == ack.get("submitted_revision")
                and post.get("response_revision") == ack.get("server_revision")
                for post in posts
            )
        )
        tokens = [parse_qs(urlparse(post.get("url", "")).query).get("vl_session") for post in posts]
        tokens_redacted = bool(tokens) and all(token == ["<current-session>"] for token in tokens)
        # A placeholder cannot establish equality of the original capability bytes.
        checks["observer_preferences_saved_in_exact_scope"] = (
            None
            if tokens_redacted
            else request_shape and len(sessions) == 1 and all(token == sessions for token in tokens)
        )
        namespace = {}
        if len(sessions) == 1 and re.fullmatch(r"[a-zA-Z0-9_-]+", sessions[0]):
            path = evidence.path(
                "bo_stategraph/config/views/conversations/" + sessions[0] + ".json"
            )
            raw = path.read_bytes()
            namespace = json.loads(raw)
            namespace_digest = digest(raw)
            namespace_stable = digest(path.read_bytes()) == namespace_digest
        else:
            namespace_digest, namespace_stable = None, False
        checks["observer_preferences_current_namespace_file"] = (
            namespace_stable
            and namespace.get("project_id") == (project or {}).get("project_id")
            and type(namespace.get("revision")) is int
            and type(ack.get("server_revision")) is int
            and namespace["revision"] >= ack["server_revision"]
        )
        default_before = observer.get("empty_before", {})
        default_after = observer.get("empty_after", {})
        current_default_path = evidence.path("bo_stategraph/config/views/local.json")
        current_default_raw = current_default_path.read_bytes()
        current_default = json.loads(current_default_raw)
        checks["observer_default_stable_during_measurement"] = default_before.get(
            "default_sha256"
        ) == default_after.get("default_sha256") == digest(
            current_default_raw
        ) and default_before.get(
            "default_revision"
        ) == default_after.get(
            "default_revision"
        ) == current_default.get(
            "revision"
        )
        exclusion_requirements = (
            "observer_capture_identity",
            "observer_capture_build",
            "observer_active_capture_delta_zero",
            "observer_saved_capture_empty_and_complete",
            "observer_saved_capture_digest",
            "observer_capture_fully_drained",
            "observer_preferences_save_acknowledged",
        )
        checks["browser_observer_exclusion_receipt"] = observer.get("checks", {}).get(
            "viewer_controls_no_business_events"
        ) is True and all(checks.get(key) is True for key in exclusion_requirements)
        observer_check = "explicit observer sidecar: viewer_controls_no_business_events"
        summaries["observer"] = {
            "path": args.observer_receipt,
            "sha256": evidence.files.get(args.observer_receipt, {}).get("sha256"),
            "recording_path": observer_path,
            "recording_id": identity,
            "boundary_event_counts": counts,
            "saved_event_count": len(actual.get("events", [])),
            "pending": settlement.get("pending"),
            "preference_post_count": len(posts),
            "save_acknowledged": ack.get("acknowledged"),
            "request_capabilities_redacted": tokens_redacted,
            "namespace_path": "bo_stategraph/config/views/conversations/<current-session>.json",
            "namespace_sha256": namespace_digest,
            "namespace_revision": namespace.get("revision"),
            "acknowledged_server_revision": ack.get("server_revision"),
            "default_revision_during_measurement": current_default.get("revision"),
            "actions": observer.get("actions", []),
        }
    layers = {
        layer: {
            "declared": sum(node.get("layer") == layer for node in nodes.values()),
            "directly_observed": sum(
                node.get("layer") == layer and identity in observed
                for identity, node in nodes.items()
            ),
        }
        for layer in sorted({node.get("layer", "unknown") for node in nodes.values()})
    }
    old_prefix = "review/" + args.phase + "/pre-upgrade/"
    old_project = evidence.read(
        old_prefix + cfg.get("model", "bo_stategraph/project.json"), required=False
    )
    old_cfg = evidence.read(old_prefix + "sync.json", required=False)
    old_ids = {node["id"] for node in model_of(old_project).get("nodes", [])}
    old_prefs = evidence.read(old_prefix + "bo_stategraph/config/views/local.json", required=False)
    prefs = evidence.read("bo_stategraph/config/views/local.json", required=False)
    for name, expected in evidence.files.items():
        try:
            if digest(evidence.path(name).read_bytes()) != expected["sha256"]:
                evidence.pending.append("Evidence changed during audit: " + name)
        except (OSError, ValueError):
            evidence.pending.append("Evidence disappeared during audit: " + name)
    pending = (
        evidence.pending
        + ["Mismatched evidence: " + name for name, value in checks.items() if value is False]
        + ["Unproven check: " + name for name, value in checks.items() if value is None]
    )
    pending += [
        "Native category not passed: " + name
        for name in ("mapping", "state_rules", "project_checks", "business")
        if native.get(name, {}).get("status") != "passed"
    ]
    return {
        "audit_kind": "Existing-evidence consistency only; no application imports, requests, native commands or trial writes",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "trial": str(evidence.root),
        "phase": args.phase,
        "status": "needs_review" if pending else "local_receipts_consistent",
        "identity_checks": checks,
        "accepted": accepted,
        "installed_release": version.get("release"),
        "source_hashes": source_hashes,
        "accepted_inventory_hashes": inventory_hashes,
        "advisory_inputs": advisory_inputs,
        "native_categories": native,
        "native_runs": runs,
        "declared_layers": layers,
        "static_structure": {
            "revision": code.get("revision"),
            "nodes": len(code.get("nodes", [])),
            "edges": len(code.get("edges", [])),
            "api_endpoints": sum(
                node.get("code_role") == "endpoint" for node in code.get("nodes", [])
            ),
            "directories": sum(
                node.get("code_role") == "directory" for node in code.get("nodes", [])
            ),
            "files": sum(node.get("code_role") == "file" for node in code.get("nodes", [])),
        },
        "http_status_observations": [
            {"method": method, "route": route, "status": status, "count": count}
            for (method, route, status), count in sorted(statuses.items())
        ],
        "observer_runtime_event_ids_detected": observer_events,
        "browser_observer_exclusion_basis": observer_check,
        "review_receipts": summaries,
        "recording": {
            "path": recording_path,
            "id": recording.get("id"),
            "build_id": recording.get("build_id"),
            "status": recording.get("status"),
            "events": len(recording.get("events", [])),
            "runtime_frames": len(recording.get("runtime_frames", {}).get("frames", [])),
            "gaps": len(recording.get("gaps", [])),
        },
        "iteration": {
            "previous_snapshot_available": old_project is not None,
            "retained_node_ids": len(old_ids & nodes.keys()),
            "added_node_ids": sorted(nodes.keys() - old_ids) if old_project else None,
            "removed_node_ids": sorted(old_ids - nodes.keys()) if old_project else None,
            "source_scope_before": (old_cfg or {}).get("source_scope"),
            "source_scope_now": cfg.get("source_scope"),
            "layout_preferences": preference_changes(old_prefs, prefs),
        },
        "evidence_files": evidence.files,
        "pending_or_inconsistent": pending,
        "human_review": [
            "Current candidate ID is linked through retained native receipts, not independently recomputed by executing project tools.",
            "Event counts cover direct raw IDs; projected state residence/API periods need browser review.",
            "HTTP numbers are observed outputs; semantic expectations remain in the separate business assertions.",
            "Observer exclusion detection covers identifiable runtime sources plus the browser receipt, not arbitrary unknown instrumentation.",
            "Review changed layout positions, all intended layers and remark privacy through the actual browser screenshots; old or identity-unbound browser receipts are not fresh execution proof.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=Path, default=DEFAULT_TRIAL)
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--out", required=True, help="New evidence basename under this audit directory"
    )
    parser.add_argument(
        "--recording", help="Existing browser recording JSON, relative to the trial"
    )
    parser.add_argument("--replay-recording", help="Existing replay recording JSON when it differs")
    parser.add_argument(
        "--observer-receipt",
        help="Separate existing active UI-only recording measurement; business browser identity stays separate",
    )
    parser.add_argument(
        "--receipt",
        action="append",
        default=[],
        metavar="KIND=PATH",
        help="Select an existing current/docs/api/browser/replay/runtime receipt",
    )
    args = parser.parse_args()
    if not all(re.fullmatch(r"[a-zA-Z0-9_-]+", name) for name in (args.phase, args.out)):
        parser.error("Use simple phase and evidence basenames")
    if any("=" not in item or item.split("=", 1)[0] not in RECEIPTS for item in args.receipt):
        parser.error("Unknown receipt kind")
    paths = [HERE / (args.out + suffix) for suffix in (".json", ".md")]
    if any(path.exists() for path in paths):
        parser.error("Existing evidence is immutable; choose a new --out name")
    report = audit(args)
    with paths[0].open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    lines = [
        "# Trial evidence audit",
        "",
        "Phase: `" + args.phase + "`. Status: `" + report["status"] + "`.",
        "",
        "This reads existing source hashes and receipts; it does not run the application or certify user intent.",
        "",
        "Native categories:",
    ]
    lines += [
        "- " + name + ": " + item["status"] for name, item in report["native_categories"].items()
    ]
    lines += ["", "Pending or inconsistent evidence:"] + [
        "- " + item
        for item in report["pending_or_inconsistent"]
        or ["No mismatch detected in the selected receipts; human review remains required."]
    ]
    lines += ["", "Human review:"] + ["- " + item for item in report["human_review"]]
    with paths[1].open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "evidence": [str(path) for path in paths],
                "status": report["status"],
                "pending": len(report["pending_or_inconsistent"]),
            }
        )
    )


if __name__ == "__main__":
    main()
