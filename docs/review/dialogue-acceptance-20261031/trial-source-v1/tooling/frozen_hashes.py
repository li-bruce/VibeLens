"""Verify trial provenance and native-library parity without exempting edited application code."""

import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    archive_files={}
    with tarfile.open(ROOT/".trial/skill-source.tar") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            stream=archive.extractfile(member)
            archive_files[member.name.removeprefix("./")]=hashlib.sha256(stream.read()).hexdigest()
    (ROOT/"review/frozen-archive-hashes.json").write_text(json.dumps({"files":archive_files},indent=2),encoding="utf-8")
    for directory,files,output in [
        (ROOT/".agents/skills/vibelens/scripts/bo_observer/policy",["definition.py","bindings.py","runtime.py"],"native-policy-hashes.json"),
        (ROOT/".agents/skills/vibelens/scripts/bo_observer/adapters/python",["bo_executor.py"],"native-executor-hashes.json"),
    ]:
        hashes={("native_executor.py" if name=="bo_executor.py" else name):hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in files}
        (ROOT/"review"/output).write_text(json.dumps({"files":hashes},indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
