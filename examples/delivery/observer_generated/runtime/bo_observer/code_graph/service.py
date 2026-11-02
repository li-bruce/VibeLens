"""Lazy source index shared by the CLI and the optional Web code view."""

import json
from copy import deepcopy
from pathlib import Path
import threading
from ..graph.behavior_model import contained, read, digest
from ..model_io import model_from_value
from ..sources import scan
from ..workflow.bo_sync import source_inventory
from .index import build, identity
from .file_dependencies import file_units
from .query import query, representation_links
from .filesystem import inventory as project_inventory


class CodeGraph:
    def __init__(self, root, *, persist=True):
        self.root = Path(root).resolve()
        self.lock = threading.RLock()
        self.previous = None
        self.graph = None
        self.fingerprint = None
        self.persist = persist
        self.project_inspections = {}
        self.model_cache = None
        self.cache = contained(self.root, ".stategraph/code-graph.json")

    def inputs(self):
        """Use the same independently declared source scope as iteration checks."""
        config = self.root / "sync.json"
        if config.is_file():
            cfg = read(config)
        else:
            excluded = {"tests/*": "Project tests", "test_*": "Project tests"}
            metadata = self.root / "bo_stategraph/runtime-version.json"
            if metadata.is_file():
                # Exclude only exact installed copies. A project-owned executor
                # or an edited support module remains visible to source analysis.
                try:
                    from ...bo_upgrade import portable_files
                except ImportError:
                    from bo_upgrade import portable_files
                for name, expected in portable_files(read(metadata).get("files", {})).items():
                    path = contained(self.root, name)
                    if path.is_file() and digest(path.read_bytes()) == expected:
                        excluded[name] = "Unchanged managed observer support"
            cfg = {
                "model": "bo_stategraph/project.json",
                "source_scope": {
                    "roots": ["."],
                    "exclude": excluded,
                },
            }
        model_path = contained(self.root, cfg.get("model", "bo_stategraph/project.json"))
        model = {"nodes": [], "source_files": []}
        if model_path.is_file():
            raw = model_path.read_bytes()
            if self.model_cache is None or raw != self.model_cache[0]:
                parsed = model_from_value(json.loads(raw.decode("utf-8-sig")))
                self.model_cache = raw, parsed
            model = deepcopy(self.model_cache[1])
        return cfg, model

    def refresh(self):
        """Check file bytes on demand; parse only changed units and invalidate deletions."""
        with self.lock:
            cfg, model = self.inputs()
            inventory = source_inventory(self.root, cfg)
            project = project_inventory(self.root, cfg, inventory)
            # Source inventory reports hidden implementation separately from parser errors.
            fingerprint = digest([inventory, project])
            from ..sources import adapter_identity

            fingerprint = digest([fingerprint, adapter_identity()])
            if self.graph is None or fingerprint != self.fingerprint:
                index = scan(self.root, inventory["files"], self.previous)
                index["errors"] += [
                    {"path": p, "error": "Excluded application implementation"}
                    for p in inventory["excluded_implementations"]
                ]
                index["errors"] += [
                    {"path": p, "error": "Excluded entrypoint", "details": value}
                    for p, value in inventory["excluded_entrypoints"].items()
                ]
                index["errors"] += project["errors"]
                self.previous, self.graph = index, build(index, project, self.root)
                self.graph["scope"] = {
                    "files": list(inventory["files"]),
                    "excluded": inventory["excluded"],
                    "project_excluded": project["excluded"],
                }
                self.fingerprint = fingerprint
                if self.persist:
                    from ..workflow.sync_io import write

                    write(self.cache, self.graph)
            representation_links(model, self.graph)
            return self.graph, model

    def view(self, **options):
        if options.get("projection") == "project":
            return self.project_view(**options)
        with self.lock:
            graph, model = self.refresh()
            result = query(graph, model, **options)
            result["scope"] = graph["scope"]
            return result

    def project_view(self, **options):
        """Expose files/containment independently of the optional symbol parser.

        This projection never replaces or seals the full AST cache. A fresh source
        inventory keeps additions, deletions and file links visible after coding.
        """
        with self.lock:
            cfg, model = self.inputs()
            inventory = source_inventory(self.root, cfg, inspection_cache=self.project_inspections)
            project = project_inventory(self.root, cfg, inventory)
            fingerprint = digest(project)
            cached = getattr(self, "project_cache", None)
            if cached is None or cached[0] != fingerprint:
                empty = scan(self.root, [])
                units, errors = file_units(
                    self.root, inventory["files"], getattr(self, "project_units", None)
                )
                self.project_units = units
                empty["units"] = units
                empty["errors"] += errors
                empty["errors"] += project["errors"]
                graph = build(empty, project, self.root)
                graph["scope"] = {
                    "files": list(inventory["files"]),
                    "excluded": inventory["excluded"],
                    "project_excluded": project["excluded"],
                }
                self.project_cache = fingerprint, graph
            graph = self.project_cache[1]
            # Source bindings resolve to files here; optional symbols remain absent.
            graph = {
                **graph,
                "symbols": {
                    node["source"]["path"]
                    + "::"
                    + node["source"].get("symbol", ""): identity("file", node["source"]["path"])
                    for node in model.get("nodes", [])
                    if node.get("source", {}).get("path")
                    and node["source"]["path"] in project["entries"]
                },
            }
            result = query(graph, model, **options)
            result["scope"] = graph["scope"]
            return result

    def check(self):
        """Verify a saved index independently; never repair evidence during a check."""
        enabled = self.cache.is_file()
        saved, errors = None, []
        if enabled:
            try:
                saved = read(self.cache)
                if not isinstance(saved, dict) or not saved:
                    raise ValueError("expected a nonempty code graph object")
            except (OSError, ValueError) as exc:
                errors.append("Invalid saved code structure: " + str(exc))
        fresh, _ = CodeGraph(self.root, persist=False).refresh()
        errors.extend(fresh["errors"])
        if isinstance(saved, dict):
            # Compare content as well as its claimed revision; reject tampering
            # that keeps the old fingerprint while removing a node or relation.
            for key in (
                "schema",
                "nodes",
                "edges",
                "bindings",
                "symbols",
                "files",
                "project",
                "scope",
                "revision",
                "errors",
            ):
                if saved.get(key) != fresh.get(key):
                    errors.append("Saved code structure differs from current source: " + key)
        return {
            "enabled": enabled,
            "valid": not errors,
            "errors": errors,
            "status": "failed" if errors else "passed" if enabled else "not_enabled",
            "revision": fresh["revision"],
            "nodes": len(fresh["nodes"]),
            "edges": len(fresh["edges"]),
        }

    def source(self, path, revision):
        """Only return an indexed project file from the exact requested revision."""
        with self.lock:
            graph, _ = self.refresh()
            if revision != graph["revision"]:
                raise ValueError("Code changed; refresh the code view before opening source")
            if path not in graph["files"]:
                raise ValueError("Source is outside the indexed scope")
            raw = contained(self.root, path).read_bytes()
            if digest(raw) != graph["files"][path]:
                raise ValueError("Source changed while reading")
            return {"source": raw.decode("utf-8-sig"), "code_revision": revision}


def main():
    """Export the full source graph or retrieve a bounded neighborhood as JSON."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scan", "query", "check"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--focus")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--projection", choices=["all", "project", "api"], default="all")
    parser.add_argument("--out")
    args = parser.parse_args()
    service = CodeGraph(args.root, persist=args.command != "check")
    if args.command == "check":
        result = service.check()
        print(json.dumps(result, ensure_ascii=False))
        return int(not result["valid"])
    if args.command == "query":
        result = service.view(
            focus=args.focus, depth=args.depth, limit=args.limit, projection=args.projection
        )
    else:
        result, _ = service.refresh()
    if args.out:
        target = contained(service.root, args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "valid": not result["errors"],
                "revision": result["revision"],
                "nodes": len(result["nodes"]),
                "edges": len(result["edges"]),
                "errors": result["errors"],
                "output": args.out,
            },
            ensure_ascii=False,
        )
    )
    return int(bool(result["errors"]))
