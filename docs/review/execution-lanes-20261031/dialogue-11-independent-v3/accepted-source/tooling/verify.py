"""Normal project gate; propagate canonical synchronization failures."""
from pathlib import Path
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__":
    os.environ.setdefault("TEAM_FILES_DB_URL", "sqlite:///" + str(ROOT / "var/team-files.sqlite3"))
    result=subprocess.run([sys.executable,"-B",str(ROOT/"observer_runtime/change_sync.py"),"check","--root",str(ROOT)])
    raise SystemExit(result.returncode)
