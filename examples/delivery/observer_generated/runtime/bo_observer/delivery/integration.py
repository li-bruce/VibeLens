"""Install only native adapters; keep analysis, controls and Web in the Skill.

The receipt records dependency bytes, not application declarations. Checks run
from the installed Skill and compare against its own sources, so editing a local
hash alongside a copied adapter cannot turn that edit into a trusted framework.
"""

from pathlib import Path
import argparse
import hashlib
import json
import os

from ..graph.behavior_model import contained, read
from ..workflow.sync_io import write

SCRIPTS = Path(__file__).resolve().parents[2]
RECEIPT = "bo_stategraph/integration.json"
PROTOCOLS = {
    "project": "bo-project/v1",
    "event": "bo-event/v1",
    "snapshot": "bo-snapshot/v1",
    "snapshot_registry": "bo-snapshot/v2",
    "capture": "bo-capture-control/v1",
}


def canonical_scripts():
    """Resolve an independent installed provider when called through a legacy copy.

    A project's runtime folder is not the canonical package. Existing launcher
    setup already supplies BO_ADAPTER_HOME; other hosts can name VIBELENS_SKILL.
    Never fall back to trusting a locally edited receipt as canonical evidence.
    """
    candidates = [SCRIPTS]
    if os.environ.get("VIBELENS_SKILL"):
        candidates.append(Path(os.environ["VIBELENS_SKILL"]) / "scripts")
    if os.environ.get("BO_ADAPTER_HOME"):
        adapter = Path(os.environ["BO_ADAPTER_HOME"]).resolve()
        if len(adapter.parents) >= 3:
            candidates.append(adapter.parents[2])
    for candidate in candidates:
        if (candidate.parent / "SKILL.md").is_file() and (candidate / "bo_contracts.py").is_file():
            return candidate.resolve()
    raise ValueError("Run checks from the installed Skill, or set VIBELENS_SKILL to its directory")


