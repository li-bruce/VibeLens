"""Standalone capture-control client. Only selection and queue draining are exposed."""

import json
import threading
from contextlib import nullcontext
from urllib.request import Request, urlopen

try:
    from .bo_probe import bo_internal
except ImportError:
    from bo_probe import bo_internal


class BOCaptureClient:
    def __init__(self, probe):
        self.bo_probe = probe
        self.bo_stop = threading.Event()
        self.bo_errors = 0
        self.bo_worker = threading.Thread(
            target=self.bo_poll, daemon=True, name="bo-capture-control"
        )

    def bo_exchange(self, action, **fields):
        probe = self.bo_probe
        body = {
            "protocol": "bo-capture-control/v1",
            "project_id": probe.bo_project["project_id"],
            "build_id": probe.bo_build,
            "producer_id": probe.bo_producer,
            "action": action,
            **fields,
        }
        request = Request(
            probe.bo_endpoint + "/api/bo/capture",
            json.dumps(body).encode(),
            {"Content-Type": "application/json", "X-BO-Token": probe.bo_token},
        )
        # Control HTTP is observer work even with broad automatic instrumentation.
        # Context-local suppression leaves concurrent application calls visible.
        with bo_internal(), probe.bo_tracing.internal() if probe.bo_tracing else nullcontext():
            with urlopen(request, timeout=2) as response:
                raw = response.read(24577)
        if len(raw) > 24576:
            raise ValueError("capture control response exceeds limit")
        value = json.loads(raw)
        if (
            not isinstance(value, dict)
            or set(value) != {"protocol", "commands"}
            or value["protocol"] != "bo-capture-control/v1"
            or not isinstance(value["commands"], list)
            or len(value["commands"]) > 64
            or any(
                not isinstance(command, dict) or not isinstance(command.get("id"), str)
                for command in value["commands"]
            )
        ):
            raise ValueError("invalid capture control response")
        return value

    def start(self):
        """Explicit startup reports registration errors; ordinary operations stay native."""
        self.bo_exchange("register")
        self.bo_worker.start()
        return self

    def bo_poll(self):
        while not self.bo_stop.is_set():
            try:
                reply = self.bo_exchange("poll")
                for command in reply["commands"]:
                    ok = False
                    if command.get("action") == "scope" and set(command) == {
                        "id",
                        "action",
                        "nodes",
                    }:
                        self.bo_probe.bo_set_scope(command["nodes"])
                        ok = True
                    elif command.get("action") == "flush" and set(command) == {
                        "id",
                        "action",
                        "timeout_ms",
                    }:
                        timeout = command["timeout_ms"]
                        if type(timeout) is int and 0 < timeout <= 30000:
                            ok = self.bo_probe.flush(timeout / 1000)
                    self.bo_exchange(
                        "ack",
                        ack={
                            "id": command["id"],
                            "ok": bool(ok),
                            "health": self.bo_probe.bo_health(),
                        },
                    )
            except (OSError, ValueError, KeyError, TypeError):
                self.bo_errors += 1
            self.bo_stop.wait(0.1)

    def close(self):
        self.bo_stop.set()
        if self.bo_worker.is_alive():
            self.bo_worker.join(3)
