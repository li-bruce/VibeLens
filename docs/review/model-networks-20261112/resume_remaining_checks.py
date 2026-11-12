"""Continue the unchanged full suite after its recorded Windows cleanup failure.

The prefix completed in full-check-release.log. The two affected watcher suites
were rerun separately after the shared cleanup fix. Execute every remaining AST
statement from tools/verify.py, including packaging and final acceptance, without
copying its commands or replacing any test/expectation.
"""

import ast
import hashlib
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
CHECKPOINT = "tools/test_assessment_fixes.py"


def main():
    prefix = (EVIDENCE / "full-check-release.log").read_text(encoding="utf-8")
    assert "test_watcher_survives_real_file_occupation_and_publishes_latest" in prefix
    assert "watch.log" in prefix and "WinError 32" in prefix
    for name in ("assessment-cleanup-retest.log", "watcher-cleanup-final.log"):
        retest = (EVIDENCE / name).read_text(encoding="utf-8")
        assert "\nOK" in retest and "FAILED" not in retest, name
    source = ROOT / "tools/verify.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    main_function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    points = [
        index
        for index, node in enumerate(main_function.body)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "run"
        and len(node.value.args) > 1
        and isinstance(node.value.args[1], ast.Constant)
        and node.value.args[1].value == CHECKPOINT
    ]
    assert len(points) == 1, "The verification entrypoint changed; review this checkpoint."
    print("Continuation after:", CHECKPOINT, flush=True)
    print("Original verifier SHA256:", hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
    sys.path.insert(0, str(ROOT / "tools"))
    namespace = runpy.run_path(str(source), run_name="vibelens_remaining_checks")
    remainder = ast.Module(body=main_function.body[points[0] + 1 :], type_ignores=[])
    exec(compile(remainder, str(source), "exec"), namespace)


if __name__ == "__main__":
    main()
