"""Discover project changes independently of the graph and emit an internal AI task.

Call `scan` after edits, or `watch` from a project-local editor integration.
This discovers work; it does not claim to invoke an arbitrary editor's AI.
"""

import argparse
import ast
from copy import deepcopy
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from ..model_io import read_model
from ..development import questions
from ..graph.source_files import SourceFiles

IGNORED = {
    ".git",
    ".venv",
    ".agents",
    ".codex",
    "node_modules",
    "__pycache__",
    ".stategraph",
    ".validation",
    ".planning",
    ".release",
    ".pytest_cache",
    ".tmp",
    "dist",
}


def infrastructure_path(name):
    path = Path(name)
    return (
        bool(
            set(path.parts)
            & {
                "tests",
                "tooling",
                "observer_generated",
                "observer_runtime",
                "review",
                "history",
                "scratch",
            }
        )
        or path.stem.startswith(("bo_", "test_", "observer_"))
        or path.name in {"run.py", "validate.py"}
        or path.parent.as_posix() == "bo_stategraph"
        and path.name in {"__init__.py", "execution_contract.py", "query.py"}
    )


def source_paths(start, supported):
    """Prune global generated/cache trees before reading their descendants.

    Ordinary scope exclusions are deliberately not pruned: their code must still
    be inspected for hidden application implementations and entrypoints.
    """
    if start.is_file():
        yield start
        return
    for parent, directories, files in os.walk(start, followlinks=False):
        kept = []
        for name in directories:
            if name in IGNORED:
                continue
            try:
                info = (Path(parent) / name).lstat()
            except OSError:
                continue
            junction = getattr(info, "st_reparse_tag", 0) == getattr(
                stat, "IO_REPARSE_TAG_MOUNT_POINT", -1
            )
            if not stat.S_ISLNK(info.st_mode) and not junction:
                kept.append(name)
        directories[:] = kept
        for name in files:
            if supported(name):
                path = Path(parent) / name
                if path.is_file():
                    yield path


