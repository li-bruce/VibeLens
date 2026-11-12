"""Build small Pages transports from unchanged, archived execution evidence.

The story shell needs captions and event IDs, not source indexes or event payloads.
The embedded viewer receives the complete artifact with repeated JSON values stored
once. Reconstruction is lossless; this is a transport optimization, not graph pruning.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs/site"


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pack(artifact):
    """Keep first occurrences and restore later copies through ordered path aliases."""
    seen, aliases = {}, []

    def visit(value, path):
        if not isinstance(value, (dict, list)):
            return value
        canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if len(canonical) >= 512:
            digest = hashlib.sha256(canonical.encode()).hexdigest()
            if digest in seen:
                aliases.append([path, seen[digest]])
                return None
            seen[digest] = path
        if isinstance(value, list):
            return [visit(item, [*path, i]) for i, item in enumerate(value)]
        return {key: visit(item, [*path, key]) for key, item in value.items()}

    data = visit(artifact, [])
    return {"schema": "vibelens-case-transport/v1", "data": data, "aliases": aliases}


def summarize(artifact):
    """Keep only fields consumed by the parent conversation and application preview."""
    model = artifact["view"]["model"]
    result = {
        "version": artifact["version"],
        "story": artifact["story"],
        "view": {
            "model": {
                "nodes": [
                    {key: node[key] for key in ("id", "label", "source") if key in node}
                    for node in model["nodes"]
                ],
                "edges": [
                    {key: edge[key] for key in ("id", "from", "to", "type")}
                    for edge in model["edges"]
                ],
                "machine": model["machine"],
            }
        },
        "recording": {"events": [{"id": event["id"]} for event in artifact["recording"]["events"]]},
        "application_frames": artifact["application_frames"],
    }
    for key in ("application_start", "application_overview"):
        if key in artifact:
            result[key] = artifact[key]
    return result


def build():
    target = SITE / "case-preview"
    target.mkdir(parents=True, exist_ok=True)
    summaries, sizes = [], []
    for version in (1, 2):
        source = SITE / f"case-data/v{version}.json"
        artifact = json.loads(source.read_text(encoding="utf-8"))
        payload = encode(pack(artifact))
        (target / f"v{version}.json").write_text(payload, encoding="utf-8", newline="\n")
        summaries.append(summarize(artifact))
        sizes.append(
            {
                "version": version,
                "original": source.stat().st_size,
                "transport": len(payload.encode()),
            }
        )
    shell = encode({"schema": "vibelens-story-summary/v1", "versions": summaries})
    (target / "story.json").write_text(shell, encoding="utf-8", newline="\n")
    print(json.dumps({"story_bytes": len(shell.encode()), "artifacts": sizes}))


if __name__ == "__main__":
    build()
