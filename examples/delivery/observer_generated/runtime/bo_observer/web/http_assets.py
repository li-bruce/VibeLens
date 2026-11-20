"""Bounded connection reuse for the viewer's nested module imports.

Static assets have complete byte lengths and no request body. Reusing their
connection avoids a new TCP handshake for every import. JSON/control/ingestion
responses retain a closing connection, including all rejected request bodies.
"""

from http.server import BaseHTTPRequestHandler


class AssetHTTPHandler(BaseHTTPRequestHandler):
    """Allow HTTP/1.1 only where the response explicitly permits reuse."""

    protocol_version = "HTTP/1.1"

    def response_connection(self, code, body):
        """Reuse successful, bodyless asset GETs for at most five idle seconds.

        A client requesting close, an HTTP/1.0 client, or a body-bearing GET is
        never upgraded. The idle deadline bounds an abandoned browser socket;
        it does not extend recording or observation settlement deadlines.
        """
        reusable = (
            self.command == "GET"
            and self.request_version == "HTTP/1.1"
            and not self.close_connection
            and code == 200
            and isinstance(body, bytes)
            and self.headers.get("Content-Length", "0") == "0"
            and not self.headers.get("Transfer-Encoding")
        )
        self.close_connection = not reusable
        if reusable:
            self.connection.settimeout(5)
        return "keep-alive" if reusable else "close"
