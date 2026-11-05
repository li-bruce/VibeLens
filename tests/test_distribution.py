"""Package parity and host-scoped controls are checked independently of prompts."""

import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "skills/vibelens/scripts")]
from build_distribution import build
from bo_observer.control.scope import ControlScope


class DistributionTests(unittest.TestCase):
    def test_complete_artifacts_preserve_canonical_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            output = Path(folder)
            report = build(output)
            self.assertEqual(build(output)["artifacts"], report["artifacts"])
            version = report["version"]
            with zipfile.ZipFile(output / f"vibelens-v{version}.zip") as archive:
                with tarfile.open(output / f"dsh-vibelens-{version}.tgz") as plugin:
                    for name, expected in report["skill_files"].items():
                        raw = archive.read("vibelens/" + name)
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, name)
                        self.assertEqual(plugin.extractfile("package/skill/" + name).read(), raw)
                    manifest = json.load(plugin.extractfile("package/package.json"))
                    self.assertNotIn("scripts", manifest)
                    self.assertIn("dsh", manifest["engines"])
                    self.assertTrue(all(member.isfile() for member in plugin.getmembers()))
                    self.assertIn("vibelens/README.md", archive.namelist())
                    for name in archive.namelist():
                        self.assertNotIn("node_modules", name)
                        self.assertNotIn("__pycache__", name)
            with zipfile.ZipFile(output / f"vibelens-skillhub-v{version}.zip") as catalog:
                self.assertLessEqual(len(catalog.infolist()), 200)
                self.assertLess(sum(item.file_size for item in catalog.infolist()), 10_000_000)
                catalog.extractall(output / "installed")
            installed = output / "installed/vibelens"
            spec = importlib.util.spec_from_file_location("vibelens_loader", installed / "bootstrap.py")
            loader = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loader)
            entry = loader.materialize(installed)
            self.assertEqual(entry.read_bytes(), (ROOT / "skills/vibelens/SKILL.md").read_bytes())
            self.assertEqual(loader.materialize(installed), entry)
            for name, expected in report["skill_files"].items():
                self.assertEqual(hashlib.sha256((entry.parent / name).read_bytes()).hexdigest(), expected)
            link = output / "linked-install"
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(installed)], check=True, capture_output=True)
            else:
                link.symlink_to(installed, target_is_directory=True)
            try:
                with self.assertRaisesRegex(ValueError, "symbolic links"):
                    loader.materialize(link)
            finally:
                link.rmdir() if os.name == "nt" else link.unlink()
            entry.write_text("modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Installed resource was modified"):
                loader.materialize(installed)
            (installed / "resources.zip.b64.txt").write_bytes(b"Y29ycnVwdA==")
            with self.assertRaisesRegex(ValueError, "checksum"):
                loader.materialize(installed)

    def test_hosts_and_conversations_do_not_share_activation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            codex, harness = ControlScope(folder), ControlScope(folder, "deepseek-harness")
            with patch.dict(os.environ, {"CODEX_THREAD_ID": "same-id"}):
                old = codex.activate("$vibelens", "project")
                expected = hashlib.sha256((str(Path(folder).resolve()) + "\0same-id").encode()).hexdigest()[:32]
                self.assertEqual(old["session"], expected, "Codex IDs remain stable")
                with self.assertRaisesRegex(ValueError, "host conversation ID"):
                    harness.activate("/vibelens start", "project")
                current = harness.activate("/vibelens start", "project", "same-id")
                self.assertNotEqual(current["session"], old["session"])
                self.assertEqual(current["host"], "deepseek-harness")
                for message in ["Example: /vibelens start", "> /vibelens start", "$vibelens"]:
                    with self.assertRaises(ValueError):
                        harness.activate(message, "project", "another-chat")
                with self.assertRaises(ValueError):
                    harness.authorized("/vibelens focus", "another-chat")
                harness.end("/vibelens stop", "same-id")
                self.assertTrue(codex.authorized("/vibelens focus")["active"])


if __name__ == "__main__":
    (ROOT / ".validation").mkdir(exist_ok=True)
    unittest.main()
