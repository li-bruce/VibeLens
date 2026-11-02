"""Exercise the listening application, concurrent requests and independent SQLite reads."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.cookiejar
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8982"
PASSWORD = "bands-8972-trial"

class Client:
    def __init__(self, actor=None):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        status, body = self.request("/")
        self.csrf = re.search(rb'name="csrf_token" value="([^"]+)"', body).group(1).decode()
        if actor:
            status, body = self.post("/login", {"username": actor, "password": PASSWORD})
            assert status == 200
            self.csrf = re.search(rb'name="csrf_token" value="([^"]+)"', body).group(1).decode()

    def request(self, path, data=None, headers=None):
        req = urllib.request.Request(BASE + path, data=data, headers=headers or {})
        try:
            with self.opener.open(req, timeout=30) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def post(self, path, fields):
        data = urllib.parse.urlencode({**fields, "csrf_token": self.csrf}).encode()
        return self.request(path, data, {"Accept": "application/json"})

    def upload(self, filename, reviewer="ben"):
        boundary = "----VibeLensFreshTrial03"
        content = ("Fresh real concurrent application upload: " + filename + "\n").encode()
        parts = []
        for key, value in {"csrf_token": self.csrf, "reviewer_id": reviewer}.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'.encode() + content + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self.request("/upload", b"".join(parts), {"Content-Type": "multipart/form-data; boundary=" + boundary, "Accept": "application/json"})

def run():
    clients = {actor: Client(actor) for actor in ("alice", "ben", "cara", "dan")}
    a, b, c, d = [clients[actor] for actor in ("alice", "ben", "cara", "dan")]
    checks, files = [], []
    def check(label, result, expected):
        status, body = result
        checks.append({"case": label, "status": status, "expected": expected,
            "body": json.loads(body) if body.startswith(b"{") else body[:120].decode(errors="replace")})
        assert status == expected, checks[-1]
        return json.loads(body) if body.startswith(b"{") else body

    check("anonymous metadata", Client().request("/files/no-file"), 401)
    check("incorrect password", Client().post("/login", {"username": "alice", "password": "wrong"}), 401)
    check("missing csrf", a.request("/upload", b"", {"Accept": "application/json"}), 400)
    check("self reviewer rolls back", a.upload("self-review-denied.txt", "alice"), 403)
    check("unknown reviewer rolls back", a.upload("unknown-reviewer-denied.txt", "missing-user"), 403)

    # Each worker owns a real cookie session. The barrier launches simultaneous HTTP requests.
    workers = [(Client("alice"), "ben"), (Client("cara"), "dan"), (Client("dan"), "alice"), (Client("ben"), "cara")]
    barrier = threading.Barrier(len(workers))
    def concurrent_upload(index):
        client, reviewer = workers[index]
        barrier.wait()
        started = time.perf_counter_ns()
        response = client.upload(f"concurrent-{index}-fresh.txt", reviewer)
        ended = time.perf_counter_ns()
        value = check(f"concurrent upload {index}", response, 201)
        return {"index": index, "started_ns": started, "ended_ns": ended, "row": value}
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(concurrent_upload, range(4)))
    files.extend(item["row"]["id"] for item in concurrent)
    assert max(item["started_ns"] for item in concurrent) < min(item["ended_ns"] for item in concurrent)

    fid = files[0]
    path = "/files/" + fid
    check("recipient before approval", c.request(path), 403)
    check("uploader cannot review", a.post(path + "/review", {"decision": "approve"}), 403)
    check("share before approval", a.post(path + "/share", {"recipient_id": "cara"}), 403)
    check("invalid review decision", b.post(path + "/review", {"decision": "maybe"}), 400)
    reviewers = [Client("ben"), Client("ben")]
    race_barrier = threading.Barrier(2)
    def review_race(index):
        race_barrier.wait()
        status, body = reviewers[index].post(path + "/review", {"decision": "approve"})
        return {"status": status, "body": json.loads(body)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        race = list(pool.map(review_race, range(2)))
    assert sorted(item["status"] for item in race) == [200, 409], race
    check("recipient still unshared", c.request(path), 403)
    check("reviewer cannot share", b.post(path + "/share", {"recipient_id": "cara"}), 403)
    check("unknown recipient rolls back", a.post(path + "/share", {"recipient_id": "missing-user"}), 400)
    check("uploader shares once", a.post(path + "/share", {"recipient_id": "cara"}), 200)
    check("recipient cannot forward", c.post(path + "/share", {"recipient_id": "dan"}), 403)
    check("cannot replace recipient", a.post(path + "/share", {"recipient_id": "dan"}), 409)
    check("unrelated user metadata", d.request(path), 403)
    check("unrelated user download", d.request(path + "/download"), 403)
    check("recipient download", c.request(path + "/download"), 200)
    check("missing file", a.request("/files/no-file"), 404)

    rejected = check("upload for rejection", a.upload("fresh-rejected.txt"), 201)["id"]
    files.append(rejected)
    check("assigned reviewer rejects", b.post("/files/" + rejected + "/review", {"decision": "reject"}), 200)
    check("rejected flow remains closed", b.post("/files/" + rejected + "/review", {"decision": "approve"}), 409)
    check("rejected file cannot share", a.post("/files/" + rejected + "/share", {"recipient_id": "cara"}), 403)
    check("reviewer retains rejected download", b.request("/files/" + rejected + "/download"), 200)
    with sqlite3.connect(ROOT / "var/team-files.sqlite3") as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute("SELECT id,filename,state,revision,uploader_id,reviewer_id,recipient_id,size,journal FROM files ORDER BY id")]
        assert not db.execute("SELECT id FROM files WHERE filename IN ('self-review-denied.txt','unknown-reviewer-denied.txt')").fetchall()
    selected = [row for row in rows if row["id"] in files]
    primary = next(row for row in selected if row["id"] == fid)
    assert (primary["state"], primary["revision"], primary["recipient_id"]) == ("approved", 3, "cara")
    assert len(json.loads(primary["journal"])) == 3
    rejected_row = next(row for row in selected if row["id"] == rejected)
    assert (rejected_row["state"], rejected_row["revision"], rejected_row["recipient_id"]) == ("rejected", 2, None)
    result = {"valid": True, "transport": "actual threaded HTTP server", "checks": checks,
        "concurrent_requests": concurrent, "review_race": race, "sqlite_rows": selected,
        "concurrent_overlap": True, "rollback_effects_checked": True}
    (OUT / "http-matrix.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    print(json.dumps({key: value for key, value in run().items() if key in ("valid", "concurrent_overlap", "rollback_effects_checked")}))
