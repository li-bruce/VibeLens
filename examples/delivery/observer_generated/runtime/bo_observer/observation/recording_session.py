"""Local observation intervals. Playback never calls application commands.

The provider returns a consistent, already instrumented graph view. Sampling
copies its event stream; it does not sample function execution or invent events.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import re
import threading
import time
import uuid
from .capture_context import context_candidates, retain_scope
from ..graph.observation_scope import capture_owners

try:
    from ...bo_models import machine_registry
    from ...runtime_frames import merge_frames
    from ...observation_scope import bo_internal
except ImportError:
    from bo_models import machine_registry
    from runtime_frames import merge_frames
    from observation_scope import bo_internal

SCHEMA = "stategraph-recording/v1"
OWNERSHIP_GAP = "A parent invocation entry was not retained; its execution boundary is incomplete."


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def graph_version(view):
    """Identify code and graph content, independently of clocks and runtime state."""
    manifest = view["manifest"]
    model_hash = manifest.get("model_hash")
    if not model_hash:
        model_hash = hashlib.sha256(
            json.dumps(
                view["model"],
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    return [manifest["build_id"], model_hash]


def checkpoint(view, *, context=False):
    """Keep graph facts, not document bodies or arbitrary application state."""
    authority = view["authority"]
    model = view.get("model", {})
    fields = model.get("presentation", {}).get("recording", {}).get("parameters")
    if fields is None:
        # Recording also accepts source-only/legacy views with no state model.
        # Full project admission still validates every declared registry.
        machines = machine_registry(model) if "machine" in model or "machines" in model else {}
        fields = sorted({key for chart in machines.values() for key in chart.get("context", {})})

    value = {
        "authority": {
            "entity": authority.get("entity"),
            "state": authority.get("state"),
            "basis": deepcopy(authority.get("basis", {})),
            "parameters": {
                k: deepcopy(authority.get("parameters", {}).get(k))
                for k in fields
                if k in authority.get("parameters", {})
            },
            "effects": [],  # Commit effects are read from selected probe fields.
        },
        "machine": deepcopy(view["machine"]),
        "health": deepcopy(view["health"]),
        "binding_status": deepcopy(view["binding_status"]),
        "historical": True,
        "busy": False,
    }
    if context:
        if view.get("project_structure"):
            value["project_structure"] = deepcopy(view["project_structure"])
        if view.get("api_structure"):
            value["api_structure"] = deepcopy(view["api_structure"])
        if view.get("concept_structure"):
            value["concept_structure"] = deepcopy(view["concept_structure"])
        value.update(
            model=deepcopy(view["model"]),
            manifest=deepcopy(view["manifest"]),
            events=deepcopy(
                list(
                    {
                        e["id"]: e
                        for e in [*view.get("open_invocations", []), *view["events"][-2000:]]
                    }.values()
                )
            ),
        )
    return value


class Recordings:
    def __init__(
        self,
        directory,
        provider,
        sources,
        *,
        action_nodes=None,
        interval=1.0,
        max_events=20000,
        max_bytes=32 * 1024 * 1024,
        scope_setter=None,
        capture_flush=None,
        event_source=None,
        command_fields=(),
        context_provider=None,
        version_provider=None,
    ):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

        def internal_reader(callback):
            def read():
                with bo_internal():
                    return callback()

            return read

        self.provider = internal_reader(provider)
        self.context_provider = internal_reader(context_provider or provider)
        self.version_provider = internal_reader(version_provider or provider)
        self.sources = sources
        self.action_nodes = action_nodes or {}
        self.bo_scope_setter = scope_setter
        self.bo_boundary_context = bool(
            getattr(getattr(scope_setter, "__self__", None), "bo_boundary_events", False)
        )
        self.bo_capture_flush = capture_flush
        self.interval, self.max_events, self.max_bytes = interval, max_events, max_bytes
        self.lock, self.operations = threading.RLock(), threading.Lock()
        self.stream_lock = threading.Lock()
        self._capture_open = False
        self.active, self.cached, self.last_error = None, {}, ""
        self.catalog = {}
        self.command_fields = tuple(command_fields)
        self._stream_events = {}
        self._capture_context = []
        self._starting = self._stream_limited = False
        self._unsubscribe = event_source.subscribe(self.bo_event) if event_source else None
        self.closed = threading.Event()
        # An interrupted process never continues the old interval under a new ID.
        for path in self.directory.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("schema") == SCHEMA:
                    self.catalog[path.stem] = self.summary(value)
                if value.get("schema") == SCHEMA and value.get("status") == "recording":
                    value.update(status="interrupted", ended_at=timestamp())
                    value["gaps"].append(
                        "The program ended before recording stopped; only the last saved record is retained."
                    )
                    self._write(value)
            except (OSError, ValueError, KeyError):
                self.last_error = "A recording could not be read; the original file was preserved."
        self.worker = threading.Thread(
            target=self._worker, daemon=True, name="stategraph-recordings"
        )
        self.worker.start()

    def bo_event(self, event):
        """Retain incoming events during an active or starting recording, within its budget."""
        with self.stream_lock:
            if not self._capture_open:
                return
            if len(self._stream_events) > self.max_events:
                self._stream_limited = True
                return
            self._stream_events[event["id"]] = deepcopy(event)

    def _path(self, ident):
        if not isinstance(ident, str) or not re.fullmatch(r"[a-f0-9]{32}", ident):
            raise ValueError("Invalid recording ID")
        return self.directory / (ident + ".json")

    def _write(self, value):
        path = self._path(value["id"])
        data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(data.encode("utf-8")) > self.max_bytes:
            raise ValueError("Recording size limit reached")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(data, encoding="utf-8", newline="\n")
        # Windows readers can briefly deny replacement even after our own file
        # handle has closed. Retry only those OS errors, with a 35 ms sleep budget.
        # Exhaustion still reaches _save's explicit interruption/gap handling.
        for delay in (0.005, 0.01, 0.02, None):
            try:
                temporary.replace(path)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) not in {5, 32, 33} or delay is None:
                    raise
                time.sleep(delay)
        self.cached[value["id"]] = value
        self.catalog[value["id"]] = self.summary(value)
        while len(self.cached) > 8:
            oldest = next(iter(self.cached))
            if self.active and oldest == self.active["id"]:
                self.cached[oldest] = self.cached.pop(oldest)
                continue
            del self.cached[oldest]

    def _save(self, value):
        """Persist a recording and mark any missing frames or write failure as visible gaps."""
        if value["status"] != "recording" and "runtime_frames" in value:
            captured = {f["event_id"] for f in value["runtime_frames"]["frames"]}
            partial = value["runtime_frames"].get("partial") is True
            missing = sum(
                not e.get("context_only") and e["id"] not in captured
                for e in value["events"]
                if not partial or type(e.get("revision")) is int
            )
            if missing:
                message = (
                    f"{missing} steps have no matching runtime snapshot; no state was inferred."
                )
                if message not in value["gaps"]:
                    value["gaps"].append(message)
        try:
            self._write(value)
            self.last_error = ""
        except (OSError, ValueError) as error:
            # Recording failure cannot change a business operation's result.
            self.last_error = str(error)[:160]
            value["status"] = "interrupted"
            value["ended_at"] = timestamp()
            value["gaps"].append("Recording could not be saved: " + self.last_error)
            self.cached[value["id"]] = value
            self.catalog[value["id"]] = self.summary(value)
            if self.active is value:
                self.active = None
        finally:
            if value["status"] != "recording":
                with self.stream_lock:
                    self._capture_open = False
                try:
                    self.bo_restore_capture()
                except (OSError, ValueError) as error:
                    # A remote producer may disappear before restoring full
                    # capture. Preserve that fact and allow observer shutdown.
                    self.last_error = "Capture scope restore failed: " + str(error)[:120]
                    value["status"] = "interrupted"
                    if self.last_error not in value["gaps"]:
                        value["gaps"].append(self.last_error)
                    self.cached[value["id"]] = value
                    self.catalog[value["id"]] = self.summary(value)
                    try:
                        self._write(value)
                    except (OSError, ValueError):
                        pass  # The interrupted in-memory evidence remains readable.

    def bo_capture_plan(self, model, requested=None, *, view=None):
        """Resolve selected regions to descendants and the parents needed to explain them."""
        requested = requested or {"mode": "all"}
        if not isinstance(requested, dict) or requested.get("mode") not in ("all", "focused"):
            raise ValueError("Invalid capture scope")
        if requested["mode"] == "all":
            return {"mode": "all", "nodes": None, "roots": [], "boundary_nodes": []}
        if self.bo_scope_setter is None:
            raise ValueError("Focused capture is not connected in this application")
        nodes = {n["id"]: n for n in model["nodes"]}
        roots = requested.get("roots", requested.get("nodes", []))
        if (
            not isinstance(roots, list)
            or not roots
            or len(roots) > 2000
            or any(not isinstance(n, str) for n in roots)
        ):
            raise ValueError("Select a valid node or region")
        # Display concepts are selectable, but only their verified native owners
        # enter the capture filter. No conceptual path becomes runtime authority.
        roots = capture_owners(view or {"model": model}, roots)
        selected = set(roots)
        while True:
            children = {n["id"] for n in nodes.values() if n.get("parent") in selected}
            if children <= selected:
                break
            selected.update(children)
        boundary = set()
        for ident in list(selected):
            parent, seen = nodes[ident].get("parent"), set()
            while parent in nodes and parent not in seen:
                seen.add(parent)
                boundary.add(parent)
                parent = nodes[parent].get("parent")
        for chart in machine_registry(model).values():
            parent = chart.get("execution", {}).get("parent")
            if parent in nodes:
                boundary.add(parent)  # Exact state revisions remain interpretable.
        return {
            "mode": "focused",
            "nodes": sorted(selected | boundary),
            "value_nodes": sorted(selected if self.bo_boundary_context else selected | boundary),
            "boundary_context": self.bo_boundary_context,
            "roots": sorted(set(roots)),
            "boundary_nodes": sorted(boundary - selected),
        }

    def bo_restore_capture(self):
        if self.bo_scope_setter:
            self.bo_scope_setter(None)

    def start(self, label="", scope=None):
        """Serialize start/stop operations and clean up temporary capture state on failure."""
        with self.operations:
            try:
                return self._start(label, scope)
            finally:
                with self.lock:
                    self._starting = False
                    if not self.active:
                        with self.stream_lock:
                            self._capture_open = False
                            self._stream_events = {}

    def _start(self, label, scope):
        """Begin from a current build snapshot and freeze the requested capture scope."""
        if self.bo_capture_flush:
            with bo_internal():
                if self.bo_capture_flush() is not True:
                    raise ValueError("Producer queue did not drain before recording")
        view = self.provider()
        with self.lock:
            if self.active:
                if graph_version(self.active["context"]) == graph_version(view):
                    return self.summary(self.active)
                self._capture(self.active["id"], view)
        with self.lock:
            with self.stream_lock:
                self._stream_events = {}
                self._capture_open = True
                self._stream_limited = False
            self._starting = True
        # The stream listener is already retaining events. Stamp this boundary
        # before the initial snapshot so work during that read cannot predate it.
        started_at = timestamp()
        view = self.context_provider()
        if view.get("historical") or view["binding_status"]["status"] != "current":
            raise ValueError("Load the accepted current application first")
        health = view["health"]
        if not health.get("enabled", True):
            raise ValueError("Event capture is disabled for this application")
        if (
            health.get("boundary_context") is True
            or health.get("producer", {}).get("boundary_context") is True
        ):
            self.bo_boundary_context = True
        plan = self.bo_capture_plan(view["model"], scope, view=view)
        if self.bo_scope_setter:
            self.bo_scope_setter(plan.get("value_nodes", plan["nodes"]))
            try:
                latest = self.provider()
                if latest["binding_status"]["status"] != "current" or graph_version(
                    latest
                ) != graph_version(view):
                    raise ValueError("Source or graph changed while recording started")
                # Only runtime/health changes after capture selection. Retain the
                # exact static tree already scanned at this same graph version.
                if view.get("project_structure"):
                    latest["project_structure"] = view["project_structure"]
                if view.get("api_structure"):
                    latest["api_structure"] = view["api_structure"]
                if view.get("concept_structure"):
                    latest["concept_structure"] = view["concept_structure"]
                view = latest
            except Exception:
                self.bo_restore_capture()
                raise
            health = view["health"]
        value = {
            "schema": SCHEMA,
            "id": uuid.uuid4().hex,
            "label": str(label).strip()[:80] or "Operation recording",
            "status": "recording",
            "started_at": started_at,
            "ended_at": None,
            "build_id": view["manifest"]["build_id"],
            "run_id": health["run_id"],
            "start_seq": health["attempted"],
            "end_seq": health["attempted"],
            "context": checkpoint(view, context=True),
            "final": checkpoint(view),
            "sources": deepcopy(self.sources),
            "events": [],
            "commands": [],
            "gaps": [],
            "capture": plan,
            "command_fields": list(self.command_fields)
            or view.get("model", {})
            .get("presentation", {})
            .get("recording", {})
            .get("command_fields", []),
        }
        if plan["nodes"] is not None:
            value_nodes = set(plan.get("value_nodes", plan["nodes"]))
            self._capture_context = context_candidates(
                value["context"]["events"], value_nodes, view["model"]
            )
            _, value["context"]["events"] = retain_scope(
                [], self._capture_context, value_nodes, view["model"]
            )
        else:
            self._capture_context = []
        if len(view["events"]) > 2000:
            value["gaps"].append("Pre-recording context retains only the latest 2000 events.")
        merge_frames(value, view, checkpoint)
        with self.lock:
            try:
                with self.stream_lock:
                    self._stream_events = {
                        k: e
                        for k, e in self._stream_events.items()
                        if e.get("stream_id", e.get("run_id")) == value["run_id"]
                        and e["seq"] > value["start_seq"]
                    }
                    self._stream_limited = False
                self._write(value)
            except Exception:
                self.bo_restore_capture()
                raise
            self.active = value
            self._starting = False
            return self.summary(value)

    def _capture(self, ident, view):
        with self.lock:
            value = self.active
            if not value or value["id"] != ident:
                return
            health = view["health"]
            if health.get("run_id") != value["run_id"] or graph_version(view) != graph_version(
                value["context"]
            ):
                value.update(status="interrupted", ended_at=timestamp())
                value["gaps"].append(
                    "The capture process or code version changed; merging has stopped."
                )
                self.active = None
                self._save(value)
                return
            end = health["attempted"]
            if end < value["end_seq"]:
                return  # A slower concurrent sampler cannot replace a newer boundary.
            merged = {e["id"]: e for e in value["events"]}
            with self.stream_lock:
                merged.update(self._stream_events)
                stream_limited = self._stream_limited
            merged.update({e["id"]: e for e in view["events"]})
            events = [
                e
                for e in merged.values()
                if e.get("stream_id", e.get("run_id")) == value["run_id"]
                and value["start_seq"] < e["seq"] <= end
            ]
            events.sort(key=lambda e: e["seq"])
            capture_plan = value.get("capture", {})
            allowed = capture_plan.get("value_nodes", capture_plan.get("nodes"))
            excluded = 0
            if allowed is not None:
                received_count = len(events)
                events, value["context"]["events"] = retain_scope(
                    events, self._capture_context, set(allowed), view["model"]
                )
                excluded = received_count - len(events)
                value["capture"]["runtime_boundary_nodes"] = sorted(
                    {
                        event["node"]
                        for event in [*value["context"]["events"], *events]
                        if event.get("context_only")
                    }
                )
            value["scope_excluded"] = excluded
            value["capture_filtered"] = max(
                0,
                health.get("filtered", health.get("producer", {}).get("filtered", 0))
                - value["context"]["health"].get(
                    "filtered", value["context"]["health"].get("producer", {}).get("filtered", 0)
                ),
            )
            value.update(
                events=deepcopy(events[: self.max_events]), end_seq=end, final=checkpoint(view)
            )
            merge_frames(value, view, checkpoint)
            if len(events) > self.max_events or stream_limited:
                value.update(status="limited", ended_at=timestamp())
                value["gaps"].append(
                    "The event limit was reached; recording stopped automatically. Later events were not saved."
                )
                self.active = None
            initial = value["context"]["health"]
            if any(health.get(k, 0) > initial.get(k, 0) for k in ("errors", "dropped")):
                message = "Capture failures or lost events occurred in this interval; the path may be incomplete."
                if message not in value["gaps"]:
                    value["gaps"].append(message)
            if health.get("reference_evictions", 0) > initial.get("reference_evictions", 0):
                message = "The causal reference cache reached its limit; missing dependencies are not inferred."
                if message not in value["gaps"]:
                    value["gaps"].append(message)
            # History/cache expiry is not itself recording loss: the listener
            # may already retain every required entry. Report actual missing IDs.
            kept = [*value["context"]["events"], *value["events"]]
            identities = {event["id"] for event in kept}
            value["ownership_gaps"] = [
                {"event": event["id"], "parent_event_id": event["parent_event_id"]}
                for event in kept
                if event.get("parent_event_id") and event["parent_event_id"] not in identities
            ]
            value["gaps"] = [message for message in value["gaps"] if message != OWNERSHIP_GAP]
            if value["ownership_gaps"]:
                value["gaps"].append(OWNERSHIP_GAP)
            self._save(value)

    def sample(self):
        with self.lock:
            ident = self.active["id"] if self.active else None
        if ident:
            self._capture(ident, self.provider())

    def stop(self):
        with self.operations:
            with self.lock:
                ident = self.active["id"] if self.active else None
            if not ident:
                raise ValueError("No recording is active")
            settlement = None
            if self.bo_capture_flush:
                # The producer worker may need both session and recording locks.
                # Never hold either lock while waiting for the bounded drain.
                try:
                    with bo_internal():
                        completed = self.bo_capture_flush() is True
                    settlement = {"flushed": completed}
                except Exception as error:
                    settlement = {"flushed": False, "error": type(error).__name__}
            self._capture(ident, self.provider())
            with self.lock:
                value = self.cached[ident]
                if value["status"] == "recording":
                    value.update(status="stopped", ended_at=timestamp())
                    if settlement is not None:
                        value["producer_settlement"] = settlement
                        if not settlement["flushed"]:
                            value["status"] = "interrupted"
                            value["gaps"].append(
                                "Producer queue did not drain; only received events are retained."
                            )
                    before = value["context"]["health"].get("producer", {})
                    after = value["final"]["health"].get("producer", {})
                    if settlement is not None and "flush_target" in after:
                        settlement.update(
                            target=after["flush_target"],
                            completed=after.get("queue_completed", 0),
                            submitted=after.get("queue_submitted", 0),
                            pending=after.get("pending", 0),
                        )
                    if any(
                        after.get(key, 0) > before.get(key, 0)
                        for key in ("errors", "dropped", "data_errors")
                    ):
                        value["status"] = "interrupted"
                        value["gaps"].append(
                            "Producer capture or transport failed during this recording."
                        )
                    if (
                        len(value["events"]) + value.get("scope_excluded", 0)
                        != value["end_seq"] - value["start_seq"]
                    ):
                        value["gaps"].append(
                            "Event sequence gaps exist; missing steps were not fabricated."
                        )
                    self.active = None
                    self._save(value)
                return self.summary(value)

    def command(self, action, values, result=None, error=None):
        """Called by the optional HTTP adapter after a command returns."""
        try:
            with self.lock:
                if not self.active:
                    return
                plan = self.active.get("capture", {})
                allowed = plan.get("value_nodes", plan.get("nodes"))
                if allowed is not None and self.action_nodes.get(action) not in allowed:
                    return
                if len(self.active["commands"]) >= 2000:
                    message = "The 2000 operation-marker limit was reached. Later markers were not saved; probe capture continues."
                    if message not in self.active["gaps"]:
                        self.active["gaps"].append(message)
                    return
                self.active["commands"].append(
                    {
                        "id": "command:"
                        + self.active["id"]
                        + ":"
                        + str(len(self.active["commands"]) + 1),
                        "observed_at": timestamp(),
                        "action": action,
                        "node": self.action_nodes.get(action),
                        "values": {
                            k: values[k]
                            for k in self.active.get("command_fields", [])
                            if k in values
                            and isinstance(values[k], (str, int, float, bool, type(None)))
                        },
                        "result": {
                            k: v
                            for k, v in (result or {}).items()
                            if k in self.active.get("command_fields", []) or k == "ok"
                        },
                        "status": "error" if error else "ok",
                        "error": str(error)[:160] if error else None,
                    }
                )
        except Exception:
            self.last_error = "Operation marker could not be saved"

    @staticmethod
    def summary(value):
        return {
            k: value[k] for k in ("id", "label", "status", "started_at", "ended_at", "build_id")
        } | {
            "events": len(value["events"]),
            "commands": len(value["commands"]),
            "gaps": value["gaps"],
            "capture": value.get("capture", {"mode": "all"}),
            "capture_filtered": value.get("capture_filtered", 0),
            "graph_version": graph_version(value["context"]),
        }

    def get(self, ident):
        current = graph_version(self.version_provider())
        with self.lock:
            path = self._path(ident)
            value = self.cached.get(ident)
            if value is None:
                if not path.exists():
                    raise ValueError("Recording not found")
                value = json.loads(path.read_text(encoding="utf-8"))
            if graph_version(value["context"]) != current:
                raise ValueError("This recording belongs to an earlier graph version")
            return deepcopy(value)

    def clear(self, ident):
        """Remove one stopped, current-version recording; leave business data untouched."""
        with self.operations:
            # Never hold the recording lock while reading the application.
            current = graph_version(self.version_provider())
            with self.lock:
                path = self._path(ident)
                if self.active:
                    raise ValueError("Stop recording before clearing a saved record")
                if path.is_symlink() or not path.resolve().is_relative_to(self.directory.resolve()):
                    raise ValueError("Invalid recording path")
                if not path.is_file():
                    raise ValueError("Recording not found")
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("schema") != SCHEMA or value.get("id") != ident:
                    raise ValueError("Invalid recording file")
                if value.get("status") not in {"stopped", "interrupted", "limited"}:
                    raise ValueError("Only stopped recordings can be cleared")
                if graph_version(value["context"]) != current:
                    raise ValueError("This recording belongs to an earlier graph version")
                # On an I/O failure retain the catalog and cache for a safe retry.
                path.unlink()
                self.cached.pop(ident, None)
                self.catalog.pop(ident, None)
                return {"id": ident, "cleared": True}

    def list(self):
        # Read outside the recording lock: a provider may take the application's
        # lock while business operations deliver events back to this recorder.
        current = graph_version(self.version_provider())
        with self.lock:
            stale = (
                self.active["id"]
                if self.active and graph_version(self.active["context"]) != current
                else None
            )
        if stale:
            self._capture(stale, self.provider())
        with self.lock:
            entries = {}
            for path in sorted(
                self.directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                try:
                    if path.stem not in self.catalog:
                        value = json.loads(path.read_text(encoding="utf-8"))
                        if value.get("schema") == SCHEMA:
                            self.catalog[path.stem] = self.summary(value)
                    if self.catalog.get(path.stem, {}).get("graph_version") == current:
                        entries[path.stem] = self.catalog[path.stem]
                        if len(entries) >= 50:
                            break
                except (OSError, ValueError, KeyError):
                    continue
            for ident, value in self.cached.items():
                if graph_version(value["context"]) == current:
                    entries[ident] = self.summary(value)
            return {
                "active": self.summary(self.active) if self.active else None,
                "recordings": sorted(entries.values(), key=lambda v: v["started_at"], reverse=True)[
                    :50
                ],
                "error": self.last_error,
                "graph_version": current,
            }

    def _worker(self):
        while not self.closed.wait(self.interval):
            try:
                self.sample()
            except Exception as error:
                with self.lock:
                    self.last_error = "Sampling failed: " + str(error)[:120]
                    if self.active and self.last_error not in self.active["gaps"]:
                        self.active["gaps"].append(self.last_error)

    def close(self):
        self.closed.set()
        self.worker.join(2)
        try:
            self.sample()
        except Exception as error:
            self.last_error = "Sampling before shutdown failed: " + str(error)[:120]
        if self._unsubscribe:
            self._unsubscribe()
        with self.lock:
            if self.active:
                value = self.active
                value.update(status="interrupted", ended_at=timestamp())
                value["gaps"].append("The application closed before recording completed.")
                self.active = None
                self._save(value)
