"""Exercise delivery failures, verified reuse and application isolation."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.client import IncompleteRead
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.delivery.dependencies import (
    LOCK_NAME,
    check_assets,
    ensure_assets,
    locked_assets,
)


class Response(io.BytesIO):
    def geturl(self):
        return "https://cdn.jsdelivr.net/reviewed/asset"


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "skill/assets/stategraph-viewer"
        self.assets.mkdir(parents=True)
        self.cache = self.root / "cache"
        self.raw = b"reviewed third-party code"
        self.entry = {
            "name": "library.js",
            "bytes": len(self.raw),
            "sha256": hashlib.sha256(self.raw).hexdigest(),
            "sources": [
                {"kind": "cdn", "url": "https://cdn.jsdelivr.net/npm/example@1.2.3/library.js"},
                {
                    "kind": "github",
                    "url": "https://raw.githubusercontent.com/example/library/0123456789abcdef/library.js",
                },
            ],
        }
        self.write_lock([self.entry])
        (self.assets / "viewer.js").write_bytes(b"owned viewer")
        self.application = self.root / "app"
        self.application.mkdir()
        (self.application / "business.py").write_bytes(b"business source")

    def write_lock(self, entries):
        (self.assets / LOCK_NAME).write_text(
            json.dumps(
                {
                    "schema": "vibelens-viewer-dependencies/v1",
                    "assets": entries,
                }
            ),
            encoding="utf-8",
        )

    def install(self, **options):
        return ensure_assets(self.assets, cache=self.cache, **options)

    def test_primary_then_verified_offline_reuse(self):
        calls = []

        def network(request, timeout):
            calls.append(request.full_url)
            return Response(self.raw)

        self.assertEqual(self.install(opener=network)["assets"][0]["origin"], "cdn")
        (self.assets / "library.js").unlink()
        self.assertEqual(self.install(offline=True)["assets"][0]["origin"], "cache")
        self.assertEqual(len(calls), 1)
        self.assertTrue(check_assets(self.assets)["valid"])
        self.assertEqual((self.assets / "viewer.js").read_bytes(), b"owned viewer")
        self.assertEqual(list(self.application.iterdir()), [self.application / "business.py"])

    def test_primary_error_or_wrong_bytes_use_github(self):
        for failure in ("unavailable", "wrong bytes", "interrupted response"):
            with self.subTest(failure=failure):
                calls = []

                def network(request, timeout):
                    calls.append(request.full_url)
                    if "cdn.jsdelivr" in request.full_url:
                        if failure == "unavailable":
                            raise URLError("simulated CDN outage")
                        if failure == "interrupted response":
                            raise IncompleteRead(b"partial", 100)
                        return Response(b"unreviewed binary")
                    return Response(self.raw)

                result = self.install(opener=network)
                self.assertEqual(result["assets"][0]["origin"], "github")
                self.assertEqual(len(result["assets"][0]["fallback"]), 1)
                self.assertEqual(len(calls), 2)
                (self.assets / "library.js").unlink()
                (self.cache / self.entry["sha256"]).unlink()

    def test_all_sources_wrong_leave_no_partial_asset(self):
        with self.assertRaisesRegex(ValueError, "Cannot download"):
            self.install(opener=lambda *a, **k: Response(b"wrong"))
        self.assertFalse((self.assets / "library.js").exists())
        self.assertFalse(self.cache.exists())

    def test_offline_missing_is_clear_and_makes_no_network_call(self):
        with self.assertRaisesRegex(ValueError, "unavailable offline"):
            self.install(offline=True, opener=lambda *a, **k: self.fail("network"))
        self.assertEqual(check_assets(self.assets)["missing_or_modified"], ["library.js"])

    def test_upgrade_cannot_retire_assets_from_an_unprepared_skill(self):
        from bo_upgrade import plan
        scripts = self.root / "skill/scripts"
        scripts.mkdir()
        with self.assertRaisesRegex(ValueError, "before planning an upgrade"):
            plan(self.application, source=scripts, runtime="observer", viewers=["local-viewer"])
        self.assertEqual(list(self.application.iterdir()), [self.application / "business.py"])

    def test_modified_install_requires_explicit_repair(self):
        (self.assets / "library.js").write_bytes(b"local modification")
        with self.assertRaisesRegex(ValueError, "Modified viewer dependency"):
            self.install(opener=lambda *a, **k: self.fail("network"))
        self.assertEqual((self.assets / "library.js").read_bytes(), b"local modification")
        self.install(repair=True, opener=lambda *a, **k: Response(self.raw))
        self.assertTrue(check_assets(self.assets)["valid"])

    def test_corrupted_cache_is_not_trusted(self):
        self.cache.mkdir()
        (self.cache / self.entry["sha256"]).write_bytes(b"wrong cache")
        with self.assertRaisesRegex(ValueError, "unavailable offline"):
            self.install(offline=True)
        self.install(opener=lambda *a, **k: Response(self.raw))
        self.assertEqual((self.cache / self.entry["sha256"]).read_bytes(), self.raw)

    def test_interrupted_write_keeps_existing_asset(self):
        target = self.assets / "library.js"
        target.write_bytes(b"original")
        with patch(
            "bo_observer.delivery.dependencies.os.replace", side_effect=OSError("interrupted")
        ):
            with self.assertRaisesRegex(OSError, "interrupted"):
                self.install(repair=True, opener=lambda *a, **k: Response(self.raw))
        self.assertEqual(target.read_bytes(), b"original")
        self.assertFalse(list(self.root.rglob(".vibelens-*")))

    def test_concurrent_setup_publishes_complete_equal_files(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: self.install(opener=lambda *a, **k: Response(self.raw)), range(2)
                )
            )
        self.assertTrue(all(result["valid"] for result in results))
        self.assertTrue(check_assets(self.assets)["valid"])

    def test_unsafe_names_duplicates_and_insecure_sources_are_rejected(self):
        for name in ("../business.py", "/abs", "a:b", "a\\b", LOCK_NAME):
            with self.subTest(name=name):
                self.write_lock([{**self.entry, "name": name}])
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    locked_assets(self.assets)
        self.write_lock([self.entry, self.entry])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            locked_assets(self.assets)
        bad = json.loads(json.dumps(self.entry))
        bad["sources"][0]["url"] = "http://cdn.jsdelivr.net/file"
        self.write_lock([bad])
        with self.assertRaisesRegex(ValueError, "URL"):
            locked_assets(self.assets)

    def test_redirect_to_plain_http_is_rejected(self):
        class UnsafeResponse(Response):
            def geturl(self):
                return "http://example.com/file"

        with self.assertRaisesRegex(ValueError, "outside HTTPS"):
            self.install(opener=lambda *a, **k: UnsafeResponse(self.raw))

    def test_known_skill_locks_match_all_example_locks(self):
        canonical = ROOT / "skills/vibelens/assets/stategraph-viewer" / LOCK_NAME
        for relative in (
            "examples/delivery/integrations/bo_view",
            "examples/delivery/observer_generated/static",
            "examples/team-archive/static/graph",
        ):
            self.assertEqual((ROOT / relative / LOCK_NAME).read_bytes(), canonical.read_bytes())

    def test_linked_destination_is_rejected(self):
        target = self.assets / "library.js"
        try:
            target.symlink_to(self.application / "business.py")
        except OSError:
            if os.name != "nt":
                raise
            # Windows normally disallows unprivileged file symlinks, but a
            # directory junction exercises the same managed-path escape guard.
            subprocess.run(["cmd", "/c", "mklink", "/J", str(self.cache),
                str(self.application)], capture_output=True, check=True)
            self.addCleanup(self.cache.rmdir)
        with self.assertRaisesRegex(ValueError, "contains a link"):
            self.install(opener=lambda *a, **k: Response(self.raw))
        self.assertEqual((self.application / "business.py").read_bytes(), b"business source")


if __name__ == "__main__":
    unittest.main()
