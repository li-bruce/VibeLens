"""Pin confirmed conceptual context to one observed build and its recordings.

Only projects with a bound concept contract use this reader. The collector never
loads an editable draft as an executable machine. The original declarations and
application remain authoritative when the viewer is closed or unavailable.
"""

from __future__ import annotations

import json
from copy import deepcopy

from ..graph.behavior_model import contained, digest
from ..graph.source_files import SourceFiles


class ConceptContext:
    """Validate once, then detect input drift from actual bytes at admission boundaries."""

    def __init__(self, root, model):
        self.root = root
        self.projection = None
        self.inputs = {}
        self.configuration = None
        self.sources = SourceFiles(root)
        if not model.get("concepts"):
            return

        from ..concepts import assess, bind_projection

        config_path = contained(root, "sync.json")
        config = (
            json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.is_file() else {}
        )
        discovery_path = config.get("discovery", "discovery.json")
        acceptance_path = config.get("acceptance", "acceptance.json")
        self.configuration = (discovery_path, acceptance_path)
        documents = []
        for name in (discovery_path, acceptance_path):
            raw = self.sources.read(contained(root, name).relative_to(root))
            if raw is None:
                raise ValueError("Bound concepts require their contract input: " + name)
            self.inputs[name] = digest(raw)
            documents.append(json.loads(raw.decode("utf-8-sig")))
        document, acceptance = documents
        report = assess(document, model=model, acceptance=acceptance)
        if not report["ready"]:
            raise ValueError(
                "Invalid bound concepts: "
                + json.dumps({"errors": report["errors"], "blocked": report["blocked"]})
            )
        self.projection = bind_projection(document, model, acceptance=acceptance)

    def changed_inputs(self):
        """Keep source-byte freshness separate from historical confirmation status."""
        changed = []
        if self.configuration is not None:
            # A changed contract location must not leave a running session reading
            # an abandoned file. Unrelated test/command settings may still change.
            try:
                # SourceFiles rechecks current ancestors, links and bytes. Reusing
                # this secure reader avoids resolving the entire Windows project
                # path for every event; it does not cache contract content.
                raw = self.sources.read("sync.json")
                if raw is None and (self.root / "sync.json").is_file():
                    raise ValueError("Cannot read the current concept configuration")
                config = json.loads(raw.decode("utf-8-sig")) if raw is not None else {}
                current = (
                    config.get("discovery", "discovery.json"),
                    config.get("acceptance", "acceptance.json"),
                )
                if current != self.configuration:
                    changed.append("sync.json")
            except (OSError, ValueError, TypeError, AttributeError):
                changed.append("sync.json")
        for name, expected in self.inputs.items():
            try:
                # Keep the logical configured name. A later ancestor replacement
                # must be checked again rather than following an old resolved alias.
                raw = self.sources.read(name)
                if digest(raw) != expected:
                    changed.append(name)
            except (OSError, ValueError):
                changed.append(name)
        return changed

    def view(self):
        """Detach static metadata so callers cannot mutate a build's confirmed graph."""
        return deepcopy(self.projection)
