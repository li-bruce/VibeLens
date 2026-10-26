"""Create a disposable, source-bound v1 or v2 case project.

v1 deliberately omits the version guard. It is a teaching defect, not a report
about an independently discovered bug. v2 is the maintained application policy.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SKILL = REPO / "skills/vibelens"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prepare(root, version):
    """Generate only in an empty destination; existing projects are never overwritten."""
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("Choose an empty destination for this case")
    for name in ["domain.py", "repository.py", "policy.py", "app.py", "bo_integration.py"]:
        shutil.copyfile(HERE / name, root / name)
    shutil.copytree(HERE / "web", root / "web")
    shutil.copytree(HERE / "review", root / "review")
    if version == 1:
        (root / "policy.py").write_text(
            '"""Authorization for publishing an image."""\n\n'
            "def approval_policy(actor, current_version, reviewed_version):\n"
            '    """Decide whether the opened image can be published."""\n'
            '    return "allowed" if actor == "reviewer" else "forbidden"\n',
            encoding="utf-8",
        )
    sys.path.insert(0, str(SKILL / "scripts"))
    from bo_observer.data.sync import synchronize

    source_files = ["domain.py", "repository.py", "policy.py", "app.py", "web/app.js"]
    nodes, edges = [], []

    def node(
        ident, label, kind, path=None, symbol=None, parent=None, inputs=None, outputs=None, **extra
    ):
        value = {
            "id": ident,
            "label": label,
            "kind": kind,
            "requirements": ["R1"],
            "summary": (
                f"{label}: {symbol} in {path}" if path else f"Artwork state: {label.lower()}"
            ),
            "layer": "business" if kind == "action" else "state" if kind == "state" else "logic",
        }
        if path:
            value["source"] = {"path": path, "symbol": symbol}
            value["capture"] = {"in": inputs or {}, "out": outputs or {}}
        if parent:
            value["parent"] = parent
        nodes.append({**value, **extra})

    def edge(a, b, kind, label):
        edges.append(
            {
                "id": a + ":" + b + ":" + kind,
                "from": a,
                "to": b,
                "type": "flow" if kind == "call" else kind,
                "label": label,
                **(
                    {"code_relation": "handles" if a.startswith("api.") else "calls"}
                    if kind == "call"
                    else {}
                ),
                "evidence": "Authored mapping to the bound request handlers, domain calls and state declaration",
            }
        )

    result = {
        "status": "string",
        "image_version": "number",
        "reviewed_version": "number",
        "published_version": "number",
    }
    for ident, label, symbol, inputs in [
        ("upload", "Upload / replace", "upload", {"actor": "string"}),
        ("review", "Open review", "preview", {"actor": "string"}),
        (
            "publish",
            "Approve opened image",
            "approve",
            {"actor": "string", "reviewed_version": "number"},
        ),
        ("exhibit", "View exhibition & messages", "public", {}),
    ]:
        node(
            ident,
            label,
            "action",
            "repository.py" if ident == "exhibit" else "domain.py",
            "Repository.public" if ident == "exhibit" else "Gallery." + symbol,
            inputs=inputs,
            outputs=result,
            semantic_roles=["permission"] if ident == "publish" else [],
        )
        node(
            "api." + ident,
            "POST /app/" + symbol,
            "function",
            "app.py",
            symbol,
            code_role="endpoint",
            parent=ident,
            inputs=inputs,
            outputs=result,
        )
        edge("api." + ident, ident, "call", "Handles request")
        ui_symbol = {
            "upload": "uploadImage",
            "review": "openReview",
            "publish": "approveReview",
            "exhibit": "refreshExhibition",
        }[ident]
        node("ui." + ident, ui_symbol, "function", "web/app.js", ui_symbol, ident)
        edge("ui." + ident, "api." + ident, "call", "Sends request")
    node(
        "image-check",
        "Check PNG",
        "function",
        "domain.py",
        "valid_image",
        "upload",
        outputs={"valid": "boolean"},
    )
    node(
        "review-policy",
        "Review permission" if version == 1 else "Permission & same image version",
        "decision",
        "policy.py",
        "approval_policy",
        "publish",
        inputs={"actor": "string", "current_version": "number", "reviewed_version": "number"},
        outputs={"verdict": "string"},
        semantic_roles=["permission"],
    )
    node(
        "choose-version",
        "Select image version",
        "function",
        "domain.py",
        "choose_version",
        "publish",
        inputs={"current_version": "number"},
        outputs={"selected": "number"},
    )
    for state in ["empty", "pending", "displayed"]:
        node("state." + state, state.capitalize(), "state", value=state)
    for a, b in [("upload", "review"), ("review", "publish"), ("publish", "exhibit")]:
        edge(a, b, "flow", "Next step")
    for a, b, label in [
        ("upload", "image-check", "Checks content"),
        ("publish", "review-policy", "Evaluates request"),
        ("publish", "choose-version", "Selects version"),
    ]:
        edge(a, b, "call", label)
    edge("review-policy", "choose-version", "guard", "Allowed")
    edge("state.empty", "upload", "guard", "Before first upload")
    edge("upload", "state.pending", "flow", "Awaits review")
    edge("state.pending", "publish", "guard", "Review candidate")
    edge("publish", "state.displayed", "flow", "Committed")
    machine = {
        "engine": "python.explicit",
        "version": str(version),
        "state_type": "enum",
        "states": ["empty", "pending", "displayed"],
        "values": ["empty", "pending", "displayed"],
        "initial": "empty",
        "transitions": [
            {"source": "empty", "dest": "pending", "trigger": "upload"},
            {"source": "pending", "dest": "pending", "trigger": "replace"},
            {"source": "pending", "dest": "displayed", "trigger": "approve"},
        ],
        "events": {name: {"payload": {}} for name in ["upload", "replace", "approve"]},
        "context": {
            key: {"type": "number"}
            for key in ["image_version", "reviewed_version", "published_version"]
        },
        "guards": {},
    }
    project = {
        "protocol": "bo-project/v1",
        "project_id": "afterlight-case",
        "selection": {
            "mode": "observe",
            "source": "user",
            "answer": "Keep native application logic and observe it",
            "locator": "review/dialogue.md#mode",
        },
        "model": {
            "schema_version": 3,
            "revision": str(version),
            "project_id": "afterlight-case",
            "intent": "intent.json",
            "source_files": source_files,
            "nodes": nodes,
            "edges": edges,
            "machine": machine,
            "overview": [{"node": n} for n in ["upload", "review", "publish", "exhibit"]],
            "scope": {"unknowns": []},
            "presentation": {"subject": "Afterlight · iteration " + str(version)},
        },
    }
    write(root / "bo_stategraph/project.json", project)
    write(
        root / "intent.json",
        {
            "project_id": "afterlight-case",
            "requirements": [
                {
                    "id": "R1",
                    "text": "Publish only the image version the reviewer opened; keep replacements pending.",
                    "status": "confirmed",
                    "source": "review/dialogue.md",
                }
            ],
        },
    )
    operations = []
    for ident, label, parent, symbol, action, targets in [
        (
            "read-artwork",
            "Read current version",
            "publish",
            "Repository.read_artwork",
            "read",
            ["table:artwork"],
        ),
        (
            "save-upload",
            "Save image & notification",
            "upload",
            "Repository.save_upload",
            "write",
            ["table:images", "table:artwork", "table:messages"],
        ),
        (
            "save-exhibition",
            "Publish selected image",
            "publish",
            "Repository.publish",
            "write",
            ["table:exhibition", "table:artwork"],
        ),
        (
            "read-public",
            "Read exhibition & messages",
            "exhibit",
            "Repository.public",
            "read",
            ["table:exhibition", "table:messages"],
        ),
        ("read-image", "Load image bytes", "exhibit", "Repository.image", "read", ["table:images"]),
        (
            "review-transaction",
            "Review transaction",
            "publish",
            "Gallery.approve",
            "transaction",
            [],
        ),
    ]:
        operations.append(
            {
                "id": ident,
                "label": label,
                "parent": parent,
                "store": "gallery",
                "action": action,
                "targets": targets,
                "parameters": {"selected": "number"} if ident == "save-exhibition" else {},
                **(
                    {
                        "target_actions": {
                            target: (
                                "read_write"
                                if target
                                == (
                                    "table:artwork"
                                    if ident == "save-upload"
                                    else "table:exhibition"
                                )
                                else "write"
                            )
                            for target in targets
                        }
                    }
                    if action == "write"
                    else {}
                ),
                "source": {
                    "path": "domain.py" if ident == "review-transaction" else "repository.py",
                    "symbol": symbol,
                },
                "before": {},
                "after": {},
                "inputs": [],
                "required_cases": ["replacement-review"],
            }
        )
    (root / "export_model.py").write_text(
        "import sys, json\nsys.path.insert(0, " + repr(str(SKILL / "scripts")) + ")\n"
        "from repository import metadata\nfrom bo_observer.data.catalog import export_sqlalchemy_metadata\n"
        "print(json.dumps(export_sqlalchemy_metadata(metadata, 'gallery')))\n",
        encoding="utf-8",
    )
    operations.append(
        {
            "id": "version-selection",
            "label": "Choose publication version",
            "parent": "publish",
            "store": "gallery",
            "action": "transform",
            "targets": [],
            "parameters": {},
            "before": {"current_version": "number"},
            "after": {"selected": "number"},
            "source": {"path": "domain.py", "symbol": "choose_version"},
            "inputs": ["read-artwork"],
            "required_cases": ["replacement-review"],
        }
    )
    next(operation for operation in operations if operation["id"] == "save-exhibition")[
        "inputs"
    ] = ["version-selection"]
    # Initialize only schema here; the server creates the artwork row for each run.
    from sqlalchemy import create_engine
    import importlib.util

    spec = importlib.util.spec_from_file_location("case_repository", root / "repository.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite:///" + (root / "gallery.sqlite").as_posix())
    module.metadata.create_all(engine)
    engine.dispose()
    os.environ["BO_CASE_DB"] = "sqlite:///" + (root / "gallery.sqlite").as_posix()
    config = {
        "protocol": "bo-databases/v1",
        "stores": [
            {
                "id": "gallery",
                "label": "Gallery database",
                "engine": "sqlalchemy",
                "url_env": "BO_CASE_DB",
                "model_layer": "SQLAlchemy Core metadata",
                "source_files": ["repository.py"],
                "declaration": "bo_stategraph/schema.json",
                "selection": {
                    "source": "user",
                    "answer": "SQLite for a local demo",
                    "locator": "review/dialogue.md#database",
                },
            }
        ],
        "operations": operations,
        "exporters": [
            {
                "store": "gallery",
                "command": ["{python}", "export_model.py"],
                "output": "bo_stategraph/schema.json",
            }
        ],
    }
    write(root / "bo_stategraph/databases.json", config)
    write(
        root / "sync.json",
        {
            "model": "bo_stategraph/project.json",
            "source_scope": {
                "roots": ["."],
                "exclude": {
                    "bo_integration.py": "Observer adapter",
                    "export_model.py": "Observer schema export",
                },
            },
        },
    )
    checked = synchronize(root)
    if not checked["valid"]:
        raise ValueError(checked)
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--version", type=int, choices=[1, 2], default=2)
    arguments = parser.parse_args()
    print(prepare(arguments.root.resolve(), arguments.version))
