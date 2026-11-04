"""Declare first-party analysis boundaries without changing watched-file integrity.

Roots discover authored and generated application source. Classified installed
dependencies and outputs are pruned before traversal; ordinary exclusions remain
subject to the existing implementation/entrypoint inspection.
"""

from pathlib import Path, PurePosixPath, PureWindowsPath
import hashlib
import json
import os
import stat

from .graph.source_files import SourceFiles


DEPENDENCY_NAMES = {
    "node_modules",
    "site-packages",
    "__pypackages__",
    ".venv",
    "venv",
    ".tox",
    ".nox",
    ".agents",
    ".codex",
    ".npm",
    ".yarn",
    ".pnpm-store",
}
ARTIFACT_NAMES = {
    ".git",
    "__pycache__",
    ".stategraph",
    ".validation",
    ".planning",
    ".release",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".tmp",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "htmlcov",
}
IGNORED = DEPENDENCY_NAMES | ARTIFACT_NAMES
DEFAULT_PRUNES = (
    {
        "path": "bo_stategraph/config",
        "category": "artifact",
        "reason": "Observer preferences and display configuration",
    },
    {
        "path": "bo_stategraph/data",
        "category": "artifact",
        "reason": "Observer recordings and generated runtime data",
    },
    {
        "path": "review/runtime",
        "category": "artifact",
        "reason": "Generated runtime review records",
    },
)


