"""Run the project-local design viewer without starting business behavior."""

import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents" / "skills" / "vibelens" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from bo_observer.web.bo_web import bo_serve


if __name__ == "__main__":
    record = {
        "phase": "design_only",
        "root": str(ROOT),
        "server_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "executable": sys.executable,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "application_url": None,
        "graph_url": None,
        "note": "No business application exists before confirmation.",
    }
    (ROOT / "review" / "design-process.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    print(json.dumps(record), flush=True)
    bo_serve(ROOT, port=0)
