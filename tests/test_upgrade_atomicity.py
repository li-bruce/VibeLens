"""Managed upgrades preserve old bytes on a mid-apply failure."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
import bo_upgrade


class UpgradeAtomicityTests(unittest.TestCase):
    def test_failure_restores_every_original_and_metadata(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            for name in ("first.py", "second.py"):
                (root / name).write_bytes(b"original\n")
            metadata = root / "runtime.json"
            metadata.write_text('{"schema":1}\n', encoding="utf-8")
            proposed = {
                "valid": True,
                "changes": ["first.py", "second.py"],
                "sources": {"first.py": b"new first\n", "second.py": b"new second\n"},
                "retired_files": [],
                "conflicts": [],
                "metadata": metadata,
                "release": "test",
                "protocols": {},
                "files": {},
            }
            native_replace = Path.replace
            failed = False

            def locked_second(source, target):
                nonlocal failed
                if Path(target).name == "second.py" and not failed:
                    failed = True
                    raise PermissionError("simulated OS sharing failure")
                return native_replace(source, target)

            with (
                patch.object(bo_upgrade, "plan", return_value=proposed),
                patch.object(Path, "replace", locked_second),
            ):
                with self.assertRaises(PermissionError):
                    bo_upgrade.apply(root)
            self.assertTrue(failed)
            for name in ("first.py", "second.py"):
                self.assertEqual((root / name).read_bytes(), b"original\n")
            self.assertEqual(json.loads(metadata.read_text()), {"schema": 1})
            self.assertEqual(list(root.glob("*.upgrade-*")), [])

    def test_replacement_never_opens_the_existing_target_for_truncation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            target = Path(folder) / "module.py"
            target.write_bytes(b"old\n")
            native_open = Path.open

            def no_truncate(path, mode="r", *args, **kwargs):
                if path == target and "w" in mode:
                    raise OSError(22, "existing mapped read section")
                return native_open(path, mode, *args, **kwargs)

            with patch.object(Path, "open", no_truncate):
                bo_upgrade.replace_copy(b"new\n", target)
            self.assertEqual(target.read_bytes(), b"new\n")


if __name__ == "__main__":
    unittest.main()
