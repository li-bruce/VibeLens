"""Explicit activation and authorization for one conversation and project."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

from ..web.view_preferences import file_lock, Preferences


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    """Replace one private control document without touching project source."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix("." + secrets.token_hex(8) + ".tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def user_command(message):
    """Only an unquoted prefix at the start of the actual user message authorizes a control."""
    if isinstance(message, str):
        message = re.sub(r"^\s*\$vibelens\s+(?=/vibelens(?:\s|$))", "", message)
    if (
        not isinstance(message, str)
        or len(message) > 16000
        or not re.match(r"^/vibelens(?:\s|$)", message.lstrip())
    ):
        raise ValueError(
            "Viewer controls require an explicit /vibelens prefix in this user message"
        )
    text = message.lstrip()[len("/vibelens") :].strip()
    if not text:
        raise ValueError("Describe the VibeLens view or replay operation after /vibelens")
    return text


class ControlScope:
    """A local scope is bound to its canonical project path and host conversation identity."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = self.root / "bo_stategraph/config/control"

    def conversation(self, supplied=None):
        current = os.environ.get("CODEX_THREAD_ID")
        if current and supplied and current != supplied:
            raise ValueError("The requested conversation differs from CODEX_THREAD_ID")
        value = current or supplied
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", value):
            raise ValueError(
                "A host conversation ID is required; never infer a global active conversation"
            )
        return value

    def _path(self, token):
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
            raise ValueError("Invalid VibeLens session")
        return self.directory / (token + ".json")

    def _bound(self, value):
        if value.get("schema") != "vibelens-control-session/v1" or value.get("root") != str(
            self.root
        ):
            raise ValueError("Control session belongs to another project")
        if value.get("active") is not True:
            raise ValueError("VibeLens is not active in this conversation")
        return value

    def activate(self, message, project_id, conversation=None):
        """Activation never installs instructions into other conversations or changes views."""
        if not isinstance(message, str) or not re.match(
            r"^(?:\$vibelens(?:\s|$)|Use\s+\$vibelens\b|使用\s*\$vibelens\b)",
            message.lstrip(),
            re.IGNORECASE,
        ):
            raise ValueError(
                "Explicit $vibelens invocation is required to activate this conversation"
            )
        if not isinstance(project_id, str) or not 1 <= len(project_id) <= 256:
            raise ValueError("A declared project identity is required")
        conversation = self.conversation(conversation)
        token = hashlib.sha256((str(self.root) + "\0" + conversation).encode()).hexdigest()[:32]
        path = self._path(token)
        with file_lock(path.with_suffix(".lock")):
            if path.exists():
                previous = read(path)
                if previous.get("active") and previous.get("project_id") != project_id:
                    raise ValueError(
                        "Project identity changed; end the old control session explicitly"
                    )
                if previous.get("active"):
                    return self._bound(previous)
            value = {
                "schema": "vibelens-control-session/v1",
                "session": token,
                "root": str(self.root),
                "conversation": conversation,
                "project_id": project_id,
                "active": True,
                "revision": 0,
                "plan": None,
                "result": None,
            }
            write(path, value)
        return deepcopy(value)

    def authorized(self, message, conversation=None):
        user_command(message)
        conversation = self.conversation(conversation)
        token = hashlib.sha256((str(self.root) + "\0" + conversation).encode()).hexdigest()[:32]
        path = self._path(token)
        if not path.exists():
            raise ValueError("Invoke $vibelens in this conversation before using controls")
        value = self._bound(read(path))
        if value["conversation"] != conversation:
            raise ValueError("Conversation identity differs")
        return value

    def publish(self, message, plan, conversation=None):
        """Publish a validated presentation plan; this API accepts no source-edit operation."""
        from .selection import validate_plan

        validate_plan(plan)
        current = self.authorized(message, conversation)
        path = self._path(current["session"])
        with file_lock(path.with_suffix(".lock")):
            current = self.authorized(message, conversation)
            if plan["base"]["project_id"] != current["project_id"]:
                raise ValueError("Plan belongs to another project")
            current.update(revision=current["revision"] + 1, plan=deepcopy(plan), result=None)
            write(path, current)
        return current

    def end(self, message, conversation=None):
        current = self.authorized(message, conversation)
        path = self._path(current["session"])
        with file_lock(path.with_suffix(".lock")):
            current = self.authorized(message, conversation)
            current.update(active=False, plan=None, revision=current["revision"] + 1)
            write(path, current)
        return {"active": False, "session": current["session"]}

    def for_view(self, token):
        """The graph window reads only its explicitly selected session, without a global fallback."""
        value = read(self._path(token))
        if value.get("schema") != "vibelens-control-session/v1" or value.get("root") != str(
            self.root
        ):
            raise ValueError("Control session belongs to another project")
        return {
            key: deepcopy(value[key])
            for key in ("schema", "session", "project_id", "active", "revision", "plan", "result")
        }

    def preferences(self, token, fallback=None):
        value = self.for_view(token)
        return Preferences(
            self.root,
            value["project_id"],
            namespace=token,
            legacy_project_ids=sorted(fallback.legacy_project_ids) if fallback else (),
        )

    def acknowledge(self, token, value):
        """Record viewer application status, never application/runtime observations."""
        if set(value) != {"revision", "status", "view_id", "nodes", "events", "error"} or value[
            "status"
        ] not in {"applied", "rejected"}:
            raise ValueError("Invalid control acknowledgement")
        path = self._path(token)
        with file_lock(path.with_suffix(".lock")):
            current = self._bound(read(path))
            if value["revision"] != current["revision"]:
                raise ValueError("Control acknowledgement is stale")
            if (
                not isinstance(value["nodes"], list)
                or len(value["nodes"]) > 1000
                or not isinstance(value["events"], list)
                or len(value["events"]) > 50000
                or len(str(value["error"])) > 1000
            ):
                raise ValueError("Control acknowledgement exceeds its bounds")
            current["result"] = deepcopy(value)
            write(path, current)
        return {"recorded": True, "revision": current["revision"]}
