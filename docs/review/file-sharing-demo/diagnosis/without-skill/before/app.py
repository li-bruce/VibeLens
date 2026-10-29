"""A local file-sharing demo built with Python's standard library and SQLite."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import mimetypes
import secrets
import shutil
import sqlite3
import time
from contextlib import closing
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parent
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 64 * 1024
SESSION_SECONDS = 8 * 60 * 60
DEMO_PASSWORD = "Demo123!"
DEMO_USERS = (("linzhou", "林舟"), ("xuning", "许宁"), ("zhoulan", "周岚"))


def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 260_000).hex()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "uploads").mkdir(exist_ok=True)
    with closing(connect(data_dir / "app.sqlite3")) as db, db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                csrf_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shares (
                file_id INTEGER NOT NULL REFERENCES files(id),
                recipient_id INTEGER NOT NULL REFERENCES users(id),
                created_at INTEGER NOT NULL,
                PRIMARY KEY (file_id, recipient_id)
            );
            CREATE INDEX IF NOT EXISTS shares_by_recipient ON shares(recipient_id);
        """)
        for username, display_name in DEMO_USERS:
            if not db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                salt = secrets.token_hex(16)
                db.execute(
                    "INSERT INTO users (username, display_name, salt, password_hash) VALUES (?, ?, ?, ?)",
                    (username, display_name, salt, password_hash(DEMO_PASSWORD, salt)),
                )


