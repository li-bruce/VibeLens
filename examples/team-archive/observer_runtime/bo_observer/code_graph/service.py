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
from .observation import qualify
from ..observation.telemetry import load_registrations
from ..source_scope import semantic_inventory


class CodeGraph:
    def __init__(self, root, *, persist=True):
        self.root = Path(root).absolute().resolve()
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
        config = contained(self.root, "sync.json")
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
            telemetry = load_registrations(self.root, model)
            from ..sources import adapter_identity

            adapter = adapter_identity()
            if getattr(self, "inspection_adapter", None) != adapter:
                self.project_inspections.clear()
                self.inspection_adapter = adapter
            inventory = source_inventory(
                self.root,
                cfg,
                inspection_cache=self.project_inspections,
                model=model,
                telemetry=telemetry,
            )
            project = project_inventory(self.root, cfg, inventory)
            # Source inventory reports hidden implementation separately from parser errors.
            fingerprint = digest([semantic_inventory(inventory), semantic_inventory(project)])
            fingerprint = digest([fingerprint, adapter, model, telemetry])
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
                self.graph = qualify(self.graph, model, telemetry)
                self.graph["scope"] = {
                    "files": list(inventory["files"]),
                    "excluded": inventory["excluded"],
                    "project_excluded": project["excluded"],
                    **{
                        key: inventory[key]
                        for key in (
                            "pruned",
                            "owned_overrides",
                            "scope_inputs",
                            "source_roots",
                            "scope_id",
                        )
                    },
                }
                self.fingerprint = fingerprint
                if self.persist:
                    from ..workflow.sync_io import write

                    write(self.cache, self.graph)
            representation_links(model, self.graph)
            # Output directories can appear during a read (for example this
            # service's cache). Report their presence without changing the
            # semantic cache or mutating an earlier returned graph snapshot.
            graph = {
                **self.graph,
                "scope": {**self.graph["scope"], "pruned": inventory["pruned"]},
            }
            return graph, model

    def view(self, **options):
        if options.get("projection") == "project":
            return self.project_view(**options)
        with self.lock:
            graph, model = self.refresh()
            result = query(graph, model, **options)
            result["scope"] = graph["scope"]
            return result

    def api_snapshot(self):
        """Return exact HTTP endpoints for mandatory live/recording context.

        Native capture nodes already belong to the authored model. Only their
        qualified mapping edges are added; file/function expansion stays optional.
        The caller's persist=False policy is respected by the shared refresh.
        """
        with self.lock:
            graph, model = self.refresh()
            endpoints = [
                deepcopy(node) for node in graph["nodes"] if node.get("code_role") == "endpoint"
            ]
            selected = {node["id"] for node in endpoints}
            links = []
            for endpoint in endpoints:
                for source in endpoint.get("observation_sources", []):
                    links.append(
                        {
                            "id": identity(
                                "http-observation",
                                [source["node"], endpoint["id"], source["method"], source["route"]],
                            ),
                            "from": source["node"],
                            "to": endpoint["id"],
                            "type": "data",
                            "code_relation": "maps",
                            "mapping_role": "http-observation",
                            "label": "HTTP observation",
                            "origin": "code-index",
                            "evidence": deepcopy(source),
                        }
                    )
            return {
                "schema": graph["schema"],
                "revision": graph["revision"],
                "nodes": endpoints,
                "edges": links,
                "bindings": {
                    key: deepcopy(value)
                    for key, value in graph["bindings"].items()
                    if key in selected
                },
                "endpoint_aliases": {
                    key: value
                    for key, value in graph.get("endpoint_aliases", {}).items()
                    if value in selected
                },
                "observation_issues": deepcopy(graph.get("observation_issues", [])),
                "errors": deepcopy(graph["errors"]),
                "scope": graph["scope"],
            }

    def api_observation_check(self, *, require_complete=False):
        """Report exact selected HTTP mapping gaps independently of code-cache use."""
        from .observation import http_selector

        snapshot = self.api_snapshot()
        _, model = self.inputs()
        configuration = load_registrations(self.root, model)
        authored = {node["id"]: node for node in model["nodes"]}
        configured = any(
            authored[item["node"]].get("layer") == "api" or http_selector(item["match"]) is not None
            for item in (configuration or {}).get("registrations", [])
        )
        issues = snapshot["observation_issues"]
        observed = [node["id"] for node in snapshot["nodes"] if node.get("observation_projection")]
        unobserved = [
            node["id"] for node in snapshot["nodes"] if not node.get("observation_projection")
        ]
        incomplete_methods = [
            {
                "endpoint": node["id"],
                "methods": sorted(
                    set(node["api"].get("methods", []))
                    - {source["method"] for source in node.get("observation_sources", [])}
                ),
            }
            for node in snapshot["nodes"]
            if set(node["api"].get("methods", []))
            - {source["method"] for source in node.get("observation_sources", [])}
        ]
        missing = (
            sorted(set(unobserved) | {item["endpoint"] for item in incomplete_methods})
            if require_complete
            else []
        )
        errors = deepcopy(snapshot["errors"]) if configured or require_complete else []
        errors.extend({"http_observation_mapping": issue} for issue in issues)
        errors.extend({"unobserved_api_route": identifier} for identifier in missing)
        valid = not errors
        return {
            "configured": configured,
            "valid": valid,
            "status": (
                "failed"
                if not valid
                else (
                    "passed"
                    if configured
                    else "not_configured" if snapshot["nodes"] else "not_applicable"
                )
            ),
            "issues": issues,
            "errors": errors,
            "coverage": (
                "complete"
                if configured
                and not issues
                and not unobserved
                and not incomplete_methods
                and not snapshot["errors"]
                else (
                    "incomplete"
                    if snapshot["nodes"] or configured or snapshot["errors"]
                    else "not_applicable"
                )
            ),
            "strict": require_complete,
            "observed_routes": observed,
            "unobserved_routes": unobserved,
            "incomplete_methods": incomplete_methods,
            "missing_routes": missing,
            "revision": snapshot["revision"],
        }

    def project_view(self, **options):
        """Expose files/containment independently of the optional symbol parser.

        This projection never replaces or seals the full AST cache. A fresh source
        inventory keeps additions, deletions and file links visible after coding.
        """
        with self.lock:
            cfg, model = self.inputs()
            from ..sources import adapter_identity

            adapter = adapter_identity()
            if getattr(self, "inspection_adapter", None) != adapter:
                self.project_inspections.clear()
                self.inspection_adapter = adapter
            inventory = source_inventory(
                self.root, cfg, inspection_cache=self.project_inspections, model=model
            )
            project = project_inventory(self.root, cfg, inventory)
            fingerprint = digest([semantic_inventory(project), inventory["scope_id"], adapter])
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
                    **{
                        key: inventory[key]
                        for key in (
                            "pruned",
                            "owned_overrides",
                            "scope_inputs",
                            "source_roots",
                            "scope_id",
                        )
                    },
                }
                self.project_cache = fingerprint, graph
            cached_graph = self.project_cache[1]
            graph = {
                **cached_graph,
                "scope": {**cached_graph["scope"], "pruned": inventory["pruned"]},
            }
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
        fresh_service = CodeGraph(self.root, persist=False)
        fresh, _ = fresh_service.refresh()
        api_observation = fresh_service.api_observation_check()
        errors.extend(fresh["errors"])
        errors.extend(
            {"api_observation_mapping": issue} for issue in fresh.get("observation_issues", [])
        )
        if isinstance(saved, dict):
            # Compare content as well as its claimed revision; reject tampering
            # that keeps the old fingerprint while removing a node or relation.
            for key in (
                "schema",
                "nodes",
                "edges",
                "bindings",
                "symbols",
                "endpoint_aliases",
                "endpoint_registrations",
                "observation_issues",
                "files",
                "project",
                "scope",
                "revision",
                "errors",
            ):
                actual = semantic_inventory(fresh[key]) if key == "scope" else fresh.get(key)
                expected = (
                    semantic_inventory(saved[key])
                    if key == "scope" and isinstance(saved.get(key), dict)
                    else saved.get(key)
                )
                if expected != actual:
                    errors.append("Saved code structure differs from current source: " + key)
        return {
            "enabled": enabled,
            "valid": not errors,
            "errors": errors,
            "status": "failed" if errors else "passed" if enabled else "not_enabled",
            "revision": fresh["revision"],
            "nodes": len(fresh["nodes"]),
            "edges": len(fresh["edges"]),
            "api_observation": api_observation,
        }

    def documentation(self, *, all_symbols=False):
        """Read current parser facts; do not trust comments cached in graph nodes."""
        from ..graph.source_documentation import report

        with self.lock:
            graph, model = self.refresh()
            result = report(self.previous, model, all_symbols=all_symbols)
            result["revision"] = graph["revision"]
            return result

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
    parser.add_argument("command", choices=["scan", "query", "check", "docs", "api-check"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--focus")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--projection", choices=["all", "project", "api"], default="all")
    parser.add_argument("--out")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail missing source comments or incomplete selected HTTP observation coverage",
    )
    parser.add_argument(
        "--all", action="store_true", help="Check every source symbol and parameter"
    )
    args = parser.parse_args()
    service = CodeGraph(args.root, persist=args.command not in {"check", "api-check"})
    if args.command == "api-check":
        result = service.api_observation_check(require_complete=args.strict)
        if args.out:
            from ..workflow.sync_io import write

            write(contained(service.root, args.out), result)
        print(json.dumps(result, ensure_ascii=False))
        return int(not result["valid"])
    if args.command == "docs":
        result = service.documentation(all_symbols=args.all)
        if args.out:
            from ..workflow.sync_io import write

            write(contained(service.root, args.out), result)
        print(json.dumps(result, ensure_ascii=False))
        return int(bool(result["errors"]) or (args.strict and not result["valid"]))
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
