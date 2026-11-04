"""Keep generated review artifacts separate from project inputs and evidence."""

import json
from pathlib import Path

from ..graph.behavior_model import contained


def guard_outputs(root, names, *, inputs=(), suffixes=(".json",)):
    """Resolve every output and reject collisions before any caller writes.

    Commands may produce multiple companion files. Configured inputs remain
    protected even when the caller did not pass them as explicit CLI options.
    """
    root = Path(root).resolve()
    config_path = root / "sync.json"
    config = (
        json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.is_file() else {}
    )
    defaults = (
        "sync.json",
        "discovery.json",
        "intent.json",
        "acceptance.json",
        "whitebox.json",
        "mapping.json",
        "reconciliation.json",
        "bo_stategraph/project.json",
    )
    protected = {contained(root, name) for name in defaults}
    protected.update(Path(path).resolve() for path in inputs if path)
    for key in (
        "discovery",
        "model",
        "intent",
        "acceptance",
        "whitebox",
        "mapping_contract",
        "reconciliation",
    ):
        if config.get(key):
            protected.add(contained(root, config[key]))
    for key in ("code_files", "watch_files"):
        protected.update(contained(root, name) for name in config.get(key, []))
    module = config.get("stategraph", {}).get("module")
    if module:
        protected.add(contained(root, module))
    targets = [contained(root, name) for name in names]
    for target in targets:
        if target in protected:
            raise ValueError("Output must not replace a contract input or project source")
        if target.is_relative_to(root / ".stategraph"):
            raise ValueError("Output must not replace workflow evidence")
        if target.suffix.lower() not in suffixes:
            raise ValueError("Output must use " + " or ".join(suffixes))
        # Unregistered source/configuration files are still project inputs.
        # Repeated generation belongs in the documented review directories;
        # a caller cannot turn an existing file elsewhere into an artifact.
        if target.exists() and not any(
            target.is_relative_to(root / folder) for folder in ("review", ".validation")
        ):
            raise ValueError(
                "Existing output must be a review artifact under review/ or .validation/"
            )
    if len(set(targets)) != len(targets):
        raise ValueError("Companion outputs must have distinct paths")
    return targets