class RequestError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class FileSharingServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], data_dir: Path):
        initialize(data_dir)
        self.data_dir = data_dir
        self.database = data_dir / "app.sqlite3"
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: FileSharingServer
    server_version = "FileSharingDemo/2.0"
    sys_version = ""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        super().end_headers()

    def json_response(self, status: int, value: dict, cookie: str | None = None) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def read_body(self, limit: int) -> bytes:
        if self.headers.get("Transfer-Encoding"):
            raise RequestError(400, "Chunked request bodies are not supported.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise RequestError(400, "Invalid request length.") from None
        if length < 0:
            raise RequestError(400, "Invalid request length.")
        if length > limit:
            self.close_connection = True
            raise RequestError(413, "The file is too large. Maximum file size is 10 MB.")
        body = self.rfile.read(length)
        if len(body) != length:
            raise RequestError(400, "The request body is incomplete.")
        return body

    def read_json(self) -> dict:
        if self.headers.get_content_type() != "application/json":
            raise RequestError(415, "Expected an application/json request.")
        try:
            body = json.loads(self.read_body(16 * 1024))
        except (ValueError, UnicodeError):
            raise RequestError(400, "Invalid JSON request.") from None
        if not isinstance(body, dict):
            raise RequestError(400, "Expected a JSON object.")
        return body

    def session(self, db: sqlite3.Connection) -> sqlite3.Row | None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie["session"].value if "session" in cookie else ""
        except Exception:
            return None
        if not token or len(token) > 256:
            return None
        return db.execute(
            "SELECT u.id, u.username, u.display_name, s.csrf_token, s.token_hash "
            "FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (token_hash(token), int(time.time())),
        ).fetchone()

    def require_user(self, db: sqlite3.Connection, mutation: bool = False) -> sqlite3.Row:
        user = self.session(db)
        if user is None:
            raise RequestError(401, "Please sign in to continue.")
        if mutation and not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), user["csrf_token"]):
            raise RequestError(403, "This session could not be verified. Sign in again.")
        return user

    @staticmethod
    def public_user(user: sqlite3.Row) -> dict:
        return {key: user[key] for key in ("id", "username", "display_name")}

    def check_request_origin(self) -> None:
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            raise RequestError(403, "This demo accepts local requests only.")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{host}":
            raise RequestError(403, "Cross-origin requests are not allowed.")

    def do_GET(self) -> None:
        self.dispatch("GET")

    def do_POST(self) -> None:
        self.dispatch("POST")

    def dispatch(self, method: str) -> None:
        try:
            self.check_request_origin()
            path = urlsplit(self.path).path
            if method == "GET" and path in {"/", "/app.js", "/styles.css", "/favicon.svg"}:
                self.serve_static(path)
                return
            with closing(connect(self.server.database)) as db, db:
                if method == "POST" and path == "/api/login":
                    self.login(db)
                elif method == "GET" and path == "/api/session":
                    user = self.session(db)
                    self.json_response(200, {"user": self.public_user(user) if user else None,
                                             "csrf_token": user["csrf_token"] if user else None})
                elif method == "POST" and path == "/api/logout":
                    user = self.require_user(db, mutation=True)
                    db.execute("DELETE FROM sessions WHERE token_hash = ?", (user["token_hash"],))
                    db.commit()
                    self.json_response(200, {"ok": True}, "session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
                elif method == "GET" and path == "/api/users":
                    user = self.require_user(db)
                    users = db.execute("SELECT id, username, display_name FROM users WHERE id != ? ORDER BY id", (user["id"],))
                    self.json_response(200, {"users": [dict(row) for row in users]})
                elif method == "GET" and path == "/api/files":
                    self.list_files(db, self.require_user(db))
                elif method == "POST" and path == "/api/files":
                    self.upload(db, self.require_user(db, mutation=True))
                elif path.startswith("/api/files/"):
                    self.file_route(db, method, path)
                else:
                    raise RequestError(404, "This page or action does not exist.")
        except RequestError as error:
            self.json_response(error.status, {"error": error.message})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            import traceback
            traceback.print_exc()
            self.json_response(500, {"error": "The request could not be completed. Try again."})

    def serve_static(self, path: str) -> None:
        name = "index.html" if path == "/" else path[1:]
        asset = ROOT / "static" / name
        data = asset.read_bytes()
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        if name.endswith((".html", ".js", ".css")):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def login(self, db: sqlite3.Connection) -> None:
        body = self.read_json()
        username, password = body.get("username"), body.get("password")
        if not isinstance(username, str) or not isinstance(password, str) or len(password) > 512:
            raise RequestError(400, "Enter a username and password.")
        user = db.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if user is None or not hmac.compare_digest(password_hash(password, user["salt"]), user["password_hash"]):
            raise RequestError(401, "The username or password is incorrect.")
        token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        previous = self.session(db)
        if previous:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (previous["token_hash"],))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)",
                   (token_hash(token), user["id"], csrf_token, int(time.time()) + SESSION_SECONDS))
        db.commit()
        self.json_response(200, {"user": self.public_user(user), "csrf_token": csrf_token},
                           f"session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}")

    def list_files(self, db: sqlite3.Connection, user: sqlite3.Row) -> None:
        rows = db.execute(
            "SELECT f.id, f.name, f.size, f.created_at, f.owner_id, u.display_name AS owner_name "
            "FROM files f JOIN users u ON u.id = f.owner_id "
            "WHERE f.owner_id = ? OR EXISTS "
            "(SELECT 1 FROM shares s WHERE s.file_id = f.id AND s.recipient_id = ?) "
            "ORDER BY f.created_at DESC, f.id DESC", (user["id"], user["id"]),
        ).fetchall()
        owned, received = [], []
        for row in rows:
            item = dict(row)
            item["is_owner"] = row["owner_id"] == user["id"]
            if item["is_owner"]:
                item["recipients"] = [dict(recipient) for recipient in db.execute(
                    "SELECT u.id, u.display_name FROM shares s JOIN users u ON u.id = s.recipient_id "
                    "WHERE s.file_id = ? ORDER BY u.id", (row["id"],))]
                owned.append(item)
            else:
                received.append(item)
        self.json_response(200, {"owned": owned, "received": received})

    def upload(self, db: sqlite3.Connection, user: sqlite3.Row) -> None:
        content_type = self.headers.get("Content-Type", "")
        if self.headers.get_content_type() != "multipart/form-data" or "\r" in content_type or "\n" in content_type:
            raise RequestError(415, "Choose a file to upload.")
        body = self.read_body(MAX_REQUEST_BYTES)
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body)
        parts = [part for part in message.iter_parts()
                 if part.get_param("name", header="content-disposition") == "file"]
        if len(parts) != 1 or parts[0].get_filename() is None:
            raise RequestError(400, "Choose one file to upload.")
        name = parts[0].get_filename().replace("\\", "/").split("/")[-1]
        if not name or name in {".", ".."} or len(name) > 200 or any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise RequestError(400, "Use a file name of 1 to 200 characters without control characters.")
        content = parts[0].get_payload(decode=True)
        if content is None:
            raise RequestError(400, "The file content is invalid.")
        if len(content) > MAX_FILE_BYTES:
            raise RequestError(413, "The file is too large. Maximum file size is 10 MB.")
        storage_key = secrets.token_hex(24)
        destination = self.server.data_dir / "uploads" / storage_key
        try:
            destination.write_bytes(content)
            cursor = db.execute(
                "INSERT INTO files (owner_id, name, size, storage_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (user["id"], name, len(content), storage_key, int(time.time())),
            )
            db.commit()
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        self.json_response(201, {"id": cursor.lastrowid, "name": name, "size": len(content), "owner_id": user["id"]})

    def file_route(self, db: sqlite3.Connection, method: str, path: str) -> None:
        segments = path.strip("/").split("/")
        if len(segments) not in {3, 4} or not segments[2].isascii() or not segments[2].isdigit() or len(segments[2]) > 15:
            raise RequestError(404, "This file or action does not exist.")
        file_id = int(segments[2])
        action = segments[3] if len(segments) == 4 else "info"
        if (method, action) not in {("GET", "info"), ("GET", "download"), ("POST", "shares"), ("POST", "revoke")}:
            raise RequestError(404, "This file or action does not exist.")
        user = self.require_user(db, mutation=method == "POST")
        file = db.execute("SELECT f.*, u.display_name AS owner_name FROM files f "
                          "JOIN users u ON u.id = f.owner_id WHERE f.id = ?", (file_id,)).fetchone()
        if file is None:
            raise RequestError(404, "The file does not exist.")
        if action in {"shares", "revoke"}:
            if file["owner_id"] != user["id"]:
                raise RequestError(403, "Only the file owner can manage sharing for this file.")
            recipient_id = self.read_json().get("recipient_id")
            if (type(recipient_id) is not int or not 0 < recipient_id <= 2**63 - 1
                    or not db.execute("SELECT id FROM users WHERE id = ?", (recipient_id,)).fetchone()):
                raise RequestError(400, "Choose an existing recipient.")
            if recipient_id == user["id"]:
                raise RequestError(400, "You already own this file. Choose another user.")
            if action == "revoke":
                db.execute("DELETE FROM shares WHERE file_id = ? AND recipient_id = ?", (file_id, user["id"]))
            else:
                db.execute("INSERT OR IGNORE INTO shares (file_id, recipient_id, created_at) VALUES (?, ?, ?)",
                           (file_id, recipient_id, int(time.time())))
            db.commit()
            self.json_response(200, {"ok": True, "file_id": file_id, "recipient_id": recipient_id, "shared": action == "shares"})
            return
        allowed = file["owner_id"] == user["id"] or db.execute(
            "SELECT 1 FROM shares WHERE file_id = ? AND recipient_id = ?", (file_id, user["id"])).fetchone()
        if not allowed:
            raise RequestError(403, "You do not have access to this file.")
        if action == "info":
            self.json_response(200, {key: file[key] for key in ("id", "name", "size", "owner_id", "owner_name", "created_at")})
            return
        source = self.server.data_dir / "uploads" / file["storage_key"]
        if not source.is_file():
            raise RequestError(404, "The file content is unavailable.")
        with source.open("rb") as handle:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(file["size"]))
            self.send_header("Content-Disposition", f"attachment; filename=\"download\"; filename*=UTF-8''{quote(file['name'], safe='')}")
            self.end_headers()
            shutil.copyfileobj(handle, self.wfile)


def create_server(data_dir: Path, port: int = 8765) -> FileSharingServer:
    return FileSharingServer(("127.0.0.1", port), data_dir.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    server = create_server(args.data_dir, args.port)
    print(f"File sharing demo: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
