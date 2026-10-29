"""Index local originals by hash and verify token-free public-facing prose; no export."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
token = read(OUT / "controls/activation-private.json")["result"]["session"]
for path in (OUT / "index.md", OUT / "summary.json", ROOT / "README.md", ROOT / "review/index.md"):
    content = path.read_text(encoding="utf-8")
    assert token not in content and ("custom-vl-" + token[:8]) not in content, path.name
files = [{"path": path.relative_to(OUT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size,
          "local_private_scope": path.relative_to(OUT).parts[0] == "controls"}
         for path in sorted(OUT.rglob("*")) if path.is_file()
         and path.name != "local-artifact-index.json" and "__pycache__" not in path.parts]
private = []
for folder in ("bo_stategraph/config/control", "bo_stategraph/config/views/conversations"):
    for path in sorted((ROOT / folder).rglob("*")):
        if not path.is_file() or path.suffix == ".lock":
            continue
        private.append({"path_redacted": path.relative_to(ROOT).as_posix().replace(token, "<private-session>"),
                        "sha256": sha(path), "bytes": path.stat().st_size, "exclude_from_public_archive": True})
assert private
result = {"schema": "local-acceptance-original-hashes/v1", "created_at": datetime.now(timezone.utc).isoformat(),
          "public_export_created": False, "session_fingerprint": hashlib.sha256(token.encode()).hexdigest(),
          "files": files, "private_configuration": private,
          "public_prose_token_check": "passed",
          "note": "Hashes index local originals. No sanitized public copies were made. Exclude private config and redact tokens/token-derived profile prefixes before public archival; preserve business and node/event/build identities."}
(OUT / "local-artifact-index.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"indexed_local_files": len(files), "private_config_files": len(private),
                  "public_prose_token_check": "passed", "public_export_created": False}))
