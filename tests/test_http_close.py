"""Rejected HTTP bodies cannot turn bounded cleanup into an unbounded wait/read."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import socket
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/vibelens/scripts"))
from bo_observer.web.http_close import reject_unread_body, DRAIN_LIMIT, DRAIN_SECONDS


class RejectedBodyTests(unittest.TestCase):
    def handler(self):
        calls = []
        connection = Mock()
        connection.gettimeout.return_value = 7
        connection.shutdown.side_effect = lambda how: calls.append(("shutdown", how))
        reader = BytesIO(b"x" * (DRAIN_LIMIT * 2))
        handler = SimpleNamespace(
            connection=connection,
            headers={"Content-Length": str(DRAIN_LIMIT * 3)},
            rfile=reader,
            wfile=BytesIO(),
            reply=lambda code, body: calls.append(("reply", code)),
            close_connection=False,
        )
        return handler, calls

    def test_reject_precedes_half_close_and_byte_bounded_drain(self):
        handler, calls = self.handler()
        reject_unread_body(handler, 403, {"error": "denied"})
        self.assertEqual(calls, [("reply", 403), ("shutdown", socket.SHUT_WR)])
        self.assertEqual(handler.rfile.tell(), DRAIN_LIMIT)
        self.assertTrue(handler.close_connection)
        handler.connection.settimeout.assert_called_with(7)

    def test_deadline_and_disconnect_keep_original_rejection(self):
        handler, calls = self.handler()
        with patch("bo_observer.web.http_close.time.monotonic", side_effect=[0, DRAIN_SECONDS + 1]):
            reject_unread_body(handler, 400, {})
        self.assertEqual(handler.rfile.tell(), 0)
        handler.connection.shutdown.side_effect = ConnectionResetError
        reject_unread_body(handler, 403, {})
        self.assertEqual(calls[-1], ("reply", 403))
        handler.connection.settimeout.assert_called_with(7)

    def test_rejected_event_group_can_drain_without_truncating_the_response(self):
        """A group just above the 256 KiB admission limit still receives its error."""
        handler, calls = self.handler()
        payload = b"x" * (300 * 1024)
        handler.headers["Content-Length"] = str(len(payload))
        handler.rfile = BytesIO(payload)
        reject_unread_body(handler, 400, {"error": "invalid payload size"})
        self.assertEqual(calls, [("reply", 400), ("shutdown", socket.SHUT_WR)])
        self.assertEqual(handler.rfile.tell(), len(payload))
        handler.connection.settimeout.assert_called_with(7)


if __name__ == "__main__":
    unittest.main()
