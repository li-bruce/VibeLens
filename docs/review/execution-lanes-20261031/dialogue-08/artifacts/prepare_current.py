"""Prepare only project-local review/output routing for the current candidate."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def main():
    inspect = json.loads((OUT / "inspect.result.json").read_text(encoding="utf-8"))
    review_path = ROOT / "resume-first-integration-20261031/review.json"
    (OUT / "previous-candidate-review.json").write_bytes(review_path.read_bytes())
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["candidate_id"] = inspect["candidate_id"]
    review["decisions"]["probes"]["reason"] = (
        "Normal canonical runtime/viewer upgrade for actual execution ownership and "
        "focused ancestor boundaries. Business source, assertions and baseline preserved. "
        "Observation outputs routed to review/retest-20261101-02 and scratch under its .tmp. "
        "Fresh runtime, Web, isolation and negative evidence required before accept.")
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    (OUT / "current-candidate-review.json").write_bytes(review_path.read_bytes())
    for name in ("browser_flow.py", "focused_capture.py", "viewer_acceptance.py"):
        path = OUT / name
        text = path.read_text(encoding="utf-8")
        text = text.replace('str(ROOT / ".tmp")', 'str(OUT / ".tmp")')
        if name == "browser_flow.py":
            text = text.replace("fresh-browser-upload-20261101-retry.txt", "fresh-browser-upload-20261101-02.txt")
            text = text.replace("Fresh 2026-11-01 trial 03:", "Fresh 2026-11-01 round 02:")
        path.write_text(text, encoding="utf-8")
    path = OUT / "core_smoke.py"
    path.write_text(path.read_text(encoding="utf-8").replace('CORE = OUT / "core-extracted"', 'CORE = OUT / ".tmp/core-extracted"'), encoding="utf-8")
    path = OUT / "audit_runtime.py"
    path.write_text(path.read_text(encoding="utf-8").replace("dir=OUT, prefix=", 'dir=OUT / ".tmp", prefix='), encoding="utf-8")
    print(json.dumps({"candidate_id": inspect["candidate_id"], "assertions_changed": False}))

if __name__ == "__main__":
    main()
