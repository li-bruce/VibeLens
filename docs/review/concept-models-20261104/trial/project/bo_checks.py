"""Run exact concept, physical source and metadata checks independently of HTTP."""

# These portable entrypoints load the explicitly selected Skill before importing it.
# ruff: noqa: E402

from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import sqlite3
import tempfile
from contextlib import closing

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(os.environ["VIBELENS_SKILL"]) / "scripts"))

from bo_observer import concepts
from bo_observer.code_graph.service import CodeGraph
from bo_observer.data.sync import synchronize
from bo_observer.model_io import read_model
from bo_observer.policy.projection import projection_errors


def main():
    """Fail for a removed native guard or missing fact binding in an isolated copy."""
    model = read_model(ROOT / "bo_stategraph/project.json")
    document = json.loads((ROOT / "discovery.json").read_text(encoding="utf-8"))
    acceptance = json.loads((ROOT / "acceptance.json").read_text(encoding="utf-8"))
    report = concepts.assess(document, model=model, acceptance=acceptance)
    assert report["ready"], report
    damaged = deepcopy(model)
    damaged["machine"]["transitions"][0]["conditions"] = []
    assert not concepts.assess(document, model=damaged, acceptance=acceptance)["ready"]
    damaged = deepcopy(model)
    damaged["concepts"]["facts"].pop("active-grant")
    assert not concepts.assess(document, model=damaged, acceptance=acceptance)["ready"]
    assert not projection_errors(model)
    api = CodeGraph(ROOT, persist=False).api_observation_check()
    assert api["valid"], api
    data = synchronize(ROOT, model_path="bo_stategraph/project.json", update=False)
    assert data["valid"], data
    from service import FileService, AccessDenied

    with tempfile.TemporaryDirectory(dir=ROOT / "var") as folder:
        folder = Path(folder)
        (folder / "existing").write_bytes(b"Retained v1 upload")
        with closing(sqlite3.connect(folder / "files.sqlite3")) as connection:
            connection.executescript(
                "CREATE TABLE files(id TEXT PRIMARY KEY, owner TEXT, name TEXT);"
                "CREATE TABLE grants(file_id TEXT PRIMARY KEY REFERENCES files(id), recipient TEXT, active INTEGER, revision INTEGER);"
                "INSERT INTO files VALUES('existing', 'Alice', 'retained.txt');"
                "INSERT INTO grants VALUES('existing', 'Bob', 1, 7);"
            )
            connection.commit()
        files = FileService(folder)
        assert files.download("Bob", "existing") == b"Retained v1 upload"
        assert files.facts("Bob", "existing")["revision"] == 7
        files.share("Alice", "existing", "Carol")
        files.revoke("Alice", "existing", "Bob")
        try:
            files.download("Bob", "existing")
        except AccessDenied:
            pass
        else:
            raise AssertionError("Revoked v1 recipient retained access")
        assert files.download("Carol", "existing") == b"Retained v1 upload"
        assert files.facts("Bob", "existing")["revision"] == 8
    print(
        json.dumps(
            {
                "concepts": "passed",
                "negative_checks": 2,
                "api": "passed",
                "database": "passed",
                "v1_data_migration": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