def relative_name(value, *, root=False):
    """Require a literal normalized project-relative path, never a glob or escape."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("source scope needs a nonempty literal path")
    name = value.replace("\\", "/")
    path = PurePosixPath(name)
    if (
        "\x00" in name
        or any(char in name for char in "*?[]{}")
        or path.is_absolute()
        or PureWindowsPath(name).drive
        or ".." in path.parts
        or path.as_posix() != name
        or (name == "." and not root)
    ):
        raise ValueError("source scope path must be normalized, relative and literal: " + value)
    return name


def within(name, prefix):
    return prefix == "." or name == prefix or name.startswith(prefix + "/")


class ScopePolicy:
    """One ownership policy shared by scanners, source bindings and the file tree."""

    def __init__(self, root, cfg):
        self.root = Path(root).absolute().resolve()
        scope = cfg.get("source_scope", {})
        if not isinstance(scope, dict):
            raise ValueError("source scope must be an object")
        allowed = {"roots", "exclude", "frozen_sources", "require_symbol_classification", "prune"}
        if set(scope) - allowed:
            raise ValueError(
                "source scope has unknown fields: " + ", ".join(sorted(set(scope) - allowed))
            )
        exclusions = scope.get("exclude", {})
        if not isinstance(exclusions, dict) or any(
            not isinstance(reason, str) or not reason.strip() for reason in exclusions.values()
        ):
            raise ValueError("source scope exclusions need nonempty reasons")
        frozen = scope.get("frozen_sources", {})
        if not isinstance(frozen, dict):
            raise ValueError("source scope frozen_sources must map literal paths")
        for directory, manifest in frozen.items():
            relative_name(directory)
            relative_name(manifest)
        roots = scope.get("roots", ["."])
        if not isinstance(roots, list) or not roots:
            raise ValueError("source scope needs nonempty roots")
        self.roots = list(dict.fromkeys(relative_name(name, root=True) for name in roots))
        rows = scope.get("prune", [])
        if not isinstance(rows, list):
            raise ValueError("source scope prune must be a list")
        self.rules = list(DEFAULT_PRUNES)
        declared = set()
        for item in rows:
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "category", "reason"}
                or item.get("category") not in {"dependency", "artifact"}
                or not isinstance(item.get("reason"), str)
                or not item["reason"].strip()
            ):
                raise ValueError(
                    "source scope prune needs path, dependency/artifact category and reason"
                )
            name = relative_name(item["path"])
            if name in declared:
                raise ValueError("source scope has duplicate prune path: " + name)
            declared.add(name)
            self.rules = [rule for rule in self.rules if rule["path"] != name]
            self.rules.append(
                {"path": name, "category": item["category"], "reason": item["reason"]}
            )
        self.pruned = {}
        self.overrides = []
        for name in self.roots:
            target = self.root / name
            if not target.exists():
                raise ValueError("source scope is missing: " + name)
            # Explicit source roots cannot turn a link into an ownership override.
            for part in [target, *target.parents]:
                if not part.is_relative_to(self.root):
                    break
                info = part.lstat()
                if SourceFiles.linked(info):
                    raise ValueError("source scope root contains a symlink or junction: " + name)
                if part == self.root:
                    break
            if name != ".":
                rule = self.classification(name, overrides=False)
                if rule:
                    self.overrides.append(
                        {"path": name, "category": "first_party", "overrides": rule["path"]}
                    )
        raw = SourceFiles(self.root).read(".gitignore")
        self.scope_inputs = {
            ".gitignore": hashlib.sha256(raw).hexdigest() if raw is not None else None
        }
        self.definition = {
            "roots": self.roots,
            "prune": self.rules,
            "defaults": sorted(IGNORED),
            "exclude": exclusions,
            "frozen_sources": frozen,
        }
        self.scope_id = hashlib.sha256(
            json.dumps([self.definition, self.scope_inputs], sort_keys=True).encode()
        ).hexdigest()

    def classification(self, name, *, overrides=True):
        """Return the applicable prune boundary, allowing explicit nested source roots."""
        name = relative_name(name, root=True)
        candidates = [rule for rule in self.rules if within(name, rule["path"])]
        parts = PurePosixPath(name).parts
        for index, part in enumerate(parts):
            if part in IGNORED:
                category = "dependency" if part in DEPENDENCY_NAMES else "artifact"
                candidates.append(
                    {
                        "path": "/".join(parts[: index + 1]),
                        "category": category,
                        "reason": (
                            "Installed dependency/cache"
                            if category == "dependency"
                            else "Generated output or repository metadata"
                        ),
                    }
                )
        if overrides:
            owners = [root for root in self.roots if root != "." and within(name, root)]
            candidates = [
                rule
                for rule in candidates
                if not any(within(owner, rule["path"]) for owner in owners)
            ]
        return max(
            candidates, key=lambda item: len(PurePosixPath(item["path"]).parts), default=None
        )

    def is_pruned(self, name):
        return self.classification(name) is not None

    def record_prune(self, name):
        rule = self.classification(name)
        if rule:
            self.pruned[rule["path"]] = dict(rule)
        return rule

    def assert_source(self, name, context="source"):
        """Reject an executable binding outside ownership before any AST is read."""
        name = relative_name(name)
        if not any(within(name, prefix) for prefix in self.roots):
            raise ValueError("source scope excludes executable " + context + ": " + name)
        rule = self.classification(name)
        if rule:
            raise ValueError(
                "source scope pruned executable "
                + context
                + ": "
                + name
                + " ("
                + rule["category"]
                + ")"
            )
        return name

    def walk_sources(self, start, supported):
        """Walk every owned subtree, pruning only declared/default storage boundaries."""
        start = Path(start)
        name = start.relative_to(self.root).as_posix()
        if self.record_prune(name):
            return
        if start.is_file():
            yield start
            return
        # Retain fresh lstat checks and os.walk's existing link handling. Ownership
        # pruning supplies the performance gain; this does not relax path safety.
        for parent, directories, files in os.walk(start, followlinks=False):
            kept = []
            for child in directories:
                path = Path(parent) / child
                if self.record_prune(path.relative_to(self.root).as_posix()):
                    continue
                try:
                    info = path.lstat()
                except OSError:
                    continue
                junction = getattr(info, "st_reparse_tag", 0) == getattr(
                    stat, "IO_REPARSE_TAG_MOUNT_POINT", -1
                )
                if not stat.S_ISLNK(info.st_mode) and not junction:
                    kept.append(child)
            directories[:] = kept
            for child in files:
                path = Path(parent) / child
                if (
                    supported(child)
                    and not self.record_prune(path.relative_to(self.root).as_posix())
                    and path.is_file()
                ):
                    yield path

    def report(self):
        return {
            "pruned": [self.pruned[key] for key in sorted(self.pruned)],
            "owned_overrides": self.overrides,
            "scope_inputs": self.scope_inputs,
            "scope_id": self.scope_id,
            "source_roots": self.roots,
        }


def compile_scope(root, cfg=None):
    """Compile supplied configuration, or the project's normal sync.json policy."""
    if cfg is None:
        path = Path(root) / "sync.json"
        raw = SourceFiles(root).read("sync.json")
        if raw is None and path.exists():
            raise ValueError("source scope configuration is not a readable file")
        cfg = json.loads(raw.decode("utf-8-sig")) if raw is not None else {}
    return ScopePolicy(root, cfg)


def validate_executable_sources(policy, cfg=None, model=None, telemetry=None):
    """Check actual executable anchors; hash-only watched/config inputs stay valid."""

    def source(value, context):
        if isinstance(value, str):
            policy.assert_source(value.split("::", 1)[0], context)
        elif isinstance(value, dict) and value.get("path"):
            policy.assert_source(value["path"], context)

    for name in (cfg or {}).get("code_files", []):
        source(name, "code_files")
    for node in (model or {}).get("nodes", []):
        source(node.get("source"), "node " + str(node.get("id")))
        source(node.get("represents"), "parameter representation")
    for feature in (model or {}).get("implementation", {}).get("features", []):
        for value in feature.get("sources", []):
            source(value, "feature")
        for parameter in feature.get("parameters", []):
            source(parameter.get("source"), "feature parameter")
    for reference in (model or {}).get("implementation", {}).get("support", {}):
        source(reference, "implementation support")
    for check in (model or {}).get("policy", {}).get("predicates", []):
        source(check.get("source"), "policy check")
    for registration in (telemetry or {}).get("registrations", []):
        source(registration.get("source"), "telemetry registration")


def semantic_inventory(inventory):
    """Encountered output prefixes are diagnostics, not changes to owned source."""
    return {key: value for key, value in inventory.items() if key != "pruned"}
