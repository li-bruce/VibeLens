"""Read a revision-consistent set of project-owned definition artifacts.

The envelope pins exact bytes. Definition legality, intent confirmation, native
binding and runtime evidence remain separate checks. A hash proves none of them.
No reader repairs files or updates expected hashes as a side effect.
"""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

from .definition_errors import require
from .graph.behavior_model import contained

PROJECT_VERSIONS = {"bo-project/v1", "bo-project/v2"}
REFERENCE_VERSIONS = {
    "discovery": {"business-discovery/v1", "business-discovery/v2", "business-discovery/v3"},
    "behavior": {"bo-behavior/v1"},
    "analysis_profiles": {"bo-analysis-profile/v1"},
}
ACTIVE_MIGRATION = ".stategraph/migrations/active.json"


def byte_hash(raw):
    return sha256(raw).hexdigest()


def parse(raw):
    """Reject duplicate keys and non-finite numbers before any semantic reader."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Non-finite JSON value: " + value)

    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)


def portable_path(name):
    """Use one cross-language, project-relative spelling with no traversal."""
    require(
        isinstance(name, str)
        and bool(name)
        and "\\" not in name
        and ":" not in name
        and not name.startswith("/")
        and all(part not in {"", ".", ".."} for part in name.split("/")),
        "artifact_path",
        "/contracts",
        str(name),
    )
    return PurePosixPath(name).as_posix()


def references(project):
    """Yield configured artifacts; absent contracts remain explicitly absent."""
    for role, value in project.get("contracts", {}).items():
        for ref in value if isinstance(value, list) else ([value] if value else []):
            yield role, ref


def validate_references(project):
    """Validate reference roles without claiming that external bytes were read."""
    paths = set()
    for role, ref in references(project):
        name = portable_path(ref["path"])
        require(name not in paths, "duplicate_artifact_path", "/contracts", name)
        paths.add(name)
        require(
            ref["schema"] in REFERENCE_VERSIONS[role],
            "unsupported_artifact_version",
            "/contracts/" + role,
            ref["schema"],
        )
    require(
        not project["contracts"]["behavior"] or project["contracts"]["discovery"],
        "missing_discovery",
        "/contracts/behavior",
        "Behavior needs its canonical discovery",
    )


def validate_documents(project, documents):
    """Resolve shared definitions through existing validators, without native execution."""
    from .protocol import schema_check, validate_project

    validate_project(project)
    discovery = documents.get("discovery")
    if discovery is not None:
        from .workflow.requirements_dialogue import assess as assess_dialogue

        declared_project = discovery.get("project_id")
        require(
            declared_project == project["project_id"]
            or discovery.get("schema") == "business-discovery/v1"
            and declared_project is None,
            "project_mismatch",
            "/contracts/discovery",
            "Discovery belongs to another project",
        )
        result = assess_dialogue(discovery)
        require(result["valid"], "invalid_discovery", "/contracts/discovery", str(result["errors"]))
    behavior = documents.get("behavior")
    if behavior is not None:
        from .behavior import assess

        result = assess(behavior, discovery)
        require(result["valid"], "invalid_behavior", "/contracts/behavior", str(result["errors"]))
    for profile in documents.get("analysis_profiles", []):
        schema_check(profile, "analysis-profile")
        require(
            behavior is not None,
            "missing_behavior",
            "/contracts/analysis_profiles",
            "An analysis profile needs a configured behavior definition",
        )
        from .analysis.capabilities import admit

        result = admit(behavior, discovery, profile)
        require(
            result["status"] != "invalid",
            "invalid_analysis_profile",
            "/contracts/analysis_profiles",
            str(result),
        )
    return documents


def load_project(root, project_path="bo_stategraph/project.json"):
    """Fail closed on interrupted migrations, stale files or mixed revisions."""
    from .protocol import validate_project

    root = Path(root).resolve()
    require(
        not contained(root, ACTIVE_MIGRATION).exists(),
        "migration_pending",
        "/",
        "Recover the interrupted artifact migration before loading",
    )
    path = contained(root, portable_path(project_path))
    raw = path.read_bytes()
    project = validate_project(parse(raw))
    loaded, fingerprints = {}, {path: byte_hash(raw)}
    for role, ref in references(project):
        source = contained(root, ref["path"])
        payload = source.read_bytes()
        require(
            byte_hash(payload) == ref["sha256"],
            "artifact_revision_mismatch",
            "/contracts/" + role,
            ref["path"],
        )
        value = parse(payload)
        require(
            value.get("schema") == ref["schema"],
            "artifact_version_mismatch",
            "/contracts/" + role,
            ref["path"],
        )
        fingerprints[source] = ref["sha256"]
        if role == "analysis_profiles":
            loaded.setdefault(role, []).append(value)
        else:
            loaded[role] = value
    validate_documents(project, loaded)
    require(
        all(byte_hash(path.read_bytes()) == expected for path, expected in fingerprints.items()),
        "artifacts_changed_during_read",
        "/",
        "Retry against one stable definition set",
    )
    require(
        not contained(root, ACTIVE_MIGRATION).exists(),
        "migration_pending",
        "/",
        "A migration started during the read",
    )
    return project
