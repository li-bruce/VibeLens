"""Exercise real Flask/SQLite operations and their independent observation export."""

import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def request(base, path, actor="Alice", body=None, method=None, content_type="application/json"):
    """Read the actual HTTP response, including framework error responses."""
    headers = {"X-User": actor}
    if body is not None:
        headers["Content-Type"] = content_type
        body = body if isinstance(body, bytes) else json.dumps(body).encode()
    try:
        response = urlopen(
            Request(base + path, data=body, method=method, headers=headers), timeout=10
        )
    except HTTPError as error:
        response = error
    raw = response.read()
    return response.status, (
        json.loads(raw)
        if response.headers.get("Content-Type", "").startswith("application/json")
        else raw
    )
