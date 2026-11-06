"""Hide observer-owned support in code views, without changing coverage policy.

The iteration inventory still scans and validates its declared scope. This module
only selects which of those files represent the user's application in the graph.
Application state executors remain application code, including in drive mode.
"""

from copy import deepcopy
from pathlib import PurePosixPath

from ..graph.behavior_model import read


def application_inventory(root, config, inventory):
    """Return a display inventory and exact exclusions for the project tree.

    Ownership declarations are preferable to a filename prefix: a business module
    called observer.py, for example, is not automatically observer infrastructure.
    """
    excluded = {}

    def exclude(path):
        if isinstance(path, str) and path and not PurePosixPath(path).is_absolute():
            excluded[path.replace("\\", "/").rstrip("/")] = "Observer support (display only)"

    for key in ("model", "manifest", "discovery", "intent", "acceptance", "mapping_contract"):
        exclude(config.get(key))
    if (root / "sync.json").is_file():
        exclude("sync.json")
    # Reserved config/data directories are already handled by source_scope,
    # including narrow, explicit application-owned overrides within them.
    # Exclude only installed metadata here; never override that ownership choice.
    for name in (
        "project.json",
        "manifest.json",
        "telemetry.json",
        "database-catalog.json",
        "databases.json",
        "runtime-version.json",
    ):
        exclude("bo_stategraph/" + name)
    ownership_path = root / "ownership.json"
    if ownership_path.is_file():
        ownership = read(ownership_path)
        exclude("ownership.json")
        for path in ownership.get("layers", {}).get("observer", {}).get("paths", []):
            exclude(path)
        # Statechart adapters in the stategraph layer are deliberately retained.
        for path in ownership.get("managed_paths", []):
            if not str(path).startswith("bo_stategraph/"):
                exclude(path)
    stategraph = config.get("stategraph", {})
    if stategraph.get("execution_mode") == "observe":
        exclude(stategraph.get("module"))
    # Generated integration bindings have a reserved filename in the scaffold.
    # Exclude only when its independent observation contract registers this file.
    integration = root / "bo_integration.py"
    if integration.is_file() and "bo_integration.py" in config.get("code_files", []):
        text = integration.read_text(encoding="utf-8-sig")
        if "BOIntegration" in text and "bo_observer" in text:
            exclude("bo_integration.py")

    def hidden(name):
        return any(name == path or name.startswith(path + "/") for path in excluded)

    selected = {
        **inventory,
        "files": {k: v for k, v in inventory["files"].items() if not hidden(k)},
    }
    display_config = deepcopy(config)
    scope = display_config.setdefault("source_scope", {})
    scope["exclude"] = {**scope.get("exclude", {}), **excluded}
    return selected, display_config, excluded


def prune_support_shells(project, exclusions):
    """Remove empty ancestors left solely by hidden support/configuration files.

    A deliberately empty application directory stays visible unless an exclusion
    beneath it explains the absence of its contents.
    """
    entries = dict(project["entries"])
    omitted = (
        set(exclusions)
        | set(project["excluded"])
        | {entry["path"] for entry in project.get("pruned", [])}
    )
    for name in sorted(entries, key=len, reverse=True):
        if name == "." or entries[name]["kind"] != "directory":
            continue
        prefix = name + "/"
        if any(child.startswith(prefix) for child in entries):
            continue
        if any(child == name or child.startswith(prefix) for child in omitted):
            del entries[name]
            omitted.add(name)
    return {**project, "entries": entries}