def native_sources(language):
    """The minimum supported native dependencies, without a service or viewer copy."""
    if language == "python":
        return {
            "bo_stategraph/__init__.py": "bo_stategraph.py",
            "bo_stategraph/bo_contracts.py": "bo_contracts.py",
            "bo_stategraph/bo_models.py": "bo_models.py",
            "bo_stategraph/execution_contract.py": "execution_contract.py",
            "bo_stategraph/bo_probe.py": "bo_observer/adapters/python/bo_probe.py",
            "bo_stategraph/bo_executor.py": "bo_observer/adapters/python/bo_executor.py",
            "bo_stategraph/bo_capture.py": "bo_observer/adapters/python/bo_capture.py",
        }
    if language == "javascript":
        return {
            "bo_stategraph/bo_runtime.mjs": "bo_observer/adapters/javascript/bo_runtime.mjs",
            "bo_stategraph/bo_capture.mjs": "bo_observer/adapters/javascript/bo_capture.mjs",
        }
    raise ValueError("language must be python or javascript (including React/Vue)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(root, language):
    """Refuse unknown local edits before writing any native dependency."""
    root = Path(root).resolve()
    receipt = contained(root, RECEIPT)
    previous = read(receipt) if receipt.exists() else {}
    if previous and (
        previous.get("schema") != "vibelens-integration/v1" or previous.get("language") != language
    ):
        raise ValueError("integration language/schema differs; migrate explicitly")
    sources = native_sources(language)
    canonical = canonical_scripts()
    previous_files = set(previous.get("files", {}))
    additions = set(sources) - previous_files
    if previous and (previous_files - set(sources) or additions - {"bo_stategraph/bo_models.py"}):
        raise ValueError("integration dependency set differs; retain and review the old receipt")
    files, changes, conflicts = {}, [], []
    for name, source in sources.items():
        expected = sha(canonical / source)
        target = contained(root, name)
        current = sha(target) if target.exists() else None
        files[name] = expected
        if current != expected:
            if current is not None and current != previous.get("files", {}).get(name):
                conflicts.append(name)
            else:
                changes.append(name)
    return {
        "valid": not conflicts,
        "schema": "vibelens-integration/v1",
        "language": language,
        "protocols": PROTOCOLS,
        "sources": sources,
        "files": files,
        "changes": changes,
        "conflicts": conflicts,
    }


def install(root, language):
    """Write reviewed dependency bytes only; application declarations stay untouched."""
    from bo_upgrade import replace_copy

    root = Path(root).resolve()
    result = plan(root, language)
    canonical = canonical_scripts()
    if not result["valid"]:
        raise ValueError(
            "native dependency edits require review: " + ", ".join(result["conflicts"])
        )
    originals = {}
    try:
        for name in result["changes"]:
            target = contained(root, name)
            originals[name] = target.read_bytes() if target.exists() else None
            target.parent.mkdir(parents=True, exist_ok=True)
            replace_copy(canonical / result["sources"][name], target)
        write(
            contained(root, RECEIPT),
            {key: result[key] for key in ("schema", "language", "protocols", "sources", "files")},
        )
    except Exception:
        for name, original in originals.items():
            target = contained(root, name)
            if original is None:
                target.unlink(missing_ok=True)
            else:
                replace_copy(original, target)
        raise
    return result


def inspect(root):
    """Check all managed dependencies, even when excluded from business scanning.

    Legacy full-copy installations retain their existing layout. Their receipt is
    checked as a whole, with native and observer modules compared to canonical
    bytes independently of that receipt. Installation is never auto-repaired.
    """
    root = Path(root).resolve()
    errors, checked = [], {}
    verified = []
    path = contained(root, RECEIPT)
    native = read(path) if path.exists() else None
    legacy_path = contained(root, "bo_stategraph/runtime-version.json")
    canonical = canonical_scripts() if native is not None or legacy_path.exists() else None
    if native is not None:
        if not isinstance(native, dict):
            raise ValueError("integration receipt must be an object")
        expected = native_sources(native.get("language"))
        if (
            native.get("schema") != "vibelens-integration/v1"
            or native.get("sources") != expected
            or native.get("protocols") != PROTOCOLS
            or set(native.get("files", {})) != set(expected)
        ):
            errors.append({"framework_receipt": RECEIPT, "reason": "invalid dependency contract"})
        for name, source in expected.items():
            target = contained(root, name)
            actual = sha(target) if target.is_file() else None
            checked[name] = actual
            if actual != native.get("files", {}).get(name) or actual != sha(canonical / source):
                errors.append(
                    {"framework_dependency": name, "reason": "missing, edited or outdated"}
                )
            else:
                verified.append(name)
    if legacy_path.exists():
        legacy = read(legacy_path)
        if legacy.get("schema") != 1 or not isinstance(legacy.get("files"), dict):
            errors.append(
                {"framework_receipt": str(legacy_path), "reason": "invalid managed manifest"}
            )
        else:
            sources = legacy.get("source_files")
            if sources is not None and set(sources) != set(legacy["files"]):
                errors.append(
                    {"framework_receipt": str(legacy_path), "reason": "source map differs"}
                )
            for name, expected in legacy["files"].items():
                target = contained(root, name)
                actual = sha(target) if target.is_file() else None
                checked[name] = actual
                if actual != expected:
                    errors.append({"framework_dependency": name, "reason": "managed bytes changed"})
                if sources is not None:
                    source = sources.get(name, "")
                    if source.startswith("bridge:"):
                        from bo_upgrade import CORE, bridge_source

                        member = source.removeprefix("bridge:")
                        module = legacy.get("module", "bo_stategraph")
                        if member not in CORE or not module.isidentifier():
                            raise ValueError("invalid managed bridge")
                        expected_source = hashlib.sha256(bridge_source(member, module)).hexdigest()
                    else:
                        if not source.startswith(("scripts/", "assets/stategraph-viewer/")):
                            raise ValueError("invalid managed framework source")
                        expected_source = sha(contained(canonical.parent, source))
                    if expected != expected_source:
                        errors.append(
                            {
                                "framework_dependency": name,
                                "reason": "canonical source differs; upgrade required",
                            }
                        )
                    elif actual == expected:
                        verified.append(name)
    return {
        "valid": not errors,
        "mode": (
            "external"
            if native is not None
            else "managed-copy" if legacy_path.exists() else "unmanaged"
        ),
        "errors": errors,
        "files": checked,
        "verified_files": sorted(verified),
        "receipt": sha(path) if path.is_file() else None,
        "managed_receipt": sha(legacy_path) if legacy_path.is_file() else None,
        "owner": "installed-skill",
        "controls": ["inspect", "view", "replay", "status", "end"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "apply", "check"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--language", choices=["python", "javascript"])
    args = parser.parse_args(argv)
    try:
        if args.command != "check" and not args.language:
            raise ValueError("plan/apply requires --language")
        function = {"plan": plan, "apply": install, "check": inspect}[args.command]
        result = (
            function(args.root, args.language) if args.command != "check" else function(args.root)
        )
    except (ValueError, OSError, TypeError, KeyError) as error:
        result = {"valid": False, "errors": [str(error)]}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["valid"] else 1
