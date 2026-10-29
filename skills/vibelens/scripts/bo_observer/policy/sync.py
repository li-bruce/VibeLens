"""Refresh policy projections during the existing coding maintenance cycle."""

import json
from pathlib import Path

from .definition import validate
from .projection import project, projection_errors
from .evidence import binding_errors


def synchronize(root, *, model_path="bo_stategraph/project.json", update=True, structure=None):
    """Read canonical rules; never infer new business policy from a changed function."""
    root = Path(root).resolve()
    path = (root / model_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("policy model path escapes project")
    if not path.is_file():
        return {"enabled": False, "valid": True, "changed": False, "errors": []}
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    model = document.get("model", document)
    if not model.get("policy"):
        return {"enabled": False, "valid": True, "changed": False, "errors": []}
    try:
        validate(model["policy"])
        candidate = project(model)
        changed = candidate != model
        errors = binding_errors(model["policy"], structure) if structure is not None else []
        if not update:
            errors += projection_errors(model)
        elif changed and not errors:
            if "model" in document:
                document["model"] = candidate
            else:
                document = candidate
            # Write the one authoritative project document, not a parallel rule file.
            temporary = path.with_suffix(path.suffix + ".policy-tmp")
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            temporary.replace(path)
        return {
            "enabled": True,
            "valid": not errors,
            "changed": changed,
            "errors": errors,
            "revision": model["policy"]["revision"],
            "internal_prompt": "Reconcile changed rule functions with confirmed policy expressions, source parameters, business anchors and whitebox cases. Ask the user only when business meaning is unresolved. Preserve shared IDs and capture actual per-check paths.",
        }
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {"enabled": True, "valid": False, "changed": False, "errors": [str(exc)]}
