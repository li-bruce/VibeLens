"""Explanation evidence, concurrency and provider boundaries stay outside execution."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.concepts import bind_projection
from bo_observer.explanations.context import packet, revision, validate_answer
from bo_observer.explanations.providers import HTTPProvider
from bo_observer.explanations.service import Explanations
from bo_observer.observation.observation_scope import bo_is_internal, observer_route
from bo_observer.web.bo_web import BOWeb
from test_concept_models import bound_fixture


def fixture():
    document, model, acceptance = bound_fixture()
    return {
        "layout_id": "synthetic-sharing",
        "model": model,
        "concept_structure": bind_projection(document, model, acceptance=acceptance),
        "manifest": {
            "build_id": "build-1",
            "model_hash": "native-1",
            "bindings": {
                "native:share": {
                    "path": "sharing.py",
                    "symbol": "share",
                    "snippet": "def share(): pass",
                    "file_sha256": "verified",
                }
            },
        },
        "events": [{"inputs": {"secret": "DO-NOT-TRANSFER"}}],
        "authority": {"parameters": {"token": "DO-NOT-TRANSFER"}},
    }


class Provider:
    name = "test-contract"

    def __init__(self):
        self.started, self.release = threading.Event(), threading.Event()
        self.calls = []

    def __call__(self, context):
        self.calls.append(context)
        self.internal = bo_is_internal()
        self.started.set()
        self.release.wait(2)
        return {
            "node_id": context["node"]["id"],
            "text": "Synthetic adapter response",
            "evidence": [context["node"]["id"]],
        }


class ExplanationTests(unittest.TestCase):
    def test_concurrent_tabs_share_the_first_provider_registry(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            web = BOWeb(folder)
            web.control_view = fixture

            def configure(view):
                time.sleep(0.03)
                return Explanations(view, Provider())

            with patch.object(Explanations, "configured", side_effect=configure) as create:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    replies = list(executor.map(web.explanation_reply, ["/api/explanations"] * 2))
                self.assertEqual(create.call_count, 1)
                self.assertEqual(replies[0], replies[1])
            web.close()

    def test_packet_is_layer_specific_and_has_no_runtime_values(self):
        view = fixture()
        before = deepcopy(view)
        business = packet(view, "share", "zh-CN")
        state = packet(view, "state:grant:active")
        self.assertEqual(business["node"]["layer"], "business")
        self.assertEqual(state["node"]["layer"], "state")
        self.assertTrue(any(e["type"] == "action_requests_event" for e in business["relations"]))
        self.assertEqual(business["sources"][0]["symbol"], "share")
        self.assertNotIn("DO-NOT-TRANSFER", json.dumps(business))
        self.assertEqual(view, before)

    def test_provider_cannot_choose_graph_content_or_invent_evidence_ids(self):
        context = packet(fixture(), "share")
        for answer in (
            {"node_id": "another", "text": "wrong", "evidence": ["share"]},
            {"node_id": "share", "text": "wrong", "evidence": ["invented"]},
            {"node_id": "share", "text": "wrong", "evidence": []},
            {"node_id": "share", "text": "wrong", "evidence": ["share"], "commands": []},
        ):
            with self.assertRaises(ValueError):
                validate_answer(answer, context)
        with self.assertRaises(ValueError):
            packet(fixture(), "../../secrets")

    def test_api_packet_includes_declared_route_without_request_credentials(self):
        view = fixture()
        view["api_structure"] = {
            "nodes": [
                {
                    "id": "route:download",
                    "kind": "function",
                    "code_role": "endpoint",
                    "api": {
                        "methods": ["GET"],
                        "path": "/files/{id}",
                        "headers": {"Authorization": "PRIVATE-HEADER"},
                    },
                }
            ],
            "edges": [],
        }
        result = packet(view, "route:download")
        self.assertEqual(result["node"]["api"], {"methods": ["GET"], "path": "/files/{id}"})
        self.assertNotIn("PRIVATE-HEADER", json.dumps(result))

    def test_registered_fields_can_be_explained_without_inventing_source_variables(self):
        result = packet(fixture(), "field:native:context:out:active")
        self.assertEqual(result["node"]["value_type"], "boolean")
        self.assertEqual(result["node"]["event_node"], "native:context")
        self.assertNotIn("source", result["node"])
        with self.assertRaises(ValueError):
            packet(fixture(), "field:native:context:out:invented")

    def test_jobs_are_deduplicated_bounded_stale_checked_and_internal(self):
        view, provider = fixture(), Provider()
        service = Explanations(lambda: view, provider)
        request = {"node": "share", "revision": revision(view), "language": "en"}
        first = service.start(request)
        self.assertTrue(provider.started.wait(1))
        self.assertEqual(service.start(request)["id"], first["id"])
        with self.assertRaises(ValueError):
            service.start({**request, "node": "read"})
        with self.assertRaises(ValueError):
            service.start({**request, "prompt": "run business code"})
        provider.release.set()
        for _ in range(100):
            result = service.get(first["id"])
            if result["status"] != "running":
                break
            time.sleep(0.01)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(provider.internal)
        self.assertEqual(len(provider.calls), 1)
        view["concept_structure"]["revision"] = "new-definition"
        self.assertEqual(service.get(first["id"])["status"], "stale")
        self.assertNotIn("answer", service.get(first["id"]))
        with self.assertRaises(ValueError):
            service.start(request)
        service.close()

    def test_retired_jobs_do_not_reappear(self):
        view, provider = fixture(), Provider()
        clock = [0]
        service = Explanations(lambda: view, provider, clock=lambda: clock[0])
        job = service.start({"node": "share", "revision": revision(view), "language": "en"})
        self.assertTrue(provider.started.wait(1))
        service.close()
        provider.release.set()
        self.assertEqual(service.jobs, {})
        with self.assertRaises(ValueError):
            service.get(job["id"])

    def test_failed_provider_is_retryable_without_disclosing_details(self):
        class FailedProvider:
            name = "failed-contract"

            def __call__(self, context):
                raise RuntimeError("PRIVATE-ACCOUNT-DETAIL")

        view, clock = fixture(), [0]
        service = Explanations(lambda: view, FailedProvider(), clock=lambda: clock[0])
        request = {"node": "share", "revision": revision(view), "language": "en"}
        job = service.start(request)
        for _ in range(100):
            result = service.get(job["id"])
            if result["status"] != "running":
                break
            time.sleep(0.01)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("PRIVATE-ACCOUNT-DETAIL", json.dumps(result))
        retry = service.start(request)
        self.assertNotEqual(retry["id"], job["id"])
        clock[0] = 601
        with self.assertRaises(ValueError):
            service.get(retry["id"])
        service.close()

    def test_remote_endpoint_configuration_and_self_observation_exclusion(self):
        self.assertTrue(observer_route("/api/explanations?job=abc"))
        self.assertFalse(observer_route("/api/explanations-business"))
        for endpoint in (
            "http://remote.example/v1/chat/completions",
            "file:///tmp/key",
            "https://key:secret@example.com",
        ):
            with self.assertRaises(ValueError):
                HTTPProvider(endpoint, "model")
        self.assertEqual(
            HTTPProvider("http://127.0.0.1:9100/v1/chat/completions", "local").name, "http"
        )


if __name__ == "__main__":
    unittest.main()
