"""One graph document in either an existing v3 model or a common project envelope."""

from pathlib import Path


def read_model(path, *, project_root=None):
    """Read legacy data or resolve the pinned v2 artifact set within its project."""
    from .project_artifacts import load_project, parse, PROJECT_VERSIONS

    path = Path(path).resolve()
    value = parse(path.read_bytes())
    if value.get("protocol") in PROJECT_VERSIONS and (
        value["protocol"] == "bo-project/v2" or project_root or path.parent.name == "bo_stategraph"
    ):
        if project_root is None and path.parent.name != "bo_stategraph":
            raise ValueError("A nonstandard project envelope path requires project_root")
        root = Path(project_root).resolve() if project_root else path.parent.parent
        return load_project(root, path.relative_to(root).as_posix())["model"]
    return model_from_value(value)


def model_from_value(value):
    """Check an in-memory envelope; external artifacts require read_model/load_project."""
    if value.get("protocol") in {"bo-project/v1", "bo-project/v2"}:
        from .protocol import validate_project

        return validate_project(value)["model"]
    if str(value.get("protocol", "")).startswith("bo-project/"):
        raise ValueError("Unsupported project protocol")
    return value
