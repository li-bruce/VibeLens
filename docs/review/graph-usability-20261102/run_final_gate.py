"""Run the unchanged full repository gate and retain its exit status and timestamps."""
from datetime import datetime
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--round", default="08")
round_id = parser.parse_args().round
if not round_id.isdigit():
    parser.error("A numeric evidence round is required")
RUN = "full-gate-" + round_id
os.environ["BO_ADAPTER_HOME"] = str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript")
temporary = ROOT / (".validation/graph-usability-full-20261102-" + round_id)
temporary.mkdir(exist_ok=False)
os.environ["TMP"] = str(temporary)
os.environ["TEMP"] = str(temporary)
receipt = {"started": datetime.now().astimezone().isoformat(),
           "command": "python -B -X utf8 tools/verify.py --database"}
(OUT / (RUN + "-started.json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
with (OUT / (RUN + ".log")).open("x", encoding="utf-8") as log:
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "tools/verify.py", "--database"],
                            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
receipt.update(ended=datetime.now().astimezone().isoformat(), passed=result.returncode == 0,
               exit_code=result.returncode)
(OUT / (RUN + ".json")).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt), flush=True)
raise SystemExit(result.returncode)
