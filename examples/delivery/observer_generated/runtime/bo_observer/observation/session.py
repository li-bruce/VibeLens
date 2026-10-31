"""Build-scoped observation session, event admission and retained runtime frames.

The native application owns execution. This module validates observations and
assembles read-only views; HTTP transport and reload borrowing live in service.py.
"""

from collections import OrderedDict
from copy import deepcopy
import json
from pathlib import Path
import secrets
import threading
from ..protocol import validate_project, validate_event, validate_snapshot
from ..graph.source_files import SourceFiles
from .event_batch import BOSessionSink

try:
    from ...behavior_model import read, capture, check, contained, digest
    from ...bo_stategraph import BOStateGraph
    from ...bo_retention import EventHistory
    from ...view_preferences import Preferences
    from ...recording_session import Recordings
    from ...bo_web import BOWeb
except ImportError:
    from behavior_model import read, capture, check, contained, digest
    from bo_stategraph import BOStateGraph
    from bo_retention import EventHistory
    from view_preferences import Preferences
    from recording_session import Recordings
    from bo_web import BOWeb


class GraphSession:
    """Own one observed build and its evidence; never execute application commands."""

    def __init__(self, root, project_path="bo_stategraph/project.json"):
        """Load one project/build and prepare its bounded event history and recording service."""
        self.root = Path(root).absolute().resolve()
        self.path = contained(self.root, project_path)
        self.project = validate_project(read(self.path))
        self.project_hash = digest(self.project)
        self.bo_project_sources = SourceFiles(self.root)
        self.bo_project_content_hash = None
        self.bo_sink = BOSessionSink(self)
        self.model = self.project["model"]
        self.manifest = capture(self.root, self.model)
        self.graph = BOStateGraph(
            self.model,
            build_id=self.manifest["build_id"],
            mode=self.project["selection"]["mode"],
        )
        self.lock = threading.RLock()
        self.sequence = 0
        self.producers = {}
        self.seen = OrderedDict()
        self.owners = {}
        self.identities = {}
        self.current_instance = None
        self.program_url = None
        self.data_status = None
        self.errors = self.gaps = 0
        self.last_error = ""
        self.bo_producer_health = None
        self.stream_id = secrets.token_hex(12)
        self.frames = OrderedDict()
        self.frame_bytes = 0
        self.frame_evictions = 0
        self.history = EventHistory(
            project_root=self.root, path=self.root / "bo_stategraph/data/events.jsonl"
        )
        self.preferences = Preferences(self.root, self.project["project_id"])
        self.web = BOWeb(self.root)
        self.recordings = Recordings(
            self.root / "bo_stategraph/data/recordings",
            self.view,
            self.sources(),
            event_source=self.history,
        )

    def bo_bind_capture(self, *, scope_setter, flush_capture, health):
        """Connect an observer controller; callbacks cannot execute business actions.

        The native application supplies bounded queue draining, temporary owner
        selection and read-only producer health. A remote-language bridge can
        implement the same callbacks. Register before serving application work.
        """
        if not all(callable(callback) for callback in (scope_setter, flush_capture, health)):
            raise ValueError("capture controller needs scope, bounded flush and health callbacks")
        with self.recordings.lock:
            if self.recordings.active:
                raise ValueError("cannot replace a capture controller during recording")
            self.recordings.bo_scope_setter = scope_setter
            self.recordings.bo_capture_flush = flush_capture
            self.bo_producer_health = health

    def sources(self):
        """Read the source files bound to this build for later source lookup and recordings."""
        return {
            name: contained(self.root, name).read_text(encoding="utf-8")
            for name in self.manifest["files"]
        }

    def binding(self):
        """Report whether current source bytes still match the loaded build."""
        status = check(self.root, self.model, self.manifest)
        try:
            # Read actual bytes every time. Only already verified identical bytes
            # may skip JSON parsing; same-size/same-mtime edits still get checked.
            # Changed formatting is compared canonically, as before this fast path.
            raw = self.bo_project_sources.read(self.path.relative_to(self.root))
            content_hash = digest(raw) if raw is not None else None
            if raw is None or (
                content_hash != self.bo_project_content_hash
                and digest(json.loads(raw.decode("utf-8-sig"))) != self.project_hash
            ):
                status.update(status="stale", project_changed=True)
            else:
                self.bo_project_content_hash = content_hash
        except (OSError, ValueError):
            status.update(status="stale", project_changed=True)
        return status

    def event(self, event):
        """Validate and append one producer event, preserving its original identity.

        The collector sequence is a display order. Producer sequences and dependency
        IDs remain the evidence for gaps and causal links.
        """
        value = validate_event(event, self.project, self.manifest["build_id"])
        with self.lock:
            if self.binding()["status"] != "current":
                raise ValueError("source or declaration changed; reload after verification")
            return self._accept_event(value)

    def _accept_event(self, value):
        """Advance one validated cursor; the caller holds the lock and source boundary.

        Event batches use this same reducer on a detached cursor before the real
        commit. Keep its mutations confined to seen, producers, sequence, gaps and
        history so invalid preflight cannot leak into the live graph or recorder.
        """
        signature = digest(value)
        producer = (value["run_id"], value["producer_id"])
        if value["id"] in self.seen:
            if self.seen[value["id"]]["digest"] != signature:
                raise ValueError("event identity collision")
            return {"accepted": True, "duplicate": True}
        if producer not in self.producers and len(self.producers) >= 1024:
            raise ValueError("producer limit reached")
        prior = self.producers.get(producer, 0)
        if value["seq"] <= prior:
            raise ValueError("old or reordered producer sequence")
        if value["seq"] != prior + 1:
            self.gaps += value["seq"] - prior - 1
        for ref in value["depends"]:
            previous = self.seen.get(ref["event"])
            if previous is None:
                self.gaps += 1
                continue
            if previous["run_id"] != value["run_id"]:
                raise ValueError("cross-run dependency")
        self.sequence += 1
        stored = {
            **value,
            "source_seq": value["seq"],
            "seq": self.sequence,
            "stream_id": self.stream_id,
        }
        self.producers[producer] = value["seq"]
        self.seen[value["id"]] = {
            "digest": signature,
            "run_id": value["run_id"],
            "producer_id": value["producer_id"],
            "entity": value["entity"],
            "attempt": value["attempt"],
            "revision": value.get("revision"),
        }
        while len(self.seen) > 10000:
            self.seen.popitem(last=False)
        self.history.append(stored)
        return {"accepted": True, "receipt_seq": self.sequence}

    def snapshot(self, value):
        """Attach an application snapshot to its matching recorded event.

        Reject stale revisions, conflicting instance owners, and cross-run evidence
        before updating the graph; retain bounded before/after frames for replay.
        """
        value = validate_snapshot(value, self.project, self.manifest["build_id"])
        with self.lock:
            if self.binding()["status"] != "current":
                raise ValueError("source or declaration changed")
            evidence = self.seen.get(value["evidence_id"])
            if not evidence or (evidence["run_id"], evidence["producer_id"]) != (
                value["run_id"],
                value["producer_id"],
            ):
                raise ValueError("snapshot lacks a matching recorded event")
            if evidence["revision"] != value["revision"]:
                raise ValueError("snapshot needs the same explicit state revision as its event")
            ident = value["run_id"] + ":" + value["instance_id"]
            owner = value["producer_id"]
            if ident in self.owners and self.owners[ident] != owner:
                raise ValueError("instance already has another authoritative producer")
            if ident not in self.owners and len(self.owners) >= 1024:
                raise ValueError("instance limit reached")
            if evidence.get("snapshot_instance") not in (None, ident):
                raise ValueError("event already belongs to another instance snapshot")
            previous = next(
                (
                    i["observed"]
                    for i in self.graph.bo_instances()
                    if i["observed"]["instance_id"] == ident
                ),
                None,
            )
            result = self.graph.bo_observe(
                ident,
                **{
                    k: value[k]
                    for k in (
                        "state",
                        "context",
                        "revision",
                        "evidence_id",
                        "build_id",
                        "configuration",
                        "event",
                        "guards",
                        "payload",
                    )
                },
            )
            if result["accepted"]:
                self.owners[ident] = owner
                self.identities[ident] = {
                    "entity": evidence["entity"],
                    "attempt": evidence["attempt"],
                }
                self.current_instance = ident
                evidence["snapshot_instance"] = ident
                if not result.get("duplicate"):
                    cfg = deepcopy(
                        value.get("configuration")
                        or {
                            "attempt": evidence["attempt"],
                            "phase": value["state"],
                            "param_version": value["revision"],
                            "activities": {},
                            "resources": {},
                            "journal": [],
                        }
                    )
                    journal = []
                    if previous and value["event"]:
                        transition = {
                            "event": value["event"],
                            "source": previous["state"],
                            "target": value["state"],
                            "attempt": evidence["attempt"],
                            "evidence_id": value["evidence_id"],
                            "revision": value["revision"],
                        }
                        cfg["state_transition"] = transition
                        journal = [transition]
                    frame = {
                        "event_id": value["evidence_id"],
                        "run_id": value["run_id"],
                        "build_id": value["build_id"],
                        "revision": value["revision"],
                        "machine": {
                            "current": value["state"],
                            "state_revision": value["revision"],
                            "configurations": [cfg],
                            "journal": journal,
                        },
                        "authority": {
                            "entity": evidence["entity"],
                            "state": value["state"],
                            "basis": {},
                            "parameters": {
                                **deepcopy(value["context"]),
                                "attempt": evidence["attempt"],
                            },
                        },
                    }
                    size = len(json.dumps(frame, ensure_ascii=False, allow_nan=False).encode())
                    self.frames[value["evidence_id"]] = (frame, size)
                    self.frame_bytes += size
                    while len(self.frames) > 2000 or self.frame_bytes > 16 * 1024 * 1024:
                        _, (_, removed) = self.frames.popitem(last=False)
                        self.frame_bytes -= removed
                        self.frame_evictions += 1
            return result

    def view(self):
        """Assemble one consistent viewer snapshot from the graph and retained runtime evidence."""
        with self.lock:
            instances = self.graph.bo_instances()
            current = next(
                (
                    i["observed"]
                    for i in instances
                    if i["observed"]["instance_id"] == self.current_instance
                ),
                {},
            )
            configurations = []
            for entry in instances:
                o = entry["observed"]
                configurations.append(
                    o.get("configuration")
                    or {
                        "attempt": self.identities[o["instance_id"]]["attempt"],
                        "phase": o["state"],
                        "param_version": o["revision"],
                        "activities": {},
                        "resources": {},
                        "journal": [],
                    }
                )
            model = deepcopy(self.model)
            model.setdefault("presentation", {}).setdefault("subject", self.project["project_id"])
            model["machine"].setdefault("labels", {s: s for s in model["machine"]["values"]})
            health = self.history.health()
            producer = self.bo_producer_health() if self.bo_producer_health else None
            current_frame = self.frames.get(current.get("evidence_id"), (None, 0))[0]
            return {
                "stage": "runtime",
                "program_url": self.program_url,
                "layout_id": self.project["project_id"],
                "model": model,
                "manifest": deepcopy(self.manifest),
                "binding_status": self.binding(),
                "events": self.current_events(),
                "database_status": self.data_status,
                "machine": {
                    "current": current.get("state"),
                    "state_revision": current.get("revision"),
                    "configurations": configurations,
                    "journal": (
                        deepcopy(current_frame["machine"]["journal"]) if current_frame else []
                    ),
                },
                "runtime_frames": {
                    "schema": "stategraph-runtime-frames/v1",
                    "partial": True,
                    "frames": [deepcopy(f) for f, _ in self.frames.values()],
                },
                "authority": {
                    "entity": self.identities.get(current.get("instance_id"), {}).get("entity"),
                    "state": current.get("state"),
                    "basis": {},
                    "parameters": {
                        **current.get("context", {}),
                        "attempt": self.identities.get(current.get("instance_id"), {}).get(
                            "attempt"
                        ),
                    },
                },
                "health": {
                    "errors": self.errors + health["log_errors"],
                    # Live history expiry is reported separately. Recording listeners
                    # already received those events, so expiry is not a capture gap.
                    "dropped": self.gaps,
                    "run_id": self.stream_id,
                    "attempted": self.sequence,
                    "written": self.sequence,
                    "enabled": producer["enabled"] if producer is not None else True,
                    **({"producer": producer} if producer is not None else {}),
                    "runtime_frame_evictions": self.frame_evictions,
                    **health,
                },
                "busy": False,
                "historical": False,
                "available_cases": ["live"],
                "instances": instances,
            }

    def export(self):
        """Return the complete declared graph with retained events and matching runtime frames."""
        with self.lock:
            events = self.current_events()
            ids = {e["id"] for e in events}
            return self.graph.bo_export(
                binding=self.binding(),
                runtime={
                    "events": events,
                    "runtime_frames": {
                        "schema": "stategraph-runtime-frames/v1",
                        "partial": True,
                        "frames": [
                            deepcopy(f) for key, (f, _) in self.frames.items() if key in ids
                        ],
                    },
                },
            )

    def current_events(self):
        """Keep prior build evidence out of the live graph after source or schema changes."""
        return [
            e for e in self.history.snapshot() if e.get("build_id") == self.manifest["build_id"]
        ]

    def close(self):
        """Stop the recording worker and its subscriptions during server shutdown."""
        self.recordings.close()
