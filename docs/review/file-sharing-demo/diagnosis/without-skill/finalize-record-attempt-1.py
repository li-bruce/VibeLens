"""Verify an isolated single-line repair and seal its evidence."""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    before = json.loads((EVIDENCE / "before/manifest.json").read_text(encoding="utf-8"))["sha256"]
    changed = [name for name, expected in before.items() if digest(ROOT / name) != expected]
    assert changed == ["app.py"], changed
    original = (EVIDENCE / "before/app.py").read_bytes()
    current = (ROOT / "app.py").read_bytes()
    wrong = b'(file_id, user["id"]))'
    correct = b'(file_id, recipient_id))'
    assert original.count(wrong) == 1
    assert original.replace(wrong, correct, 1) == current
    test_files = {name: digest(ROOT / name) for name in before if name.startswith("tests/")}
    assert len(test_files) == 4
    assert all(test_files[name] == before[name] for name in test_files)
    diff = "".join(difflib.unified_diff(original.decode().splitlines(keepends=True), current.decode().splitlines(keepends=True),
                                       fromfile="before/app.py", tofile="after/app.py"))
    (EVIDENCE / "repair.diff").write_text(diff, encoding="utf-8")
    after = EVIDENCE / "after"
    after.mkdir(exist_ok=False)
    shutil.copyfile(ROOT / "app.py", after / "app.py")
    with zipfile.ZipFile(after / "repaired-source.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in before:
            archive.write(ROOT / name, name)
    save(after / "manifest.json", {name: digest(ROOT / name) for name in before})

    red = json.loads((EVIDENCE / "red/browser-result.json").read_text(encoding="utf-8"))
    green = json.loads((EVIDENCE / "green/browser-result.json").read_text(encoding="utf-8"))
    assert red["status"] == "failed" and red["stale_page"]["http_status"] == 200
    assert red["stale_page"]["download_events"] == 1 and red["stale_page"]["same_document"]
    assert red["database_before_cancel"] == red["database_after_cancel"]
    assert green["status"] == "passed" and green["stale_page"]["http_status"] == 403
    assert green["stale_page"]["download_events"] == 0 and green["stale_page"]["same_document"]
    assert all(item["passed"] for item in green["checks"])
    assert len(green["original_regression"]["checks"]) == 11
    assert len(green["original_revocation"]["checks"]) == 11
    assert green["original_regression"]["status"] == green["original_revocation"]["status"] == "passed"
    assert red["server_stopped"] and green["server_stopped"]
    red_http = json.loads((EVIDENCE / "red/http-tests.json").read_text(encoding="utf-8"))
    green_http = json.loads((EVIDENCE / "green/http-tests.json").read_text(encoding="utf-8"))
    assert red_http["exit_code"] == 1 and "Ran 20 tests" in red_http["stderr"] and "failures=4" in red_http["stderr"]
    assert green_http["exit_code"] == 0 and "Ran 20 tests" in green_http["stderr"]
    red_downloads = EVIDENCE / "red/witness/downloads"
    assert digest(red_downloads / "unexpected-after-cancel-0.txt") == digest(red_downloads / "recipient-before-cancel.txt")
    green_downloads = list((EVIDENCE / "green/witness/downloads").glob("*.txt"))
    assert len(green_downloads) == 4
    assert len({digest(path) for path in green_downloads}) == 1
    verification = {"timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    "context": "controlled fault supplied before diagnosis", "changed_original_files": changed,
                    "single_binding_parameter_repaired": True, "original_tests_unchanged": test_files,
                    "red_http": {"total": 20, "failures": 4}, "green_http": {"total": 20, "failures": 0},
                    "red_witness": {"total": len(red["checks"]), "failures": sum(not item["passed"] for item in red["checks"])},
                    "green_witness": {"total": len(green["checks"]), "failures": 0},
                    "original_browser_regression": 11, "original_browser_revocation": 11,
                    "isolated_servers_stopped": True, "original_delivery_accessed": False,
                    "preserved_bad_download_matches_original": True, "owner_other_recipient_and_reshare_bytes_equal": True}
    save(EVIDENCE / "verification.json", verification)
    inventory = []
    for path in sorted(EVIDENCE.rglob("*")):
        if path.is_file() and path.name != "evidence-inventory.json":
            path.resolve().relative_to(EVIDENCE.resolve())
            inventory.append({"path": path.relative_to(EVIDENCE).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    save(EVIDENCE / "evidence-inventory.json", {"files": inventory})
    print(json.dumps({"changed_source": changed, "tests_unchanged": len(test_files), "green_http": 20,
                      "green_original_browser": 22, "green_witness": len(green["checks"]), "evidence_files": len(inventory)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
