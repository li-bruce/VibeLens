"""Check owned-source boundaries and prove that lint rejects real invalid code."""

import hashlib
import json
import tempfile
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_scope import owned_sources

sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))


class SourceQualityTests(unittest.TestCase):
    def test_vendor_and_generated_code_are_outside_owned_scope(self):
        groups = owned_sources()
        names = groups["python"] + groups["javascript"] + groups["presentation"]
        self.assertGreater(len(groups["python"]), 90)
        self.assertIn("skills/vibelens/assets/stategraph-viewer/detail-panel.js", names)
        self.assertFalse(
            any(
                ".vendor." in n or "/node_modules/" in n or "/.release/" in n
                for n in names
            )
        )
        self.assertFalse(any(n.endswith("node-icons.js") for n in names))

    def test_python_lint_rejects_undefined_binding(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--config",
                "tools/formatting/ruff.toml",
                "--stdin-filename",
                "skills/vibelens/scripts/bo.py",
                "-",
            ],
            input="def broken():\n    return absent_runtime_binding\n",
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("F821", result.stdout)

    def test_javascript_lint_rejects_undefined_binding_and_duplicate_keys(self):
        source = "export const broken={a:1,a:absentGraphValue};"
        result = subprocess.run(
            [
                "node",
                "tools/formatting/node_modules/eslint/bin/eslint.js",
                "--config",
                "tools/formatting/eslint.config.mjs",
                "--stdin",
                "--stdin-filename",
                "skills/vibelens/assets/stategraph-viewer/viewer.js",
            ],
            input=source,
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-undef", result.stdout)
        self.assertIn("no-dupe-keys", result.stdout)

    def test_fixture_sync_rejects_stale_source_before_writing(self):
        from sync_runtime import verify_mode_bindings

        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "bo_stategraph").mkdir()
            source = root / "app.py"
            source.write_text("value = 1\n", encoding="utf-8")
            manifest = root / "bo_stategraph/sources.json"
            manifest.write_text(
                json.dumps(
                    {
                        "files": {
                            "app.py": hashlib.sha256(source.read_bytes()).hexdigest()
                        }
                    }
                ),
                encoding="utf-8",
            )
            verify_mode_bindings(root)
            before = manifest.read_bytes()
            source.write_text("value = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already stale"):
                verify_mode_bindings(root)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertEqual(source.read_text(encoding="utf-8"), "value = 2\n")

    def test_collector_entrypoint_preserves_the_public_session_class(self):
        from bo_observer.service import GraphSession
        from bo_observer.observation.session import GraphSession as Session

        self.assertIs(GraphSession, Session)


if __name__ == "__main__":
    unittest.main()
