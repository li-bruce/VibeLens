"""One graph document in either an existing v3 model or a common project envelope."""

import json
from pathlib import Path


def read_model(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return model_from_value(value)


def model_from_value(value):
    """Validate a parsed project envelope or return its legacy model payload."""
    if value.get("protocol") == "bo-project/v1":
        from .protocol import validate_project

        return validate_project(value)["model"]
    return value
