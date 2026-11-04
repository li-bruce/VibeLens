"""Check preserved files after native startup without changing business data."""

import hashlib
import json
from pathlib import Path

EVIDENCE = Path(__file__).parent
REPOSITORY = EVIDENCE.parents[3]
TRIAL = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
before = json.loads((EVIDENCE / "protected-before.json").read_text(encoding="utf-8"))
changed = []
for name, expected in before.items():
    path = TRIAL / name
    current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if current != expected["sha256"]:
        changed.append({"path": name, "before": expected["sha256"], "current": current})

database = bytearray((TRIAL / "runtime/team-files.sqlite3").read_bytes())
expected = before["runtime/team-files.sqlite3"]["sha256"]
counter = int.from_bytes(database[24:28], "big")
valid_for = int.from_bytes(database[92:96], "big")
counter_only = None
for difference in range(1, min(counter, valid_for, 32) + 1):
    candidate = bytearray(database)
    candidate[24:28] = (counter - difference).to_bytes(4, "big")
    candidate[92:96] = (valid_for - difference).to_bytes(4, "big")
    if hashlib.sha256(candidate).hexdigest() == expected:
        counter_only = {"counter_increment": difference, "changed_header_ranges": [[24, 28], [92, 96]], "all_other_database_bytes_identical": True}
        break
allowed = {".stategraph/code-graph.json"}
if counter_only:
    allowed.add("runtime/team-files.sqlite3")
result = {
    "checked_files": len(before),
    "changed": changed,
    "generated_source_cache_refreshed": any(item["path"] == ".stategraph/code-graph.json" for item in changed),
    "database_restart_metadata": counter_only,
    "unexpected_changes": [item for item in changed if item["path"] not in allowed],
}
result["valid"] = not result["unexpected_changes"]
(EVIDENCE / "restart-hash-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
raise SystemExit(int(not result["valid"]))
