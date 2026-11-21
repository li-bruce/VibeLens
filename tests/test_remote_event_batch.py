"""Real HTTP backlogs retain every event and ordered snapshot across both SDKs."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
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

    def test_lost_batch_response_retries_the_group_before_individual_fallback(self):
        """One lost ACK must not turn a committed group into many source-check requests."""
        handler = self.server.RequestHandlerClass
        original = handler.do_POST
        for language in ("python", "node"):
            requests = []
            lost_ids, individual_ids = set(), []
            lost = False
            initial = self.session.sequence
            single = self.session.event

            def individual(value):
                individual_ids.append(value["id"])
                return single(value)

            def respond(request):
                nonlocal lost
                requests.append(request.path)
                if request.path != "/api/bo/events/batch" or lost:
                    return original(request)
                body = json.loads(request.rfile.read(int(request.headers["Content-Length"])))
                lost_ids.update(value["id"] for value in body["events"])
                self.session.bo_sink.bo_accept_many(body["events"])
                lost = True
                request.close_connection = True
                request.connection.shutdown(socket.SHUT_RDWR)
                request.connection.close()

            with (
                self.subTest(language=language),
                patch.object(handler, "do_POST", respond),
                patch.object(self.session, "event", side_effect=individual),
            ):
                result = self.produce(language)
                self.assertTrue(lost)
                self.assertTrue(result["flushed"])
                self.assertEqual(result["health"]["errors"], 0)
                # The lost group's original IDs must retry as a group. A later
                # singleton at a snapshot barrier is legitimate ordinary traffic,
                # regardless of thread scheduling or the chosen batch byte limit.
                self.assertFalse(lost_ids.intersection(individual_ids), individual_ids)
                self.assertEqual(result["health"]["transport_retries"], 1)
                self.assertEqual(
                    [event["id"] for event in self.session.history.snapshot()[initial:]],
                    result["ids"],
                )

    def test_two_lost_group_receipts_recover_in_ordered_subgroups(self):
        """Repeated ACK loss must not fan a large committed group into singleton requests."""
        handler = self.server.RequestHandlerClass
        original = handler.do_POST
        for language in ("python", "node"):
            lost_ids, singles, recovered = set(), set(), []
            losses = 0
            initial = self.session.sequence

            def respond(request):
                nonlocal losses
                if request.path not in {"/api/bo/events", "/api/bo/events/batch"}:
                    return original(request)
                body = json.loads(request.rfile.read(int(request.headers["Content-Length"])))
                if request.path.endswith("/events"):
                    singles.add(body["id"])
                    return request.reply(200, self.session.event(body))
                values = body["events"]
                ids = {value["id"] for value in values}
                receipts = self.session.bo_sink.bo_accept_many(values)
                if (not lost_ids and len(values) >= 4) or (ids == lost_ids and losses < 2):
                    lost_ids.update(ids)
                    losses += 1
                    request.close_connection = True
                    request.connection.shutdown(socket.SHUT_RDWR)
                    request.connection.close()
                    return
                if ids < lost_ids:
                    recovered.append(ids)
                return request.reply(200, receipts)

            with self.subTest(language=language), patch.object(handler, "do_POST", respond):
                result = self.produce(language)
                self.assertEqual(losses, 2)
                self.assertTrue(result["flushed"])
                self.assertEqual(result["health"]["errors"], 0)
                self.assertEqual(result["health"]["pending"], 0)
                self.assertFalse(lost_ids & singles)
                self.assertEqual(set().union(*recovered), lost_ids)
                self.assertEqual(
                    [event["id"] for event in self.session.history.snapshot()[initial:]],
                    result["ids"],
                )

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

    def test_lost_snapshot_response_retries_the_same_frame(self):
        """Transport recovery cannot fabricate another revision or advance past its barrier."""
        handler = self.server.RequestHandlerClass
        original = handler.do_POST
        for language in ("python", "node"):
            lost = False
            initial = self.session.sequence
            previous_frames = len(self.session.frames)

            def respond(request):
                nonlocal lost
                if request.path != "/api/bo/snapshots" or lost:
                    return original(request)
                body = json.loads(request.rfile.read(int(request.headers["Content-Length"])))
                self.assertTrue(self.session.snapshot(body)["accepted"])
                lost = True
                request.close_connection = True
                request.connection.shutdown(socket.SHUT_RDWR)
                request.connection.close()

            with self.subTest(language=language), patch.object(handler, "do_POST", respond):
                result = self.produce(language)
                self.assertTrue(lost)
                self.assertTrue(result["flushed"])
                self.assertEqual(result["health"]["errors"], 0)
                self.assertEqual(result["health"]["transport_retries"], 1)
                self.assertEqual(len(self.session.frames), previous_frames + 1)
                self.assertEqual(
                    [event["id"] for event in self.session.history.snapshot()[initial:]],
                    result["ids"],
                )

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

    def test_stop_prioritizes_real_admission_over_display_scans_and_sampling(self):
        """A pending drain yields viewer work while new facts remain admissible."""
        recordings = self.session.recordings
        recordings.start("Settlement scheduling")
        entered, release, reader_entered = threading.Event(), threading.Event(), threading.Event()
        original_wait = recordings.wait_for_settlement

        def settle():
            entered.set()
            if not release.wait(5):
                raise TimeoutError("Test settlement was not released")
            return True

        def wait():
            reader_entered.set()
            return original_wait()

        recordings.bo_capture_flush = settle
        values = self.envelopes()
        with ThreadPoolExecutor(max_workers=2) as pool:
            stopping = pool.submit(recordings.stop)
            try:
                self.assertTrue(entered.wait(2))
                with (
                    patch.object(recordings, "wait_for_settlement", side_effect=wait),
                    patch.object(
                        self.session.web,
                        "structure_context",
                        wraps=self.session.web.structure_context,
                    ) as scan,
                ):
                    reading = pool.submit(self.session.view)
                    self.assertTrue(reader_entered.wait(2))
                    self.assertEqual(scan.call_count, 0)
                    with patch.object(
                        recordings, "provider", side_effect=AssertionError("Competing checkpoint")
                    ):
                        recordings.sample()
                    receipts = self.post({"protocol": "bo-event-batch/v1", "events": values})
                    self.assertTrue(all(receipt["accepted"] for receipt in receipts))
                    release.set()
                    self.assertEqual(stopping.result(timeout=5)["status"], "stopped")
                    view = reading.result(timeout=5)
                    self.assertEqual(scan.call_count, 1)
                    self.assertEqual(
                        [event["id"] for event in view["events"]], [event["id"] for event in values]
                    )
            finally:
                release.set()
        self.assertTrue(recordings.settlement_done.is_set())

    def test_failed_settlement_releases_readers_and_retains_the_capture_gap(self):
        recordings = self.session.recordings
        identifier = recordings.start("Failed settlement")["id"]
        with patch.object(recordings, "bo_capture_flush", side_effect=TimeoutError("Offline")):
            stopped = recordings.stop()
        self.assertEqual(stopped["status"], "interrupted")
        self.assertTrue(recordings.settlement_done.is_set())
        record = recordings.get(identifier)
        self.assertEqual(record["producer_settlement"], {"flushed": False, "error": "TimeoutError"})
        self.assertIn(
            "Producer queue did not drain; only received events are retained.", record["gaps"]
        )
        self.assertEqual(recordings.list()["active"], None)

    def test_batch_budget_is_separate_from_the_single_envelope_budget(self):
        """A legal group can exceed 24 KiB without accepting an oversized event."""
        template = self.envelopes()[0]
        values = []
        for index in range(64):
            event = deepcopy(template)
            event.update(id=f"bounded-group:{index}", seq=index + 1)
            event["basis"] = {"diagnostic_text": "值" * 400}
            values.append(event)
        self.assertGreater(len(json.dumps(values, ensure_ascii=False).encode()), 24576)
        receipts = self.post({"protocol": "bo-event-batch/v1", "events": values})
        self.assertEqual(len(receipts), 64)
        self.assertEqual(self.session.sequence, 64)
        large = [dict(value, basis={"diagnostic_text": "x" * 23000}) for value in values[:12]]
        with self.assertRaises(HTTPError) as error:
            self.post({"protocol": "bo-event-batch/v1", "events": large})
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(json.load(error.exception), {"error": "invalid payload size"})
        self.assertEqual(self.session.sequence, 64)
        oversized = deepcopy(values[0])
        oversized.update(id="too-large", seq=65, basis={"diagnostic_text": "x" * 24576})
        for path, body in (
            ("events", oversized),
            ("events/batch", {"protocol": "bo-event-batch/v1", "events": [oversized]}),
        ):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                self.post(body, path=path)
            self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.session.sequence, 64)

    def test_both_producers_use_bounded_large_groups_for_realistic_envelopes(self):
        """Source validation is amortized over envelopes carrying actual-size context."""
        handler = self.server.RequestHandlerClass
        original = handler.do_POST
        for language in ("python", "node"):
            sizes = []

            def observe(request):
                if request.path == "/api/bo/events/batch":
                    sizes.append(int(request.headers["Content-Length"]))
                return original(request)

            initial = self.session.sequence
            with self.subTest(language=language), patch.object(handler, "do_POST", observe):
                result = self.produce(language, padding=1600)
            self.assertTrue(result["flushed"])
            self.assertEqual(result["health"]["errors"], 0)
            self.assertTrue(any(size > 24576 for size in sizes), sizes)
            self.assertTrue(all(size <= 256 * 1024 for size in sizes), sizes)
            self.assertEqual(
                [event["id"] for event in self.session.history.snapshot()[initial:]], result["ids"]
            )

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

    def produce(self, language, *, padding=0):
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
                const options=data.padding ? {basis:{diagnostic_text:'x'.repeat(data.padding)}} : {};
                for(let i=0;i<80;i++) ids.push(p.record('advance','return',()=>({outputs:{state:'running'}}), options));
                const evidence=p.record('advance','change',()=>({outputs:{state:'pending'}}),
                    {entity:'node-item',attempt:'node-item',scope:'entity',revision:1});
                ids.push(evidence);
                p.snapshot('node-item','pending',{slots:1},1,evidence);
                for(let i=0;i<40;i++) ids.push(p.record('advance','return',()=>({outputs:{state:'running'}}), options));
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
                        "padding": padding,
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
                probe.record(
                    "advance",
                    "return",
                    lambda: {"outputs": {"state": "running"}},
                    **({"basis": {"diagnostic_text": "x" * padding}} if padding else {}),
                )
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
                probe.record(
                    "advance",
                    "return",
                    lambda: {"outputs": {"state": "running"}},
                    **({"basis": {"diagnostic_text": "x" * padding}} if padding else {}),
                )
                for _ in range(40)
            ]
            return {"ids": ids, "flushed": probe.flush(10), "health": probe.bo_health()}
        finally:
            probe.close()


if __name__ == "__main__":
    unittest.main()
