"""Small CLI used by an explicitly invoked skill to control presentation."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from .scope import ControlScope, user_command, read
from .selection import build_plan, model_revision, ClarificationRequired


def local_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use the project's verified local observer URL")
    return value.rstrip("/").removesuffix("/graph")


def get(base, route):
    with urlopen(base + route, timeout=10) as response:
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Observer response exceeds the inspection budget")
    return json.loads(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["activate", "inspect", "plan", "apply", "status", "end"]
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--conversation")
    parser.add_argument(
        "--message",
        required=True,
        help="The actual current user message, never quoted source material",
    )
    parser.add_argument("--url", help="The verified local observer URL")
    parser.add_argument(
        "--snapshot", type=Path, help="A current observer JSON snapshot, for offline preview"
    )
    parser.add_argument(
        "--spec", type=Path, help="A structured interpretation of this prefixed user request"
    )
    parser.add_argument(
        "--recording", help="Exact stopped recording ID; no implicit latest selection"
    )
    args = parser.parse_args(argv)
    scope = ControlScope(args.root)
    try:
        if args.command == "activate":
            if not args.url:
                raise ValueError("Activation requires the verified observer URL")
            base = local_url(args.url)
            view = get(base, "/api/view")
            known = set()
            if view.get("stage") == "design":
                from ..web.bo_design import BODesign
                from ..graph.behavior_model import digest

                local = BODesign(scope.root).view()
                if (
                    digest(local["model"]) != digest(view["model"])
                    or local["manifest"]["build_id"] != view["manifest"]["build_id"]
                ):
                    raise ValueError("Observer design does not match this project's declaration")
                known.add(local["layout_id"])
            for path in [scope.root / "bo_stategraph/project.json", scope.root / "behavior.json"]:
                if path.exists():
                    value = read(path)
                    known.update(
                        filter(
                            None,
                            [
                                value.get("project_id"),
                                value.get("presentation", {}).get("layout_id"),
                            ],
                        )
                    )
            sync = scope.root / "sync.json"
            if sync.exists() and view.get("stage") != "design":
                path = (scope.root / read(sync)["model"]).resolve()
                if not path.is_relative_to(scope.root):
                    raise ValueError("Model path leaves the selected project")
                model = read(path)
                known.update(
                    filter(
                        None,
                        [model.get("project_id"), model.get("presentation", {}).get("layout_id")],
                    )
                )
            project_id = (
                view.get("layout_id")
                or view["model"].get("project_id")
                or view["model"].get("presentation", {}).get("layout_id")
            )
            if project_id not in known:
                raise ValueError("Observer identity does not match this project's declaration")
            value = scope.activate(args.message, project_id, args.conversation)
            result = {
                "active": True,
                "session": value["session"],
                "graph_url": base + "/graph?vl_session=" + value["session"],
            }
        else:
            active = scope.authorized(args.message, args.conversation)
            if args.command == "status":
                result = scope.for_view(active["session"])
            elif args.command == "end":
                result = scope.end(args.message, args.conversation)
            else:
                base = local_url(args.url) if args.url else None
                view = (
                    get(base, "/api/view")
                    if base
                    else read(args.snapshot) if args.snapshot else None
                )
                if not view:
                    raise ValueError("Provide a verified observer URL or current snapshot")
                project_id = (
                    view.get("layout_id")
                    or view["model"].get("project_id")
                    or view["model"].get("presentation", {}).get("layout_id")
                )
                if project_id != active["project_id"]:
                    raise ValueError("Snapshot belongs to another project")
                if args.command == "inspect":
                    result = {
                        "project_id": project_id,
                        "model_revision": model_revision(view),
                        "nodes": [
                            {
                                key: node[key]
                                for key in (
                                    "id",
                                    "label",
                                    "kind",
                                    "parent",
                                    "source",
                                    "semantic_roles",
                                )
                                if key in node
                            }
                            for node in view["model"]["nodes"]
                        ],
                        "edges": view["model"]["edges"],
                        "recordings": (
                            get(base, "/api/recordings")
                            if base and view.get("stage") != "design"
                            else []
                        ),
                    }
                else:
                    if not args.spec:
                        raise ValueError(
                            "A structured interpretation of the user's requested view is required"
                        )
                    spec = read(args.spec)
                    recording = None
                    if spec.get("action") == "replay":
                        if view.get("stage") == "design":
                            raise ValueError(
                                "Design graphs have no runtime recordings; choose a live implementation"
                            )
                        if (
                            not base
                            or not args.recording
                            or not all(char.isalnum() or char in "-_" for char in args.recording)
                        ):
                            raise ValueError(
                                "Replay filtering requires an exact recording ID and observer URL"
                            )
                        recording = get(base, "/api/recordings/" + args.recording)
                    plan = build_plan(view, spec, recording)
                    result = (
                        scope.publish(args.message, plan, args.conversation)
                        if args.command == "apply"
                        else plan
                    )
        print(json.dumps({"valid": True, "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except ClarificationRequired as error:
        print(
            json.dumps({"valid": False, "needs_clarification": error.question}, ensure_ascii=False)
        )
        return 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, ensure_ascii=False))
        return 1