def source_inventory(root, cfg, *, inspection_cache=None):
    """Enumerate the configured source scope independently of existing graph nodes.

    Inspect excluded code for hidden application entrypoints. A reviewed, unchanged
    runtime copy can be excluded using its managed-file fingerprint.
    """
    root = Path(root).absolute().resolve()
    reader = SourceFiles(root)
    inspected = set()
    known = None
    scope = cfg.get("source_scope", {})
    if not isinstance(scope, dict):
        raise ValueError("source scope must be an object")
    exclusions = scope.get("exclude", {})
    if not isinstance(exclusions, dict) or any(
        not isinstance(reason, str) or not reason.strip() for reason in exclusions.values()
    ):
        raise ValueError("each source exclusion needs a reason")
    roots = scope.get("roots", ["."])
    if (
        not isinstance(roots, list)
        or not roots
        or any(not isinstance(p, str) or not p.strip() for p in roots)
    ):
        raise ValueError("source scope needs nonempty project-relative roots")
    files, excluded, hidden_entrypoints, hidden_implementations = {}, {}, {}, []
    for prefix in roots:
        start = (root / prefix).resolve()
        if not start.is_relative_to(root):
            raise ValueError("source scope escapes project")
        if not start.exists():
            raise ValueError("source scope is missing: " + prefix)
        try:
            from ..sources import supported_path, scan as scan_sources
        except ImportError:
            from bo_observer.sources import supported_path, scan as scan_sources
        for path in source_paths(start, supported_path):
            name = path.relative_to(root).as_posix()
            if any(part in IGNORED for part in Path(name).parts):
                continue
            if path.is_symlink():
                raise ValueError("source symlink escapes declared project: " + name)
            raw = reader.read(name)
            if raw is None:
                raise ValueError("source file became unavailable: " + name)
            # This is an optional native dependency, not observer activity. Only
            # exact managed copies of this tool's own library are excluded from
            # application coverage. A changed file returns to normal inspection.
            parts = Path(name).parts
            if len(parts) == 3 and parts[1] == "policy" and parts[0].isidentifier():
                metadata = root / parts[0] / "runtime-version.json"
                canonical = Path(__file__).resolve().parents[1] / "policy" / parts[2]
                if (
                    metadata.is_file()
                    and canonical.is_file()
                    and parts[2]
                    in {
                        "__init__.py",
                        "definition.py",
                        "projection.py",
                        "bindings.py",
                        "runtime.py",
                    }
                ):
                    managed = json.loads(metadata.read_text(encoding="utf-8")).get("files", {})
                    actual = hashlib.sha256(raw).hexdigest()
                    if (
                        managed.get(name)
                        == actual
                        == hashlib.sha256(canonical.read_bytes()).hexdigest()
                    ):
                        excluded[name] = "Managed native policy dependency; exact bundled source"
                        continue
            reason = next(
                (v for pattern, v in exclusions.items() if fnmatch.fnmatchcase(name, pattern)), None
            )
            if reason:
                excluded[name] = reason
                frozen = False
                for archive, manifest in scope.get("frozen_sources", {}).items():
                    base = (root / archive).resolve()
                    record = (root / manifest).resolve()
                    if not base.is_relative_to(root) or not record.is_relative_to(root):
                        raise ValueError("frozen source evidence escapes project")
                    if path.is_relative_to(base) and record.is_file():
                        expected = (
                            json.loads(record.read_text(encoding="utf-8-sig"))
                            .get("files", {})
                            .get(path.relative_to(base).as_posix())
                        )
                        if expected == hashlib.sha256(raw).hexdigest():
                            frozen = True
                if frozen:
                    continue
                # Reviewed shipped graph assets are not application source. A
                # modified or arbitrary excluded UI file still gets inspected.
                metadata = root / "bo_stategraph/runtime-version.json"
                if path.suffix != ".py" and metadata.is_file():
                    if known is None:
                        try:
                            from ...bo_upgrade import portable_files
                        except ImportError:
                            from bo_upgrade import portable_files
                        known = portable_files(
                            json.loads(metadata.read_text(encoding="utf-8")).get("files", {})
                        )
                    if known.get(name) == hashlib.sha256(raw).hexdigest():
                        continue
                if path.suffix == ".py" and inspection_cache is not None:
                    inspected.add(name)
                    previous = inspection_cache.get(name)
                    if previous and previous["hash"] == hashlib.sha256(raw).hexdigest():
                        if previous["implementation"]:
                            hidden_implementations.append(name)
                        if previous["entrypoints"]:
                            hidden_entrypoints[name] = deepcopy(previous["entrypoints"])
                        continue
                # An exclusion is not a way to hide an application endpoint.
                # Inspect declarations without importing or executing the file.
                try:
                    if path.suffix != ".py":
                        result = scan_sources(root, [name])
                        if result["errors"]:
                            hidden_entrypoints[name] = result["errors"]
                        symbols = list(result["symbols"].values())
                        if not infrastructure_path(name) and symbols:
                            hidden_implementations.append(name)
                        routes = [d for v in symbols for d in v.get("entrypoints", [])]
                        if routes:
                            hidden_entrypoints[name] = routes
                        continue
                    tree = ast.parse(raw.decode("utf-8-sig"), filename=name)
                    if not infrastructure_path(name) and any(
                        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        for n in ast.walk(tree)
                    ):
                        hidden_implementations.append(name)
                    routes = [
                        ast.unparse(d)
                        for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        for d in n.decorator_list
                        if isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Attribute)
                        and d.func.attr
                        in {
                            "route",
                            "get",
                            "post",
                            "put",
                            "patch",
                            "delete",
                            "websocket",
                            "command",
                            "task",
                        }
                    ]
                    from ..graph.python_routes import registrations

                    routes.extend(item["declaration"] for item in registrations(tree, name))
                    if routes:
                        hidden_entrypoints[name] = routes
                except (SyntaxError, UnicodeError) as exc:
                    hidden_entrypoints[name] = ["cannot inspect excluded Python: " + str(exc)]
                if path.suffix == ".py" and inspection_cache is not None:
                    inspection_cache[name] = {
                        "hash": hashlib.sha256(raw).hexdigest(),
                        "implementation": name in hidden_implementations,
                        "entrypoints": deepcopy(hidden_entrypoints.get(name, [])),
                    }
            else:
                files[name] = hashlib.sha256(raw).hexdigest()
    if inspection_cache is not None:
        for name in list(inspection_cache):
            if name not in inspected:
                del inspection_cache[name]
    return {
        "files": dict(sorted(files.items())),
        "excluded": dict(sorted(excluded.items())),
        "excluded_entrypoints": hidden_entrypoints,
        "excluded_implementations": sorted(hidden_implementations),
    }


