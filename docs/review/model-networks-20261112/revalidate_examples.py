"""Revalidate the managed-runtime upgrade from the preserved Git baseline.

This acceptance recipe first checks and begins a change in an unmodified Git
export. Only then does it copy the reviewed working-tree implementation. Existing
business classifications are reused only for identical source bytes. Every
configured project check runs before the new approval is frozen for distribution.
"""

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
WORK = ROOT / ".validation/model-networks-release-retest"
CHANGE = "model-networks-20261112"
FROZEN_CHANGE = CHANGE + "-verified"
RUN = "example-upgrade-complete"
REASON = (
    "Upgrade the isolated VibeLens runtime to named model registries, explicit "
    "model-qualified observations and independent subnet views. Application "
    "sources, state definitions, business rules and independent scenario "
    "expectations remain unchanged."
)
ENV = {
    **os.environ,
    "BO_ADAPTER_HOME": str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def command(project, runtime, stage, action, *args, baseline=False):
    """Keep exact command output, including failures, before interpreting it."""
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            runtime + "/change_sync.py",
            action,
            "--root",
            ".",
            *args,
        ],
        cwd=project,
        env={**ENV, "VIBELENS_SKILL": str((WORK if baseline else ROOT) / "skills/vibelens")},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write(
        EVIDENCE / RUN / project.name / (stage + ".json"),
        {
            "action": action,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    print(project.name, stage, result.returncode, flush=True)
    if result.returncode and action != "inspect":
        raise RuntimeError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def main():
    if not WORK.exists():
        WORK.mkdir(parents=True)
        archive = subprocess.check_output(
            [
                "git",
                "archive",
                "--format=zip",
                "476d2d93",
                "examples/delivery",
                "examples/team-archive",
                "skills/vibelens",
            ],
            cwd=ROOT,
        )
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            source.extractall(WORK)
    files = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "examples/delivery",
                "examples/team-archive",
            ],
            cwd=ROOT,
        )
        .decode("utf-8")
        .split("\0")
    )
    dependencies = WORK / "examples/multilanguage"
    dependencies.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        (dependencies / name).write_bytes(
            subprocess.check_output(
                [
                    "git",
                    "show",
                    "476d2d93:examples/multilanguage/" + name,
                ],
                cwd=ROOT,
            )
        )
    installed = subprocess.run(
        [
            "npm.cmd" if os.name == "nt" else "npm",
            "ci",
            "--prefix",
            str(dependencies),
            "--no-audit",
            "--no-fund",
        ],
        cwd=WORK,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    write(
        EVIDENCE / RUN / "test-dependencies.json",
        {
            "exit_code": installed.returncode,
            "stdout": installed.stdout,
            "stderr": installed.stderr,
            "source": "Base commit examples/multilanguage/package-lock.json",
        },
    )
    installed.check_returncode()
    for name, runtime, manifest in (
        ("delivery", "observer_generated/runtime", "observer_generated/manifest.json"),
        ("team-archive", "observer_runtime", "manifest.json"),
    ):
        project = WORK / "examples" / name
        original = ROOT / "examples" / name
        if (original / ".release/stategraph" / FROZEN_CHANGE).exists():
            command(project, runtime, "09-frozen-recheck", "check")
            continue
        change = project / ".stategraph" / CHANGE
        if change.exists():
            # Resume the same change, preserving its original baseline and the
            # failed project-command evidence before rerunning unchanged checks.
            prior_checks = EVIDENCE / RUN / name / "prior-checks"
            if (change / "checks").exists() and not prior_checks.exists():
                shutil.copytree(change / "checks", prior_checks)
            for filename in ("verification.json", "review.json", "accepted.json"):
                if (change / filename).exists():
                    shutil.copyfile(change / filename, prior_checks.parent / ("prior-" + filename))
            overlay(project, files)
            impact = command(project, runtime, "05-inspect-retest", "inspect")
            review = read(change / "review.json")
            review["candidate_id"] = impact["candidate_id"]
            # Application declarations and expectations are byte-identical; the
            # only further change fixes package imports in managed tool modules.
            for source in read(project / "sync.json")["code_files"]:
                if isinstance(source, str):
                    current_bytes = (project / source).read_bytes()
                    git_bytes = subprocess.check_output(
                        ["git", "show", "476d2d93:examples/" + name + "/" + source], cwd=ROOT
                    )
                    if current_bytes.replace(b"\r\n", b"\n") != git_bytes.replace(b"\r\n", b"\n"):
                        raise ValueError(
                            "Application source changed; manual review needed: " + source
                        )
            write(change / "review.json", review)
            (project / "scratch").mkdir(exist_ok=True)
            command(project, runtime, "06-verify-retest", "verify")
            command(project, runtime, "07-accept-retest", "accept")
            command(project, runtime, "08-check-retest", "check")
            freeze(project, original, manifest)
            continue
        frozen = project / ".release/stategraph"
        previous = Path(read(frozen / "active.json")["change"]).name
        prior_review = read(frozen / previous / "review.json")
        source_bytes = {
            symbol: (project / symbol.split("::")[0]).read_bytes()
            for symbol in prior_review["excluded_symbols"]
        }
        shutil.copytree(frozen, project / ".stategraph")
        shutil.copyfile(project / ".release/manifest.json", project / manifest)
        command(project, runtime, "00-baseline", "check", baseline=True)
        command(
            project,
            runtime,
            "01-begin",
            "begin",
            "--change",
            ".stategraph/" + CHANGE,
            "--request",
            REASON,
            baseline=True,
        )
        overlay(project, files)
        impact = command(project, runtime, "02-inspect", "inspect")
        review = {
            "candidate_id": impact["candidate_id"],
            "excluded_symbols": {
                symbol: prior_review["excluded_symbols"][symbol]
                for symbol, data in source_bytes.items()
                if (project / symbol.split("::")[0]).read_bytes() == data
            },
            "requirement_changes": {},
            "decisions": {
                part: {
                    "action": "updated" if part in ("abstraction", "probes") else "unchanged",
                    "reason": REASON,
                }
                for part in ("business", "state_machine", "abstraction", "probes")
            },
        }
        write(project / ".stategraph" / CHANGE / "review.json", review)
        (project / "scratch").mkdir(exist_ok=True)
        command(project, runtime, "03-verify", "verify")
        command(project, runtime, "04-accept", "accept")
        command(project, runtime, "05-check", "check")
        freeze(project, original, manifest)


def freeze(project, original, manifest):
    """Add a new approval; leave every historical approval intact."""
    for target in (original / ".release/stategraph", original / ".stategraph"):
        shutil.copytree(project / ".stategraph" / CHANGE, target / FROZEN_CHANGE)
        write(target / "active.json", {"change": ".stategraph/" + FROZEN_CHANGE})
        for filename in ("source-baseline.json", "maintenance.json"):
            shutil.copyfile(project / ".stategraph" / filename, target / filename)
    shutil.copyfile(project / manifest, original / ".release/manifest.json")
    shutil.copyfile(project / manifest, original / manifest)


def overlay(project, files):
    """Copy reviewed source only; preserve baselines and existing acceptance evidence."""
    for relative in files:
        if not relative.startswith("examples/" + project.name + "/") or "/.release/" in relative:
            continue
        source = ROOT / relative
        if source.is_file():
            target = WORK / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


if __name__ == "__main__":
    main()
