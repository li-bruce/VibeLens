"""Bounded observation history. Current business state is never deleted here."""

from collections import deque
from copy import deepcopy
import json
import os
from pathlib import Path
import threading
import time

DEFAULTS = {
    "memory_events": 10000,
    "memory_seconds": 1800,
    "log_bytes": 8 * 1024 * 1024,
    "log_backups": 2,
}


class EventHistory:
    def __init__(self, *, project_root=None, path=None, limits=None):
        settings = dict(DEFAULTS)
        if project_root:
            config = Path(project_root) / "bo_stategraph/config/retention.json"
            if config.exists():
                settings.update(json.loads(config.read_text(encoding="utf-8")))
        settings.update(limits or {})
        if set(settings) != set(DEFAULTS) or any(
            type(v) is not int or v <= 0 for v in settings.values()
        ):
            raise ValueError("retention limits must be positive integers with known names")
        self.limits, self.path = settings, Path(path) if path else None
        self.events, self.listeners = deque(), []
        self.lock = threading.RLock()
        self.evicted = self.log_errors = self.listener_errors = 0

    def _trim(self):
        cutoff = time.monotonic() - self.limits["memory_seconds"]
        while self.events and (
            len(self.events) > self.limits["memory_events"] or self.events[0][0] < cutoff
        ):
            self.events.popleft()
            self.evicted += 1

    def append(self, event):
        self.append_many([event])

    def append_many(self, events):
        """Publish a validated ordered group with one bounded log append session.

        Each event remains independently retained and delivered to every listener.
        File rotation still occurs at an event boundary, with the same byte limit.
        """
        copies = [deepcopy(event) for event in events]
        with self.lock:
            self.events.extend((time.monotonic(), event) for event in copies)
            self._trim()
            listeners = list(self.listeners)
        # Recording listeners copy bounded data in memory, before UI history expires.
        for event in events:
            for listener in listeners:
                try:
                    listener(event)
                except Exception:
                    self.listener_errors += 1
        if self.path:
            try:
                self._log_many(events)
            except OSError:
                self.log_errors += len(events)

    def _log_many(self, events):
        """Reuse the file handle while retaining per-line rotation and error limits."""
        lines = [(json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8") for event in events]
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            size = self.path.stat().st_size if self.path.exists() else 0
            stream = None
            try:
                for raw in lines:
                    if len(raw) > self.limits["log_bytes"]:
                        self.log_errors += 1
                        continue
                    if size + len(raw) > self.limits["log_bytes"]:
                        if stream is not None:
                            stream.close()
                            stream = None
                        self._rotate()
                        size = 0
                    if stream is None:
                        stream = self.path.open("ab")
                    stream.write(raw)
                    size += len(raw)
            finally:
                if stream is not None:
                    stream.close()

    def _rotate(self):
        """Retain the configured number of complete previous log files."""

        def rotated(i):
            return self.path.with_name(self.path.name + "." + str(i))

        for i in range(self.limits["log_backups"], 1, -1):
            if rotated(i - 1).exists():
                os.replace(rotated(i - 1), rotated(i))
        if self.path.exists():
            os.replace(self.path, rotated(1))

    def snapshot(self):
        with self.lock:
            self._trim()
            return deepcopy([event for _, event in self.events])

    def _capture_references(self):
        """Pin private copy-on-ingress events for cloning outside the session lock.

        Only the view assembler uses these references. Public reads still return
        independent values; expiry may remove deque entries but cannot edit them.
        """
        with self.lock:
            self._trim()
            return tuple(event for _, event in self.events)

    def subscribe(self, listener):
        with self.lock:
            self.listeners.append(listener)

        def unsubscribe():
            with self.lock:
                if listener in self.listeners:
                    self.listeners.remove(listener)

        return unsubscribe

    def health(self):
        with self.lock:
            self._trim()
            return {
                "retained_events": len(self.events),
                "evicted_events": self.evicted,
                "history_start_seq": self.events[0][1].get("seq") if self.events else None,
                "log_errors": self.log_errors,
                "listener_errors": self.listener_errors,
                "retention": dict(self.limits),
            }
