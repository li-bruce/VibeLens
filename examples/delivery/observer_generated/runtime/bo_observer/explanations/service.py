"""Bounded background inference with revision-pinned, expiring display results."""

from collections import OrderedDict
from copy import deepcopy
import secrets
import threading
import time

from .context import packet, revision, validate_answer
from .providers import configured_provider
from ..observation.observation_scope import bo_internal


class Explanations:
    """Own display jobs only; no application callback or graph mutation is exposed."""

    def __init__(self, view, provider=None, *, clock=time.monotonic):
        self.view, self.provider, self.clock = view, provider, clock
        self.jobs = OrderedDict()
        self.lock = threading.RLock()
        self.closed = False

    def status(self):
        return {
            "available": self.provider is not None,
            "provider": getattr(self.provider, "name", None),
        }

    @classmethod
    def configured(cls, view):
        return cls(view, configured_provider())

    def start(self, request):
        """Validate server evidence before creating a job; concurrent clicks reuse it."""
        if not isinstance(request, dict) or set(request) != {"node", "revision", "language"}:
            raise ValueError("Explanation needs a node, revision and language")
        current = self.view()
        if request["revision"] != revision(current):
            raise ValueError("Graph changed. Refresh the node details.")
        context = packet(current, request["node"], request["language"])
        with self.lock:
            if self.closed or self.provider is None:
                raise ValueError("No AI explanation provider is connected")
            self._expire()
            for job in self.jobs.values():
                if (
                    all(job[key] == context[key] for key in ("revision", "language"))
                    and job["node"] == request["node"]
                    and job["status"] != "error"
                ):
                    return self._public(job)
            if any(job["status"] == "running" for job in self.jobs.values()):
                raise ValueError("Another node is being explained. Try again shortly.")
            identity = secrets.token_hex(16)
            job = {
                "id": identity,
                "node": request["node"],
                "revision": context["revision"],
                "language": context["language"],
                "provider": self.provider.name,
                "status": "running",
                "created": self.clock(),
            }
            self.jobs[identity] = job
            while len(self.jobs) > 32:
                self.jobs.popitem(last=False)
            threading.Thread(target=self._run, args=(identity, context), daemon=True).start()
            return self._public(job)

    def _run(self, identity, context):
        try:
            with bo_internal():
                answer = validate_answer(self.provider(context), context)
            result = {"status": "complete", "answer": answer}
        except Exception:
            # Provider messages can contain account details or remote payloads.
            # Keep those out of the web response and the business event stream.
            result = {
                "status": "error",
                "error": "AI explanation unavailable. Check the provider and retry.",
            }
        with self.lock:
            if not self.closed and identity in self.jobs:
                self.jobs[identity].update(result)

    def get(self, identity):
        with self.lock:
            self._expire()
            job = self.jobs.get(identity)
            if not job:
                raise ValueError("Explanation expired. Request it again.")
            result = self._public(job)
        if result["revision"] != revision(self.view()):
            return {
                k: v
                for k, v in {**result, "status": "stale"}.items()
                if k not in {"answer", "error"}
            }
        return result

    def _expire(self):
        for key, job in list(self.jobs.items()):
            if self.clock() - job["created"] > 600:
                del self.jobs[key]

    @staticmethod
    def _public(job):
        return deepcopy({k: v for k, v in job.items() if k != "created"})

    def close(self):
        """Discard responses after retirement; provider calls already have deadlines."""
        with self.lock:
            self.closed = True
            self.jobs.clear()
