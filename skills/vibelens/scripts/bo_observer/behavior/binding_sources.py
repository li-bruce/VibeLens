"""Resolve native readers and capture sites through an independent source index.

No application module is imported here. A declaration, an observation field and
an independent native reader keep different responsibilities and identities.
"""

from dataclasses import dataclass

from ..project_artifacts import portable_path
from .diagnostics import require
from ..value_types import represents  # Public compatibility import for existing adapters.


@dataclass(frozen=True)
class SourceBinding:
    path: str
    symbol: str

    @property
    def identity(self):
        return self.path + "::" + self.symbol


class BindingSources:
    """Validate only supplied owned-source inventory, never traverse dependencies."""

    def __init__(self, model, index):
        self.nodes = {node["id"]: node for node in model.get("nodes", [])}
        self.index = index
        self.excluded = (model.get("implementation") or {}).get("excluded", {})
        self.sources = set()

    def source(self, reference, path):
        native = SourceBinding(portable_path(reference["path"]), reference["symbol"])
        require(
            self.excluded.get(native.identity, {}).get("category") != "observer",
            "observer_binding",
            path,
            native.identity,
        )
        if self.index is not None:
            symbol = self.index.get("symbols", {}).get(native.identity)
            require(symbol is not None, "binding_source_missing", path, native.identity)
            require(
                symbol.get("kind") == "function",
                "binding_source_kind",
                path,
                "Bind a callable declaration, not a file label",
            )
            require(
                symbol.get("documentation", {}).get("status") == "documented",
                "binding_documentation_missing",
                path,
                native.identity,
            )
        self.sources.add(native.identity)
        return native

    def site(self, site, path):
        node = self.nodes.get(site["node"])
        require(node is not None, "binding_node_missing", path, site["node"])
        require(
            isinstance(node.get("source"), dict),
            "binding_source_missing",
            path,
            "A native boundary needs an actual source declaration",
        )
        self.source(node["source"], path + "/source")
        for condition in site.get("when", []):
            route = condition["path"]
            if route[0] in {"inputs", "outputs", "exception"}:
                self.capture(node, route, site["phase"], path + "/when")
            else:
                require(
                    route
                    in [
                        [key]
                        for key in (
                            "entity",
                            "attempt",
                            "build_id",
                            "project_id",
                            "model_revision",
                            "call_id",
                            "parent_call_id",
                        )
                    ],
                    "binding_selector_path",
                    path,
                    "Select a declared capture or scalar event identity",
                )
        return node

    def field(self, site, path):
        """Resolve exactly the selected capture path, including nested fields."""
        node = self.site(site, path)
        return self.capture(node, site["path"], site["phase"], path)

    @staticmethod
    def capture(node, route, phase, path):
        """Resolve a capture spec without recursively validating site selectors."""
        if route == ["exception", "type"] and phase == "error":
            return "string"  # Existing redacted exception protocol; no message or payload.
        require(
            len(route) >= 2 and route[0] in {"inputs", "outputs"},
            "binding_capture_path",
            path,
            "Select an input or output capture field",
        )
        value = node.get("capture", {}).get("in" if route[0] == "inputs" else "out", {})
        for part in route[1:]:
            if isinstance(value, dict) and isinstance(part, str) and part in value:
                value = value[part]
            elif isinstance(value, list) and len(value) == 1 and type(part) is int:
                value = value[0]
            else:
                require(False, "binding_capture_missing", path, str(route))
        return value
