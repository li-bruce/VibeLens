"""Validate the supplied frozen-source receipt, independently of project checks."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "vibelens-control-fix"
receipt_path = SOURCE / ".validation/control-final-result.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
head = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
assert head == receipt["revision"] == "3052e03c32e9bbfcdc19961cad36085415795433"
assert receipt["valid"] and len(receipt["skill_files"]) == 240 and len(receipt["examples"]) == 2
assert not subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain"], text=True)
for name, value in receipt["skill_files"].items():
    assert sha(SOURCE / name) == value, name
log = SOURCE / ".validation/control-final-full.log"
assert sha(log) == receipt["log_sha256"]
shutil.copyfile(receipt_path, OUT / "upstream-result.json")
shutil.copyfile(log, OUT / "upstream-full.log")
result = {"status": "passed", "revision": head, "clean_worktree": True,
          "verified_skill_files": 240, "example_receipts": receipt["examples"],
          "log_sha256": sha(log), "receipt_sha256": sha(receipt_path),
          "scope": "Supplied source regression receipt only; project and browser acceptance run separately."}
(OUT / "upstream-receipt-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({key: result[key] for key in ("status", "revision", "verified_skill_files", "log_sha256")}))
