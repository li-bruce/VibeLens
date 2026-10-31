"""Run the project's accepted-current-input gate."""

from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

if __name__=="__main__":
    result=subprocess.run([sys.executable,"-B","-X","utf8",str(ROOT/"observer_runtime/change_sync.py"),"check","--root",str(ROOT)],cwd=ROOT)
    raise SystemExit(result.returncode)