def maintenance_task(root, cfg, previous=None):
    """Compare source with the accepted baseline and describe the mapping work still needed."""
    from ..data.sync import synchronize
    from ..policy.sync import synchronize as sync_policy

    policy = sync_policy(root, model_path=cfg.get("model", "bo_stategraph/project.json"))
    if not policy["valid"]:
        return {
            "schema": "bo-maintenance/v1",
            "status": "needs_update",
            "policy": policy,
            "internal_prompt": "Repair invalid policy declarations before regenerating the graph.",
        }

    database = synchronize(root, model_path=cfg.get("model", "bo_stategraph/project.json"))
    # The optional code index follows edits once the developer has enabled it.
    # Off means no extra index construction during ordinary maintenance.
    from ..model_io import read_model

    declaration = Path(root) / cfg.get("model", "bo_stategraph/project.json")
    declared = read_model(declaration) if declaration.is_file() else {}
    if (Path(root) / ".stategraph/code-graph.json").is_file() or any(
        node.get("represents") for node in declared.get("nodes", [])
    ):
        from ..code_graph.service import CodeGraph

        CodeGraph(root).refresh()
    current = source_inventory(root, cfg)
    old = (previous or {}).get("files", {})
    changed = sorted(
        p for p in set(old) | set(current["files"]) if old.get(p) != current["files"].get(p)
    )
    registered = set(cfg.get("code_files", []))
    if not cfg.get("source_scope") and not cfg.get("stategraph"):
        registered |= set(cfg.get("watch_files", []))
    unregistered = sorted(set(current["files"]) - registered)
    gaps = []
    if cfg.get("stategraph"):
        try:
            from ...code_structure import scan
            from ...implementation_coverage import static_errors, inventory_errors
        except ImportError:
            from code_structure import scan
            from implementation_coverage import static_errors, inventory_errors
        path = (Path(root) / cfg["model"]).resolve()
        if not path.is_relative_to(Path(root).resolve()):
            raise ValueError("model escapes project")
        model = read_model(path)
        index = scan(root, current["files"])
        gaps = (
            index["errors"]
            + inventory_errors(cfg, current)
            + static_errors(model.get("implementation"), model, index)
        )
        from ..observation.telemetry import business_layer_errors, load_registrations

        gaps.extend(business_layer_errors(model))
        try:
            load_registrations(root, model)
        except (ValueError, OSError) as error:
            gaps.append("telemetry registration: " + str(error))
    digest = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    return {
        "schema": "bo-maintenance/v1",
        "source_id": digest,
        "inventory": current,
        "changed_files": changed,
        "unregistered_files": unregistered,
        "implementation_gaps": gaps,
        "database": database,
        "policy": policy,
        "status": (
            "needs_update"
            if changed
            or unregistered
            or gaps
            or not database["valid"]
            or current["excluded_entrypoints"]
            or current["excluded_implementations"]
            else "current"
        ),
        "internal_prompt": "Review the listed implementation changes. Update affected business abstractions, states, function/parameter mappings, and probes. "
        "Do not omit new entrypoints because the old graph lacks them. Match features, parameters, and runtime cases through the implementation inventory. "
        "Exclusions must not bypass business implementation. Check real relations and filter boundaries in every view, then run project acceptance. "
        "Do not ask users to maintain observation files. Ask only when new business ambiguity appears.",
        "confirmations": (
            questions(
                {
                    "model": model,
                    "selection": {
                        "mode": cfg.get("stategraph", {}).get("development_mode"),
                        "source": cfg.get("stategraph", {}).get("decision_source"),
                        "answer": cfg.get("stategraph", {}).get("decision", ""),
                        "locator": "sync.json",
                    },
                },
                index,
                (
                    json.loads((Path(root) / cfg["discovery"]).read_text(encoding="utf-8-sig"))
                    if cfg.get("discovery")
                    else None
                ),
            )
            if cfg.get("stategraph")
            else {}
        ),
        "ai_invocation": "host_or_coding_agent_required",
    }


def main():
    """Publish one maintenance scan or watch for changed results without accepting the changes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scan", "watch"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default="sync.json")
    parser.add_argument("--interval", type=float, default=1)
    args = parser.parse_args()
    root = Path(args.root).absolute().resolve()
    target = root / ".stategraph/maintenance.json"
    previous, last = None, None
    baseline = root / ".stategraph/source-baseline.json"
    while True:
        cfg_path = (root / args.config).resolve()
        if not cfg_path.is_relative_to(root):
            raise ValueError("config escapes project")
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            # Reading a detected change never acknowledges it. Only accept updates
            # this baseline after the full verification gate succeeds.
            previous = (
                json.loads(baseline.read_text(encoding="utf-8")) if baseline.exists() else None
            )
            value = maintenance_task(root, cfg, previous)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            # Editors can briefly leave configuration incomplete. Keep watching,
            # report the missing evidence, and retry without replacing the baseline.
            value = {
                "schema": "bo-maintenance/v1",
                "status": "needs_update",
                "errors": [str(error)],
                "inventory": None,
                "internal_prompt": "Fix source scan configuration and rescan; mapping completeness cannot currently be assessed.",
                "ai_invocation": "host_or_coding_agent_required",
            }
        # Registration and an accepted baseline can change without changing file
        # bytes. Publish those task transitions too, rather than leaving stale work.
        task_id = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        if task_id != last:
            try:
                try:
                    from ...sync_io import write
                except ImportError:
                    from sync_io import write
                write(target, value)
            except OSError as error:
                # Publishing failure does not acknowledge the source or kill a
                # watcher. A one-shot scan must return a visible failure.
                print(
                    json.dumps(
                        {
                            "status": "needs_update",
                            "publication_error": str(error),
                            "retrying": args.command == "watch",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                if args.command == "scan":
                    return 1
            else:
                print(json.dumps(value, ensure_ascii=False), flush=True)
                last = task_id
        if args.command == "scan":
            return 1 if value.get("errors") else 0
        time.sleep(max(0.1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
