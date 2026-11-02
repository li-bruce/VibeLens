"""Install only the staged Git Skill in an isolated project and run its interfaces."""

from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def run(cwd, *args):
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", *map(str, args)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
    )
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    return result.stdout


def main():
    tree = subprocess.check_output(["git", "write-tree"], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(
        ["git", "archive", "--format=zip", tree, "skills/vibelens", "tools/install_skill.py"],
        cwd=ROOT,
    )
    with tempfile.TemporaryDirectory(prefix="test-install-", dir=ROOT / ".validation") as folder:
        base = Path(folder).resolve()
        if not base.is_relative_to((ROOT / ".validation").resolve()):
            raise ValueError("Installation smoke directory escaped validation root")
        exported = base / "repository"
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.extractall(exported)
        project = base / "project"
        project.mkdir()
        run(exported, exported / "tools/install_skill.py", "--project", project)
        installed = project / ".agents/skills/vibelens"
        policy = (installed / "agents/openai.yaml").read_text(encoding="utf-8")
        if "allow_implicit_invocation: false" not in policy:
            raise AssertionError("Explicit-only activation was lost")
        run(project, installed / "scripts/bo_relations.py", "--help")
        fixture = json.loads((OUT / "dialogue-case.json").read_text(encoding="utf-8"))
        (project / "discovery.json").write_text(json.dumps(fixture["answered"]), encoding="utf-8")
        (project / "previous.json").write_text(json.dumps(fixture["previous"]), encoding="utf-8")
        checked = json.loads(
            run(
                project,
                installed / "scripts/requirements_dialogue.py",
                "check",
                "--file",
                project / "discovery.json",
                "--previous",
                project / "previous.json",
            )
        )
        if not checked["ready"]:
            raise AssertionError("Installed clarification failed")
        preview = run(
            project,
            installed / "scripts/bo_design.py",
            "preview",
            "--root",
            project,
            "--nodes",
            "business.allowed",
            "business.download",
            "--url",
            "http://127.0.0.1:8123/graph",
        )
        if "Recipient and share still active" not in preview or "Withdraw share" not in preview:
            raise AssertionError("Installed graph did not reflect the new decision")
        source = exported / "skills/vibelens/references/iteration-dialogue.md"
        target = installed / "references/iteration-dialogue.md"
        if source.read_bytes() != target.read_bytes():
            raise AssertionError("Installed guidance differs from staged Git")
        report = {
            "valid": True,
            "staged_tree": tree,
            "scope": "Only the staged Skill directory and installer were exported; no installed runtime or source was borrowed.",
            "checks": [
                "complete project-local installation",
                "explicit-only activation",
                "relation CLI",
                "later-turn decision history",
                "local diagram from updated discovery",
                "exact installed guidance",
            ],
            "guidance_sha256": sha256(target.read_bytes()).hexdigest(),
        }
        (OUT / "clean-install.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"valid": True, "checks": len(report["checks"]), "tree": tree}))


if __name__ == "__main__":
    main()
