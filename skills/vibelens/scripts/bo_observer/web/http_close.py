"""Bounded staged close for a response that rejects an unread request body.

RFC 9112 section 9.6 describes how a full close with unread inbound bytes can
reset the connection before the client reads the response. Send the rejection
first, half-close output, then consume only a bounded remainder. Never parse or
admit that body, and never wait indefinitely for an incomplete client request.
"""

import socket
import time

# Cleanup is not admission: a rejected 256 KiB event group may still be in
# flight when the response is sent. Drain up to the viewer's largest supported
# body size in small chunks, under the same short deadline. A 64 KiB cleanup
# cap left ordinary oversized groups unread and could reset their HTTP error.
DRAIN_LIMIT = 2 * 1024 * 1024
DRAIN_SECONDS = 0.25


def reject_unread_body(handler, code, body):
    """Deliver a rejection before a short, byte-bounded transport cleanup."""
    handler.close_connection = True
    handler.reply(code, body)
    connection = handler.connection
    previous_timeout = connection.gettimeout()
    try:
        handler.wfile.flush()
        connection.shutdown(socket.SHUT_WR)
        try:
            remaining = min(max(int(handler.headers.get("Content-Length", "0")), 0), DRAIN_LIMIT)
        except ValueError:
            remaining = DRAIN_LIMIT
        deadline = time.monotonic() + DRAIN_SECONDS
        while remaining:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                break
            connection.settimeout(timeout)
            chunk = handler.rfile.read1(min(remaining, 8192))
            if not chunk:
                break
            remaining -= len(chunk)
    except OSError:
        # The peer may already have left. The original rejection stays final.
        pass
    finally:
        try:
            connection.settimeout(previous_timeout)
        except OSError:
            pass
