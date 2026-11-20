"""Keep a cold viewer's parallel module requests out of the TCP retry path."""

from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection, HTTPResponse
from pathlib import Path
import queue
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.service import GraphSession, make_server
from bo_observer.web.bo_web import BOHTTPServer, bo_serve
from test_multilanguage import project_fixture


class ViewerTransportTests(unittest.TestCase):
    def test_design_server_reuses_modules_and_closes_rejected_hosts(self):
        """The source-free design page uses the same asset connection policy."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "discovery.json").write_bytes(
                (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_bytes()
            )
            assets = root / "viewer-assets"
            assets.mkdir()
            (assets / "viewer.js").write_bytes(b"export const design = true;\n")
            servers, errors = queue.Queue(), queue.Queue()

            def construct(address, handler):
                server = BOHTTPServer(address, handler)
                servers.put(server)
                return server

            def serve():
                try:
                    bo_serve(root, port=0, assets=assets)
                except Exception as error:
                    errors.put(error)

            with patch("bo_observer.web.bo_web.BOHTTPServer", side_effect=construct):
                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                server = servers.get(timeout=10)
                client = HTTPConnection(*server.server_address, timeout=3)
                try:
                    client.connect()
                    original_socket = client.sock
                    for _ in range(12):
                        client.request("GET", "/viewer.js")
                        response = client.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), b"export const design = true;\n")
                        self.assertFalse(response.will_close)
                        self.assertIs(client.sock, original_socket)
                    client.request("GET", "/viewer.js", headers={"Host": "untrusted.invalid"})
                    response = client.getresponse()
                    self.assertEqual(response.status, 403)
                    response.read()
                    self.assertTrue(response.will_close)
                finally:
                    client.close()
                    server.shutdown()
                    thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertTrue(errors.empty())

    def test_client_close_and_body_bearing_asset_requests_are_not_reused(self):
        """No unread request body can become the next request on a reused socket."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project_fixture(root)
            assets = root / "viewer-assets"
            assets.mkdir()
            (assets / "viewer.js").write_bytes(b"export const ready = true;\n")
            session = GraphSession(root)
            server = make_server(session, port=0, assets=assets)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for headers in ({"Connection": "close"}, {"Content-Length": "1"}):
                    with self.subTest(headers=headers):
                        client = HTTPConnection(*server.server_address, timeout=3)
                        try:
                            client.request("GET", "/viewer.js", headers=headers)
                            response = client.getresponse()
                            self.assertEqual(response.status, 200)
                            response.read()
                            self.assertTrue(response.will_close)
                        finally:
                            client.close()
                self.assertEqual(session.sequence, 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(3)

    def test_module_chain_reuses_socket_then_closes_for_api_response(self):
        """Nested imports share a socket; observation/control boundaries still close it."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project_fixture(root)
            assets = root / "viewer-assets"
            assets.mkdir()
            expected = b"export const ready = true;\n"
            (assets / "viewer.js").write_bytes(expected)
            session = GraphSession(root)
            server = make_server(session, port=0, assets=assets)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            client = HTTPConnection(*server.server_address, timeout=3)
            try:
                client.connect()
                original_socket = client.sock
                for _ in range(120):
                    client.request("GET", "/viewer.js")
                    response = client.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), expected)
                    self.assertFalse(response.will_close)
                    self.assertIs(client.sock, original_socket)
                client.request("GET", "/api/bo/health")
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                self.assertTrue(response.will_close)
                self.assertEqual(session.sequence, 0)
            finally:
                client.close()
                server.shutdown()
                server.server_close()
                thread.join(3)

    def test_cold_parallel_asset_burst_preserves_bytes_and_emits_no_events(self):
        # A browser and its module workers can connect before the serving thread
        # is scheduled. Hold that thread briefly to exercise the listen backlog
        # itself, rather than depend on an intermittent browser connection retry.
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project_fixture(root)
            assets = root / "viewer-assets"
            assets.mkdir()
            expected = {
                "viewer.js": b"export const viewer = 'ready';\n",
                "routing-tools.vendor.js": b"export const route = 'ready';\n",
                "libavoid.wasm": b"\x00asm\x01\x00\x00\x00",
            }
            for name, content in expected.items():
                (assets / name).write_bytes(content)
            session = GraphSession(root)
            server = make_server(session, port=0, assets=assets)
            started, release = threading.Barrier(17), threading.Event()
            connections = queue.Queue()

            def request(index):
                started.wait(timeout=5)
                try:
                    connection = socket.create_connection(server.server_address, timeout=1)
                except OSError as error:
                    connections.put(str(error))
                    return None
                connections.put(None)
                with connection:
                    if not release.wait(5):
                        raise TimeoutError("The test did not start the HTTP server")
                    name = tuple(expected)[index % len(expected)]
                    request_bytes = (
                        f"GET /{name} HTTP/1.0\r\n" f"Host: 127.0.0.1:{server.server_port}\r\n\r\n"
                    ).encode("ascii")
                    connection.settimeout(5)
                    connection.sendall(request_bytes)
                    response = HTTPResponse(connection)
                    response.begin()
                    return (
                        name,
                        response.status,
                        response.getheader("Content-Type"),
                        response.read(),
                    )

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            try:
                with ThreadPoolExecutor(max_workers=16) as pool:
                    pending = [pool.submit(request, index) for index in range(16)]
                    started.wait(timeout=5)
                    accepted = [connections.get(timeout=5) for _ in pending]
                    thread.start()
                    release.set()
                    responses = [future.result(timeout=10) for future in pending]
                self.assertEqual(
                    [error for error in accepted if error],
                    [],
                    "Parallel viewer connections overflowed the listen backlog",
                )
                for name, status, mime, content in responses:
                    self.assertEqual(status, 200)
                    self.assertEqual(content, expected[name])
                    if name.endswith(".wasm"):
                        self.assertEqual(mime, "application/wasm")
                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/api/bo/health", timeout=5
                ) as response:
                    self.assertEqual(
                        response.getheader("Content-Type"), "application/json; charset=utf-8"
                    )
                    response.read()
                self.assertEqual(session.sequence, 0)
                self.assertEqual(session.history.snapshot(), [])
            finally:
                release.set()
                if thread.is_alive():
                    server.shutdown()
                    thread.join(timeout=5)
                server.server_close()
                session.close()


if __name__ == "__main__":
    unittest.main()
