"""Capture fresh continuation commands without altering frozen review evidence."""
import hashlib, json, subprocess, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ROUND = Path(__file__).resolve().parent
os.environ.setdefault("TEAM_FILES_DB_URL", "sqlite:///" + str(ROOT / "var/team-files.sqlite3"))
SKILL = ROOT.parents[1] / 'SoftwareStatusObserverSkill/skills/vibelens'
def execute(name, arguments):
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', *arguments], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (ROUND/(name+'.stdout.log')).write_text(result.stdout, encoding='utf-8')
    (ROUND/(name+'.stderr.log')).write_text(result.stderr, encoding='utf-8')
    record={'argv':arguments,'returncode':result.returncode}
    (ROUND/(name+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record))
    return result
if __name__ == '__main__':
    execute(sys.argv[1],sys.argv[2:])
