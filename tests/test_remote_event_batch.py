"""Real HTTP backlogs retain every event and ordered snapshot across both SDKs."""

from copy import deepcopy
import json
from http.client import HTTPResponse
import queue
from pathlib import Path
import subprocess
import sys
import socket
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.service import GraphSession, make_server


class RemoteEventBatchTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.token = "synthetic-batch-test"
        self.server = make_server(self.session, port=0, token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.folder.cleanup()

    def post(self, body, path="events/batch", token=None):
        request = Request(
            self.base + "/api/bo/" + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-BO-Token": token or self.token},
        )
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def envelopes(self):
        values = []
        probe = BOProbe(
            self.project,
            self.session.manifest["build_id"],
            sink=lambda value, kind: values.append(value),
        )
        try:
            for _ in range(3):
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            self.assertTrue(probe.flush(2))
        finally:
            probe.close()
        return values

    def test_http_batch_is_atomic_and_preserves_duplicate_receipts(self):
        values = self.envelopes()
        invalid = deepcopy(values)
        invalid[-1]["node"] = "missing"
        with self.assertRaises(HTTPError) as error:
            self.post({"protocol": "bo-event-batch/v1", "events": invalid})
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.session.sequence, 0)
        receipts = self.post({"protocol": "bo-event-batch/v1", "events": values})
        self.assertEqual(len(receipts), 3)
        self.assertTrue(all(value["accepted"] for value in receipts))
        duplicate = self.post({"protocol": "bo-event-batch/v1", "events": values})
        self.assertTrue(all(value["duplicate"] for value in duplicate))
        self.assertEqual(self.session.sequence, 3)
        with self.assertRaises(HTTPError) as error:
            self.post({}, token="wrong")
        self.assertEqual(error.exception.code, 403)

    def test_both_http_producers_amortize_checks_without_crossing_snapshots(self):
        for language in ("python", "node"):
            with self.subTest(language=language):
                initial = self.session.sequence
                batches, barriers = [], []
                accept = self.session.bo_sink.bo_accept_many
                snapshot = self.session.snapshot

                def receive(values):
                    batches.append([value["id"] for value in values])
                    return accept(values)

                def receive_snapshot(value):
                    result = snapshot(value)
                    barriers.append(self.session.sequence)
                    return result

                with (
                    patch.object(self.session.bo_sink, "bo_accept_many", side_effect=receive),
                    patch.object(self.session, "snapshot", side_effect=receive_snapshot),
                    patch.object(self.session, "binding", wraps=self.session.binding) as binding,
                ):
                    result = self.produce(language)
                expected = result["ids"]
                observed = self.session.history.snapshot()[initial:]
                self.assertTrue(result["flushed"])
                self.assertEqual(result["health"]["errors"], 0)
                self.assertEqual(result["health"]["pending"], 0)
                self.assertEqual([value["id"] for value in observed], expected)
                self.assertEqual(barriers, [initial + 81])
                self.assertTrue(any(len(batch) > 1 for batch in batches))
                self.assertTrue(all(len(batch) <= 64 for batch in batches))
                self.assertLess(binding.call_count, len(expected) // 2)

    def test_legacy_collectors_fall_back_without_losing_facts(self):
        self.check_fallback(legacy=True)

    def test_ambiguous_batch_receipts_retry_original_ids_without_duplicates(self):
        self.check_fallback(legacy=False)

    def check_fallback(self, *, legacy):
        """Exercise legacy HTTP and a lost receipt after actual atomic admission."""
        handler = self.server.RequestHandlerClass
        original = handler.do_POST
        batches = []
        session = self.session

        def respond(request):
            if request.path != "/api/bo/events/batch":
                return original(request)
            raw = request.rfile.read(int(request.headers["Content-Length"]))
            body = json.loads(raw)
            batches.append(len(body["events"]))
            if legacy:
                return request.reply(405, {"error": "not supported"})
            session.bo_sink.bo_accept_many(body["events"])
            # A proxy can lose the valid receipt after the collector commits.
            return request.reply(200, {"unexpected": "receipt"})

        with patch.object(handler, "do_POST", respond):
            for language in ("python", "node"):
                initial = self.session.sequence
                attempts = len(batches)
                result = self.produce(language)
                self.assertTrue(result["flushed"])
                self.assertEqual(result["health"]["errors"], 0)
                self.assertEqual(result["health"]["pending"], 0)
                self.assertEqual(
                    [value["id"] for value in self.session.history.snapshot()[initial:]],
                    result["ids"],
                )
                if legacy:
                    self.assertEqual(len(batches) - attempts, 1)

    def test_byte_limit_and_batch_shape_are_strict(self):
        values = self.envelopes()
        for body in (
            {"protocol": "wrong", "events": values},
            {"protocol": "bo-event-batch/v1", "events": []},
            {"protocol": "bo-event-batch/v1", "events": values, "extra": True},
            {"protocol": "bo-event-batch/v1", "events": values * 22},
        ):
            with self.assertRaises(HTTPError) as error:
                self.post(body)
            self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.session.sequence, 0)

    def test_changed_source_rejects_whole_http_batch(self):
        values = self.envelopes()
        with (self.root / "worker.py").open("a", encoding="utf-8") as stream:
            stream.write("\n# Different current source bytes\n")
        with self.assertRaises(HTTPError) as error:
            self.post({"protocol": "bo-event-batch/v1", "events": values})
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.session.sequence, 0)

    def test_rejected_small_bodies_return_complete_receipts_repeatedly(self):
        for _ in range(40):
            with self.assertRaises(HTTPError) as error:
                self.post({}, token="wrong")
            with error.exception as response:
                self.assertEqual(response.code, 403)
                self.assertEqual(response.headers["Connection"], "close")
                self.assertEqual(json.load(response), {"error": "origin or collector token denied"})
        self.assertEqual(self.session.sequence, 0)
        self.assertTrue(
            all(
                row["accepted"]
                for row in self.post({"protocol": "bo-event-batch/v1", "events": self.envelopes()})
            )
        )

    def test_rejection_is_sent_before_an_incomplete_body_arrives(self):
        with socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=2
        ) as connection:
            headers = (
                "POST /api/bo/events/batch HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.server.server_port}\r\n"
                "X-BO-Token: wrong\r\nContent-Length: 2\r\n\r\n"
            )
            connection.sendall(headers.encode())
            response = HTTPResponse(connection)
            response.begin()
            self.assertEqual(response.status, 403)
            self.assertEqual(
                json.loads(response.read()), {"error": "origin or collector token denied"}
            )
            response.close()
        self.assertEqual(self.session.sequence, 0)

    def test_flush_prefix_finishes_while_later_http_work_is_blocked(self):
        """Continued business traffic cannot become part of an earlier stop barrier."""
        for language in ("python", "node"):
            with self.subTest(language=language):
                entered, release = threading.Event(), threading.Event()
                suffix, finish = threading.Event(), threading.Event()
                accept = self.session.bo_sink.bo_accept_many
                single = self.session.event
                result = queue.Queue()
                process = probe = waiter = None

                def gate(values, callback):
                    if not entered.is_set():
                        entered.set()
                        if not release.wait(5):
                            raise TimeoutError("Initial delivery was not released")
                    if any(value["outputs"].get("state") == "done" for value in values):
                        suffix.set()
                        if not finish.wait(5):
                            raise TimeoutError("Later delivery was not released")
                    return callback()

                with (
                    patch.object(
                        self.session.bo_sink,
                        "bo_accept_many",
                        side_effect=lambda values: gate(values, lambda: accept(values)),
                    ),
                    patch.object(
                        self.session,
                        "event",
                        side_effect=lambda value: gate([value], lambda: single(value)),
                    ),
                ):
                    try:
                        if language == "python":
                            probe = BOProbe(
                                self.project,
                                self.session.manifest["build_id"],
                                endpoint=self.base,
                                token=self.token,
                            )
                            for _ in range(80):
                                probe.record(
                                    "advance", "return", lambda: {"outputs": {"state": "running"}}
                                )
                            self.assertTrue(entered.wait(2))
                            waiter = threading.Thread(target=lambda: result.put(probe.flush(3)))
                            waiter.start()
                            deadline = time.monotonic() + 1
                            while (
                                probe.bo_health()["flush_target"] != 80
                                and time.monotonic() < deadline
                            ):
                                threading.Event().wait(0.001)
                            self.assertEqual(probe.bo_health()["flush_target"], 80)
                            probe.record(
                                "advance", "return", lambda: {"outputs": {"state": "done"}}
                            )
                        else:
                            module = (
                                ROOT
                                / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
                            ).as_uri()
                            options = {
                                "project": self.project,
                                "buildId": self.session.manifest["build_id"],
                                "endpoint": self.base,
                                "token": self.token,
                            }
                            code = f"""
                                import {{BOProbe}} from {json.dumps(module)};
                                const p=new BOProbe({json.dumps(options)});
                                for(let i=0;i<80;i++) p.record('advance','return',()=>({{outputs:{{state:'running'}}}}));
                                const prefix=p.flush(3000);
                                p.record('advance','return',()=>({{outputs:{{state:'done'}}}}));
                                console.log(JSON.stringify(await prefix));
                                await p.flush(5000);
                            """
                            process = subprocess.Popen(
                                ["node", "--input-type=module", "-e", code],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding="utf-8",
                            )
                            waiter = threading.Thread(
                                target=lambda: result.put(json.loads(process.stdout.readline()))
                            )
                            waiter.start()
                            self.assertTrue(entered.wait(2))
                        release.set()
                        self.assertTrue(suffix.wait(3))
                        self.assertTrue(result.get(timeout=1))
                    finally:
                        release.set()
                        finish.set()
                        if probe:
                            probe.flush(3)
                            probe.close()
                        if process:
                            process.wait(timeout=8)
                            process.stdout.close()
                            process.stderr.close()
                        if waiter:
                            waiter.join(3)

    def produce(self, language):
        """Run real adapter code against the collector, without timing thresholds."""
        if language == "node":
            module = (
                ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
            ).as_uri()
            code = """
                import {BOProbe} from MODULE;
                const data = JSON.parse(await new Promise(resolve => {
                    let raw='';process.stdin.on('data',x=>raw+=x);
                    process.stdin.on('end',()=>resolve(raw));
                }));
                const p=new BOProbe({project:data.project,buildId:data.build,endpoint:data.base,token:data.token});
                const ids=[];
                for(let i=0;i<80;i++) ids.push(p.record('advance','return',()=>({outputs:{state:'running'}})));
                const evidence=p.record('advance','change',()=>({outputs:{state:'pending'}}),
                    {entity:'node-item',attempt:'node-item',scope:'entity',revision:1});
                ids.push(evidence);
                p.snapshot('node-item','pending',{slots:1},1,evidence);
                for(let i=0;i<40;i++) ids.push(p.record('advance','return',()=>({outputs:{state:'running'}})));
                const flushed=await p.flush(10000);
                console.log(JSON.stringify({ids,flushed,health:p.bo_health()}));
            """.replace(
                "MODULE", json.dumps(module)
            )
            process = subprocess.run(
                ["node", "--input-type=module", "-e", code],
                input=json.dumps(
                    {
                        "project": self.project,
                        "build": self.session.manifest["build_id"],
                        "base": self.base,
                        "token": self.token,
                    }
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        probe = BOProbe(
            self.project, self.session.manifest["build_id"], endpoint=self.base, token=self.token
        )
        try:
            ids = [
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
                for _ in range(80)
            ]
            evidence = probe.record(
                "advance",
                "change",
                lambda: {"outputs": {"state": "pending"}},
                entity="python-item",
                attempt="python-item",
                scope="entity",
                revision=1,
            )
            ids.append(evidence)
            probe.snapshot("python-item", "pending", {"slots": 1}, 1, evidence)
            ids += [
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
                for _ in range(40)
            ]
            return {"ids": ids, "flushed": probe.flush(10), "health": probe.bo_health()}
        finally:
            probe.close()


if __name__ == "__main__":
    unittest.main()
