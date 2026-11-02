"""Retain commands and receipts for the explicitly authorized fresh retest."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ROUND = Path(__file__).resolve().parent
os.environ.setdefault("TEAM_FILES_DB_URL", "sqlite:///" + str(ROOT / "var/team-files.sqlite3"))

if __name__ == "__main__":
    name, arguments = sys.argv[1], sys.argv[2:]
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", *arguments], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    (ROUND / (name + ".stdout.log")).write_text(result.stdout, encoding="utf-8")
    (ROUND / (name + ".stderr.log")).write_text(result.stderr, encoding="utf-8")
    receipt = {"argv": arguments, "returncode": result.returncode}
    (ROUND / (name + ".json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    print(result.stdout[-4500:])
    raise SystemExit(result.returncode)
