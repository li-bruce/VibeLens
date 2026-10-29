"""Read direct package dependencies without installing or loading packages."""

import json
from pathlib import PurePosixPath
import re
import tomllib


def local_manifest(path, ecosystem, name, version, names, entries):
    """Resolve explicit local declarations, not a coincidentally matching name."""
    if ecosystem != "npm":
        return None
    if version.startswith("workspace:"):
        candidates = names.get((ecosystem, name), [])
        return candidates[0] if len(candidates) == 1 else None
    if version.startswith(("file:", "link:")):
        parts = list(PurePosixPath(path).parent.parts)
        for part in PurePosixPath(version.split(":", 1)[1]).parts:
            if part == "..":
                if not parts:
                    return None
                parts.pop()
            elif part not in {".", ""}:
                parts.append(part)
        target = "/".join([*parts, "package.json"])
        return target if entries.get(target, {}).get("kind") == "file" else None
    return None


def dependencies(root, project, nodes, edge, identity):
    """Link manifests to exact local package names or external boundaries."""
    documents, names, errors = {}, {}, []
    for path in sorted(project["text_files"]):
        name = PurePosixPath(path).name
        if name not in {"package.json", "pyproject.toml"}:
            continue
        try:
            text = (root / path).read_text(encoding="utf-8-sig")
            document = json.loads(text) if name == "package.json" else tomllib.loads(text)
            if not isinstance(document, dict):
                raise ValueError("Package manifest must be an object")
            ecosystem = "npm" if name == "package.json" else "python"
            declaration = document if ecosystem == "npm" else document.get("project", {})
            if not isinstance(declaration, dict):
                raise ValueError("Project declaration must be an object")
            package = declaration.get("name")
            if isinstance(package, str):
                names.setdefault((ecosystem, package), []).append(path)
            documents[path] = (ecosystem, declaration)
        except (OSError, ValueError, TypeError) as exc:
            errors.append({"path": path, "error": "Cannot read package declarations: " + str(exc)})
    for path, (ecosystem, document) in documents.items():
        try:
            if ecosystem == "npm":
                sections = (
                    "dependencies",
                    "devDependencies",
                    "peerDependencies",
                    "optionalDependencies",
                )
                if any(not isinstance(document.get(section, {}), dict) for section in sections):
                    raise ValueError("Dependency sections must be objects")
                declared = [
                    (section, name, version)
                    for section in sections
                    for name, version in (document.get(section, {}) or {}).items()
                ]
            else:
                declared = []
                values = document.get("dependencies", [])
                if not isinstance(values, list) or any(
                    not isinstance(value, str) for value in values
                ):
                    raise ValueError("Python dependencies must be strings in an array")
                for value in values:
                    match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
                    if match:
                        declared.append(("dependencies", match[0], value))
                    else:
                        raise ValueError("Cannot extract dependency name: " + value)
            if any(
                not isinstance(version, str) or not version.strip() for _, _, version in declared
            ):
                raise ValueError("Dependency versions must be nonempty strings")
        except (AttributeError, TypeError, ValueError) as exc:
            errors.append({"path": path, "error": "Invalid package dependencies: " + str(exc)})
            continue
        for section, name, version in declared:
            local = local_manifest(path, ecosystem, name, version, names, project["entries"])
            if local:
                target = identity("file", local)
            else:
                target = identity("package", [path, ecosystem, name])
                nodes[target] = {
                    "id": target,
                    "label": name,
                    "code_role": "unresolved",
                    "kind": "data",
                    "layer": "project",
                    "origin": "code-index",
                    "reference_scope": "project",
                    "parent": identity("file", path),
                    "package_name": name,
                    "summary": str(version),
                }
            edge(
                identity("file", path),
                target,
                "dependency",
                "Package dependency",
                {"path": path, "field": section + "." + name, "declaration": str(version)},
            )
    return errors
