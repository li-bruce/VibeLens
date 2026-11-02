"""Execute the exported core in a new process with no observer implementation."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import zipfile

OUT = Path(__file__).resolve().parent
CORE = OUT / "core-extracted"

if not CORE.exists():
    with zipfile.ZipFile(OUT / "core.zip") as archive:
        names = archive.namelist()
        assert not any(name.startswith(("observer_runtime/", "integrations/", "bo_stategraph/data/", "bo_stategraph/config/views/", "bo_stategraph/config/control/")) for name in names)
        archive.extractall(CORE)
sys.path.insert(0, str(CORE))
from app.web import create_app
from app.storage import TEST_PASSWORD

def main():
    content = b"Actual exported core workflow without VibeLens Web or runtime.\n"
    app = create_app(CORE)
    clients = {actor: app.test_client() for actor in ("alice", "ben", "cara", "dan")}
    def post(client, path, data):
        client.get("/")
        with client.session_transaction() as session:
            token = session["csrf_token"]
        return client.post(path, data={**data, "csrf_token": token}, headers={"Accept": "application/json"})
    for actor, client in clients.items():
        assert post(client, "/login", {"username": actor, "password": TEST_PASSWORD}).status_code == 302
    a, b, c, d = [clients[actor] for actor in ("alice", "ben", "cara", "dan")]
    upload = post(a, "/upload", {"reviewer_id": "ben", "file": (io.BytesIO(content), "core-file.txt")})
    assert upload.status_code == 201
    path = "/files/" + upload.json["id"]
    assert post(a, path + "/share", {"recipient_id": "cara"}).status_code == 403
    assert post(b, path + "/review", {"decision": "approve"}).status_code == 200
    assert post(a, path + "/share", {"recipient_id": "cara"}).status_code == 200
    assert c.get(path + "/download").data == content
    assert d.get(path + "/download").status_code == 403
    assert post(c, path + "/share", {"recipient_id": "dan"}).status_code == 403
    with sqlite3.connect(CORE / "var/team-files.sqlite3") as db:
        actual = db.execute("SELECT state,revision,recipient_id FROM files WHERE id=?", (upload.json["id"],)).fetchone()
    assert actual == ("approved", 3, "cara")
    assert not any(name == "bo_observer" or name.startswith("bo_observer.") for name in sys.modules)
    app.extensions["trial_store"].engine.dispose()
    result = {"valid": True, "source_root": str(CORE), "observed_runtime_imported": False,
        "actual_sqlite": list(actual), "download_bytes": len(content), "business_entrypoints": "actual Flask handlers",
        "scope": "Exported core upload/review/share/download and rejection checks; no observer runtime or Web is packaged."}
    (OUT / "core-execution.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
