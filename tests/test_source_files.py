"""Source verification reads real bytes and preserves physical containment."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.graph.source_files import SourceFiles


class SourceFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        (self.root / "app").mkdir()
        self.file = self.root / "app/service.py"
        self.file.write_bytes(b"value = 1\n")

    def tearDown(self):
        self.folder.cleanup()

    def test_rereads_same_size_content_with_restored_timestamp(self):
        initial = self.file.stat()
        self.assertEqual(SourceFiles(self.root).read("app/service.py"), b"value = 1\n")
        self.file.write_bytes(b"value = 2\n")
        os.utime(self.file, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        self.assertEqual(SourceFiles(self.root).read("app/service.py"), b"value = 2\n")

    def test_missing_directory_and_nonfile_stay_missing(self):
        self.file.unlink()
        reader = SourceFiles(self.root)
        self.assertIsNone(reader.read("app/service.py"))
        self.assertIsNone(reader.read("missing/service.py"))
        self.assertIsNone(reader.read("app"))
        self.assertIsNone(reader.read("."))

    def test_absolute_and_parent_paths_are_rejected(self):
        reader = SourceFiles(self.root)
        for value in [str(self.file.resolve()), "../source.py", "app/../source.py"]:
            with self.assertRaisesRegex(ValueError, "contained relative"):
                reader.read(value)

    def directory_link(self, link, target):
        if os.name == "nt":
            # No administrator or developer-mode requirement for a directory junction.
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)

    def test_internal_directory_link_reads_actual_target(self):
        link = self.root / "linked"
        self.directory_link(link, self.root / "app")
        try:
            self.assertEqual(SourceFiles(self.root).read("linked/service.py"), b"value = 1\n")
        finally:
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()

    def test_outside_directory_link_is_rejected_even_for_matching_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as external:
            (Path(external) / "service.py").write_bytes(b"value = 1\n")
            link = self.root / "linked"
            self.directory_link(link, Path(external))
            try:
                with self.assertRaisesRegex(ValueError, "escapes project"):
                    SourceFiles(self.root).read("linked/service.py")
            finally:
                if os.name == "nt":
                    link.rmdir()
                else:
                    link.unlink()

    def test_replaced_parent_is_rechecked_within_the_same_pass(self):
        reader = SourceFiles(self.root)
        self.assertEqual(reader.read("app/service.py"), b"value = 1\n")
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as external:
            (Path(external) / "service.py").write_bytes(b"value = 1\n")
            self.file.unlink()
            link = self.root / "app"
            link.rmdir()  # This contains only the synthetic file removed above.
            self.directory_link(link, Path(external))
            try:
                with self.assertRaisesRegex(ValueError, "escapes project"):
                    reader.read("app/service.py")
            finally:
                if os.name == "nt":
                    link.rmdir()
                else:
                    link.unlink()


if __name__ == "__main__":
    unittest.main()
