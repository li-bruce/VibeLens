"""Exercise canonical source ownership with isolated, synthetic fixture code."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
REPO = next(parent for parent in OUTPUT.parents if (parent / "skills/vibelens/SKILL.md").is_file())
sys.path.insert(0, str(REPO / "skills/vibelens/scripts"))

from bo_observer.source_scope import compile_scope, validate_executable_sources
from bo_observer.sources import scan
from bo_observer.workflow.bo_sync import source_inventory
from bo_observer.workflow.implementation_coverage import inventory_errors


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    fixture = Path(tempfile.mkdtemp(prefix="source-scope-adoption-20261104-", dir=REPO / ".validation"))
    config = json.loads((OUTPUT / "sync-planned.json").read_text(encoding="utf-8"))
    events = []

    def write(name, body):
        target = fixture / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    owned = {
        "web/src/index.js": "export function identity(value) { return value; }\n",
        "server/__init__.py": "",
        "server/app.py": "def identity(value):\n    return value\n",
        "modules/private-core/service.py": "def private_identity(value):\n    return value\n",
        "review/manual-tests/test_app.py": (
            "import unittest\nfrom server.app import identity\n\n"
            "class ApplicationTests(unittest.TestCase):\n"
            "    def test_application_identity(self):\n"
            "        self.assertEqual(identity('fixture'), 'fixture')\n"
        ),
    }
    for name, body in owned.items():
        write(name, body)
    write("package.json", '{"private":true,"type":"module"}\n')
    write("pyproject.toml", '[project]\nname = "scope-fixture"\nversion = "0.0.0"\n')
    write(".gitignore", "modules/private-core/\nnode_modules/\n.venv/\ndata/uploads/\nreview/runtime/\n")
    for boundary in ("node_modules", ".venv", "data/uploads", "review/runtime"):
        write(boundary + "/nested/poison.py", "invalid historical or installed content !!!\n")
    write("sync.json", json.dumps(config, indent=2) + "\n")
    events.append("planned_scope_written_before_first_inventory")
    visited = []
    blocked = [fixture / item["path"] for item in config["source_scope"]["prune"]]
    original_scandir = os.scandir

    def inspect_scandir(directory):
        path = Path(directory).resolve()
        relative = path.relative_to(fixture).as_posix()
        visited.append(relative)
        assert not any(path == prefix or path.is_relative_to(prefix) for prefix in blocked), (
            "A pruned descendant was visited: " + relative
        )
        return original_scandir(directory)

    with patch("os.scandir", side_effect=inspect_scandir):
        initial = source_inventory(fixture, config, model={}, telemetry={})
    events.append("first_inventory_completed")
    assert set(initial["files"]) == set(owned), initial
    assert set(item["path"] for item in initial["pruned"]) == {
        "node_modules", ".venv", "data/uploads", "review/runtime"
    }, initial["pruned"]
    index = scan(fixture, list(initial["files"]))
    assert not index["errors"], index["errors"]
    assert "modules/private-core/service.py::private_identity" in index["symbols"]

    app_test_command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "review/manual-tests", "-p", "test_app.py", "-v"]
    app_test = subprocess.run(app_test_command, cwd=fixture, text=True, capture_output=True)
    assert app_test.returncode == 0, app_test.stdout + app_test.stderr

    write("later_feature/new_handler.py", "def added(value):\n    return value\n")
    second = source_inventory(fixture, config, model={}, telemetry={})
    assert set(second["files"]) - set(initial["files"]) == {"later_feature/new_handler.py"}
    obligations = inventory_errors({**config, "stategraph": True, "code_files": list(initial["files"])}, second)
    assert any(isinstance(row, dict) and row.get("unregistered_source") == "later_feature/new_handler.py" for row in obligations)

    old_scope_inputs = second["scope_inputs"]
    write(".gitignore", (fixture / ".gitignore").read_text(encoding="utf-8") + "later_feature/\n")
    advisory = source_inventory(fixture, config, model={}, telemetry={})
    assert advisory["files"] == second["files"]
    assert advisory["scope_inputs"] != old_scope_inputs

    rejected_bindings = []
    policy = compile_scope(fixture, config)
    for item in config["source_scope"]["prune"]:
        name = item["path"] + "/nested/poison.py"
        try:
            validate_executable_sources(policy, model={"nodes": [{"id": "invalid-anchor", "source": {"path": name, "symbol": "hidden"}}]})
        except ValueError as error:
            rejected_bindings.append({"path": name, "error": str(error)})
        else:
            raise AssertionError("Pruned execution binding was accepted: " + name)

    narrow = {"source_scope": {"roots": ["server"]}}
    narrow_inventory = source_inventory(fixture, narrow, model={}, telemetry={})
    narrow_errors = inventory_errors({**narrow, "stategraph": True, "code_files": list(narrow_inventory["files"])}, narrow_inventory)
    assert any(isinstance(row, str) and "must scan the project root" in row for row in narrow_errors)

    # The inventory has no oracle for directory ownership: retain unclassified code.
    write("vendor/plugins/candidate.py", "def candidate(value):\n    return value\n")
    ambiguous = source_inventory(fixture, config, model={}, telemetry={})
    assert "vendor/plugins/candidate.py" in ambiguous["files"]
    invalid = deepcopy(config)
    invalid["source_scope"]["prune"].append({"path": "vendor/plugins", "category": "unknown", "reason": "Ownership pending"})
    try:
        compile_scope(fixture, invalid)
    except ValueError as error:
        unsupported_category_error = str(error)
    else:
        raise AssertionError("Unsupported ownership category was accepted")

    write("later_feature/unparsed.go", "package later\nfunc Unknown() {}\n")
    unsupported_inventory = source_inventory(fixture, config, model={}, telemetry={})
    unsupported_index = scan(fixture, list(unsupported_inventory["files"]))
    unsupported_errors = [row for row in unsupported_index["errors"] if row.get("path") == "later_feature/unparsed.go"]
    assert unsupported_errors, unsupported_index["errors"]

    product_files = [
        "skills/vibelens/SKILL.md",
        "skills/vibelens/references/source-scope.md",
        "skills/vibelens/references/requirements-dialogue.md",
        "skills/vibelens/scripts/bo_observer/source_scope.py",
        "skills/vibelens/scripts/bo_observer/workflow/bo_sync.py",
        "skills/vibelens/scripts/bo_observer/workflow/implementation_coverage.py",
        "skills/vibelens/scripts/bo_observer/sources.py",
    ]
    result = {
        "schema": "vibelens-source-scope-adoption-trial/v1",
        "evidence_class": "scripted_ai_dialogue_and_executed_isolated_fixture",
        "independent_human_evidence": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_root": str(fixture),
        "canonical_inputs": {name: sha256(REPO / name) for name in product_files},
        "status": "pass",
        "checks": {
            "scope_recorded_before_scan": True,
            "ignored_first_party_module_in_inventory_and_ast": True,
            "dependency_artifact_descendants_never_visited": True,
            "manual_test_code_in_inventory_and_executed": True,
            "new_top_level_source_independently_discovered_and_obligated": True,
            "gitignore_change_hashed_without_hiding_source": True,
            "pruned_executable_bindings_rejected": True,
            "narrow_roots_reject_full_project_coverage_claim": True,
            "ambiguous_unclassified_subtree_retained": True,
            "unsupported_scope_category_rejected": True,
            "unsupported_language_reported_incomplete": True,
        },
        "sequence": events,
        "initial_inventory": initial,
        "initial_ast_symbols": sorted(index["symbols"]),
        "scandir_visited_directories": visited,
        "unvisited_descendants_counted_as_inspected": False,
        "new_source_obligations": obligations,
        "gitignore_scope_inputs_before": old_scope_inputs,
        "gitignore_scope_inputs_after": advisory["scope_inputs"],
        "rejected_executable_bindings": rejected_bindings,
        "narrow_scope_errors": narrow_errors,
        "ambiguous_ownership": {
            "path": "vendor/plugins",
            "status": "pending_external_ownership_decision",
            "inventory_behavior": "Unclassified source retained; no dependency status inferred from path name",
            "valid_clarification": "vendor/plugins contains your maintained application code or installed third-party packages?",
            "boundary": "A syntactically valid dependency/artifact declaration is an ownership decision, not proof of true ownership; the scanner cannot infer the user's answer.",
        },
        "unsupported_category_error": unsupported_category_error,
        "unsupported_language_errors": unsupported_errors,
        "manual_test_execution": {
            "command_argv": app_test_command,
            "cwd": str(fixture),
            "exit_code": app_test.returncode,
            "stdout": app_test.stdout,
            "stderr": app_test.stderr,
        },
        "limitations": [
            "The public exchange is scripted, not an independent human trial.",
            "Fixture checks exercise static scope and one synthetic test; no real application, business graph, runtime monitoring or acceptance result is established.",
            "The fixture declares ownership explicitly; canonical validation rejects malformed scope but does not prove semantic ownership or complete business mapping.",
        ],
    }
    (OUTPUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "fixture_root": str(fixture), "results": str(OUTPUT / "results.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
