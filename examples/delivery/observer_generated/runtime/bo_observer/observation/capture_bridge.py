"""Acknowledged capture controls across a process/language boundary.

Producers pull a tiny allowlist of observer operations. There is no callable,
source path or application command in this protocol. Queue draining waits on a
condition outside the event-ingestion lock, so actual events can still arrive.
"""

from copy import deepcopy
import threading
import time
import uuid

PROTOCOL = "bo-capture-control/v1"


class CaptureBridge:
    bo_boundary_events = True

    def __init__(self, session, timeout=5):
        self.session = session
        self.timeout = timeout
        self.condition = threading.Condition()
        self.clients = {}
        self.pending = {}
        self.bound = False

    def exchange(self, body):
        """Register/poll/acknowledge only against this exact project and build."""
        if not isinstance(body, dict) or set(body) - {
            "protocol",
            "project_id",
            "build_id",
            "producer_id",
            "action",
            "ack",
        }:
            raise ValueError("invalid capture control envelope")
        if (
            body.get("protocol") != PROTOCOL
            or body.get("project_id") != self.session.project["project_id"]
            or body.get("build_id") != self.session.manifest["build_id"]
        ):
            raise ValueError("capture control project/build differs")
        producer, action = body.get("producer_id"), body.get("action")
        if (
            not isinstance(producer, str)
            or not 1 <= len(producer) <= 160
            or action not in {"register", "poll", "ack"}
        ):
            raise ValueError("unsupported capture operation or producer")
        if (action == "ack") != ("ack" in body):
            raise ValueError("only acknowledgement messages may carry an ack")
        with self.condition:
            if action == "register":
                if producer not in self.clients:
                    if self.pending or self.session.recordings.active:
                        raise ValueError("register producers before starting a recording")
                    if len(self.clients) >= 64:
                        raise ValueError("capture producer limit exceeded")
                    if not self.bound:
                        if self.session.recordings.bo_capture_flush is not None:
                            raise ValueError("a capture controller is already bound")
                        self.session.bo_bind_capture(
                            scope_setter=self.set_scope,
                            flush_capture=self.flush,
                            health=self.health,
                        )
                        self.bound = True
                    self.clients[producer] = {"health": {}, "seen": time.monotonic()}
            if producer not in self.clients:
                raise ValueError("capture producer is not registered")
            self.clients[producer]["seen"] = time.monotonic()
            if action == "ack":
                ack = body.get("ack")
                if (
                    not isinstance(ack, dict)
                    or set(ack) != {"id", "ok", "health"}
                    or type(ack["ok"]) is not bool
                    or not isinstance(ack["health"], dict)
                    or not isinstance(ack["id"], str)
                ):
                    raise ValueError("invalid capture acknowledgement")
                request = self.pending.get(ack["id"])
                if request is None or producer not in request["waiting"]:
                    raise ValueError("stale or repeated capture acknowledgement")
                health = ack["health"]
                for key in ("errors", "dropped", "pending"):
                    if type(health.get(key)) is not int or health[key] < 0:
                        raise ValueError("capture acknowledgement needs actual health counters")
                for key in ("queue_submitted", "queue_completed", "flush_target"):
                    if key in health and (type(health[key]) is not int or health[key] < 0):
                        raise ValueError("capture queue counters must be nonnegative integers")
                request["waiting"].remove(producer)
                request["ok"] = request["ok"] and ack["ok"]
                self.clients[producer]["health"] = deepcopy(health)
                self.condition.notify_all()
            commands = [
                deepcopy(item["command"])
                for item in self.pending.values()
                if producer in item["waiting"]
            ]
            return {"protocol": PROTOCOL, "commands": commands}

    def request(self, action, **fields):
        """Wait for every registered producer; missing replies are explicit gaps."""
        expected = {"scope": {"nodes"}, "flush": {"timeout_ms"}}
        if action not in expected or set(fields) != expected[action]:
            raise ValueError("unsupported capture control command")
        ident = uuid.uuid4().hex
        command = {"id": ident, "action": action, **fields}
        with self.condition:
            if not self.clients:
                return False
            request = {"command": command, "waiting": set(self.clients), "ok": True}
            self.pending[ident] = request
            deadline = time.monotonic() + self.timeout
            try:
                while request["waiting"]:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    self.condition.wait(remaining)
                return request["ok"]
            finally:
                del self.pending[ident]

    def set_scope(self, nodes):
        if nodes is not None and (
            not isinstance(nodes, list) or any(node not in self.session.bo_nodes for node in nodes)
        ):
            raise ValueError("capture scope requires declared nodes")
        if not self.request("scope", nodes=nodes):
            raise ValueError("capture scope was not acknowledged by every producer")

    def flush(self):
        return self.request("flush", timeout_ms=max(1, int(self.timeout * 800)))

    def health(self):
        with self.condition:
            return {
                "enabled": bool(self.clients),
                "boundary_context": True,
                **{
                    key: sum(client["health"].get(key, 0) for client in self.clients.values())
                    for key in (
                        "errors",
                        "dropped",
                        "pending",
                        "queue_submitted",
                        "queue_completed",
                        "flush_target",
                    )
                },
                "producers": len(self.clients),
            }
