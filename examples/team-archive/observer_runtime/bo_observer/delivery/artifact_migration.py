"""Journaled project/discovery upgrades with exact-byte rollback.

Only the named canonical documents are migrated. Personal views, runtime records,
source files and historical confirmation snapshots are never rewritten. Readers
refuse a pending journal; recovery refuses to overwrite concurrent external edits.
"""

from base64 import b64decode, b64encode
from copy import deepcopy
import json
import os
from pathlib import Path
import uuid

from ..concepts.common import digest
from ..definition_errors import require
from ..graph.behavior_model import contained
from ..project_artifacts import (
    ACTIVE_MIGRATION,
    byte_hash,
    load_project,
    parse,
    portable_path,
    references,
    validate_documents,
)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def replace_bytes(path, raw):
    """Flush before replacing one file; the journal coordinates the whole set."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def plan(
    root,
    *,
    project="bo_stategraph/project.json",
    discovery="discovery.json",
    behavior="bo_stategraph/behavior.json",
    refresh=False,
):
    """Prepare portable changes without asserting fresh review or inventing behavior."""
    root = Path(root).resolve()
    for name in (project, discovery, behavior):
        portable_path(name)
    require(len({project, discovery, behavior}) == 3, "artifact_path_collision", "/", project)
    options = {"project": project, "discovery": discovery, "behavior": behavior, "refresh": refresh}
    if refresh:
        return _refresh_plan(root, options)
    original_bytes = contained(root, project).read_bytes()
    original = load_project(root, project)
    require(
        parse(original_bytes) == original,
        "artifacts_changed_during_read",
        "/",
        "Project changed while loading the migration basis",
    )
    if original["protocol"] == "bo-project/v2":
        return {
            "schema": "bo-artifact-migration/v1",
            "options": options,
            "changes": [],
            "inputs": {project: byte_hash(original_bytes)},
            "warnings": ["Project already uses v2; references are unchanged"],
        }
    documents, changes, inputs = {}, [], {}
    upgraded = deepcopy(original)
    upgraded.update(
        protocol="bo-project/v2",
        contracts={"discovery": None, "behavior": None, "analysis_profiles": []},
    )
    for role, name in (("discovery", discovery), ("behavior", behavior)):
        path = contained(root, name)
        if not path.exists():
            continue
        before = path.read_bytes()
        inputs[name] = byte_hash(before)
        value = parse(before)
        after = before
        if role == "discovery" and value.get("schema") == "business-discovery/v2":
            value = deepcopy(value)
            value["schema"] = "business-discovery/v3"
            value["construction"] = {"targets": [], "obligations": [], "presentations": []}
            after = encode(value)
            changes.append(
                {
                    "path": name,
                    "before_sha256": byte_hash(before),
                    "after_sha256": byte_hash(after),
                    "value": value,
                }
            )
        documents[role] = value
        upgraded["contracts"][role] = {
            "path": name,
            "sha256": byte_hash(after),
            "schema": value["schema"],
        }
    validate_documents(upgraded, documents)
    before = original_bytes
    inputs[project] = byte_hash(before)
    require(
        all(
            byte_hash(contained(root, path).read_bytes()) == expected
            for path, expected in inputs.items()
        ),
        "artifacts_changed_during_read",
        "/",
        "Input changed while constructing the migration plan",
    )
    changes.append(
        {
            "path": project,
            "before_sha256": byte_hash(before),
            "after_sha256": byte_hash(encode(upgraded)),
            "value": upgraded,
        }
    )
    return {
        "schema": "bo-artifact-migration/v1",
        "options": options,
        "inputs": inputs,
        "changes": changes,
        "warnings": ["New construction review and runtime evidence remain pending"],
    }


def _refresh_plan(root, options):
    """Stage new reference hashes after explicit definition edits, without acceptance."""
    from ..protocol import validate_project

    require(
        not contained(root, ACTIVE_MIGRATION).exists(), "migration_pending", "/", "Recover first"
    )
    name = options["project"]
    raw = contained(root, name).read_bytes()
    project = validate_project(parse(raw))
    require(project["protocol"] == "bo-project/v2", "refresh_version", "/", "Migrate to v2 first")
    inputs, documents = {name: byte_hash(raw)}, {}
    for role, ref in references(project):
        payload = contained(root, ref["path"]).read_bytes()
        inputs[ref["path"]] = byte_hash(payload)
        value = parse(payload)
        require(value.get("schema") == ref["schema"], "artifact_version_mismatch", "/", ref["path"])
        ref["sha256"] = byte_hash(payload)
        if role == "analysis_profiles":
            documents.setdefault(role, []).append(value)
        else:
            documents[role] = value
    validate_documents(project, documents)
    require(
        all(
            byte_hash(contained(root, path).read_bytes()) == expected
            for path, expected in inputs.items()
        ),
        "artifacts_changed_during_read",
        "/",
        "Retry the plan against a stable definition set",
    )
    after = encode(project)
    # Reformatting alone is not a required migration.
    changed = project != parse(raw)
    return {
        "schema": "bo-artifact-migration/v1",
        "options": options,
        "inputs": inputs,
        "changes": (
            [
                {
                    "path": name,
                    "before_sha256": byte_hash(raw),
                    "after_sha256": byte_hash(after),
                    "value": project,
                }
            ]
            if changed
            else []
        ),
        "warnings": [
            "Reference refresh validates definitions; confirmation and runtime evidence remain separate"
        ],
    }


def _journal(root, identity):
    require(
        len(identity) == 64 and all(c in "0123456789abcdef" for c in identity),
        "migration_identity",
        "/",
        identity,
    )
    return contained(root, ".stategraph/migrations/" + identity + "/journal.json")


def apply(root, proposal):
    """Apply only a freshly reproducible plan; leave a recoverable journal on interruption."""
    root = Path(root).resolve()
    require(proposal.get("schema") == "bo-artifact-migration/v1", "migration_version", "/", "")
    current = plan(root, **proposal["options"])
    require(
        current == proposal, "stale_migration_plan", "/", "Re-plan after canonical files change"
    )
    if not current["changes"]:
        return {"valid": True, "status": "unchanged", "changes": []}
    identity = digest(proposal)
    journal_path = _journal(root, identity)
    require(not journal_path.exists(), "migration_already_recorded", "/", identity)
    lock = contained(root, ACTIVE_MIGRATION)
    lock.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation serializes cooperating writers. A crash before the
    # journal is complete is deliberately blocked, never guessed away.
    with lock.open("xb") as stream:
        stream.write(encode({"id": identity, "plan": proposal}))
        stream.flush()
        os.fsync(stream.fileno())
    records = []
    try:
        for change in proposal["changes"]:
            before = contained(root, change["path"]).read_bytes()
            require(
                byte_hash(before) == change["before_sha256"],
                "stale_migration_input",
                "/" + change["path"],
                "File changed after planning",
            )
            records.append(
                {
                    "path": change["path"],
                    "before": b64encode(before).decode("ascii"),
                    "after": b64encode(encode(change["value"])).decode("ascii"),
                }
            )
        journal = {
            "schema": "bo-migration-journal/v1",
            "id": identity,
            "plan": proposal,
            "state": "prepared",
            "files": records,
        }
        replace_bytes(journal_path, encode(journal))
        # Recheck unchanged pinned inputs too, before any canonical write.
        require(
            all(
                byte_hash(contained(root, path).read_bytes()) == expected
                for path, expected in proposal["inputs"].items()
            ),
            "stale_migration_input",
            "/",
            "Input changed while preparing snapshots",
        )
        journal["state"] = "applying"
        replace_bytes(journal_path, encode(journal))
        for item in records:
            path = contained(root, item["path"])
            require(
                path.read_bytes() == b64decode(item["before"]),
                "concurrent_artifact_edit",
                "/" + item["path"],
                "A writer changed this file during migration",
            )
            replace_bytes(path, b64decode(item["after"]))
        require(
            all(
                contained(root, item["path"]).read_bytes() == b64decode(item["after"])
                for item in records
            ),
            "concurrent_artifact_edit",
            "/",
            "Output changed during migration",
        )
        journal["state"] = "committed"
        replace_bytes(journal_path, encode(journal))
        lock.unlink()
    except Exception:
        if journal_path.exists():
            recover(root)
        else:
            # No canonical writes preceded durable snapshots.
            lock.unlink(missing_ok=True)
        raise
    load_project(root, proposal["options"]["project"])
    return {
        "valid": True,
        "status": "committed",
        "id": identity,
        "changes": [item["path"] for item in records],
    }


def recover(root):
    """Restore the exact previous set, or finish a fully committed journal."""
    root = Path(root).resolve()
    lock = contained(root, ACTIVE_MIGRATION)
    require(lock.exists(), "no_pending_migration", "/", "No interrupted migration")
    marker = parse(lock.read_bytes())
    identity = marker["id"]
    journal_path = _journal(root, identity)
    if not journal_path.exists():
        # No canonical write can precede the first durable journal. Check the
        # original input set before releasing a lock interrupted during preparation.
        require(
            digest(marker["plan"]) == identity
            and all(
                byte_hash(contained(root, portable_path(name)).read_bytes()) == expected
                for name, expected in marker["plan"]["inputs"].items()
            ),
            "migration_recovery_conflict",
            "/",
            "Input changed before snapshots completed",
        )
        lock.unlink()
        return {"valid": True, "status": "rolled_back", "id": identity}
    journal = parse(journal_path.read_bytes())
    require(
        journal["schema"] == "bo-migration-journal/v1"
        and journal["id"] == identity
        and digest(journal["plan"]) == identity,
        "invalid_migration_journal",
        "/",
        identity,
    )
    changes = journal["plan"]["changes"]
    require(len(changes) == len(journal["files"]), "invalid_migration_journal", "/", identity)
    desired = "after" if journal["state"] == "committed" else "before"
    # Inspect every destination first, so one conflict cannot cause a partial rollback.
    for item, change in zip(journal["files"], changes):
        require(
            item["path"] == change["path"]
            and all(
                byte_hash(b64decode(item[stage])) == change[stage + "_sha256"]
                for stage in ("before", "after")
            ),
            "invalid_migration_snapshot",
            "/",
            identity,
        )
        path = contained(root, portable_path(item["path"]))
        require(
            path.exists()
            and path.read_bytes() in (b64decode(item["before"]), b64decode(item["after"])),
            "migration_recovery_conflict",
            "/" + item["path"],
            "Preserve the external edit",
        )
    for item in journal["files"]:
        replace_bytes(contained(root, item["path"]), b64decode(item[desired]))
    journal["state"] = "committed" if desired == "after" else "rolled_back"
    replace_bytes(journal_path, encode(journal))
    lock.unlink()
    return {"valid": True, "status": journal["state"], "id": identity}


def check(root, project="bo_stategraph/project.json"):
    value = load_project(root, project)
    return {
        "valid": True,
        "protocol": value["protocol"],
        "artifacts": [ref["path"] for _, ref in references(value)],
        "meaning_confirmation": "not_checked",
        "runtime_evidence": "not_checked",
    }
