"""Fetch reviewed viewer assets without installing packages in the application.

The lock file is the delivery contract: one exact byte length and SHA-256 per
asset, an ordered CDN/GitHub source pair, and preserved license/source records.
Downloads are data only. This module never executes a package or unpacks an
archive. A verified content-addressed cache is shared by Skill installations.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ASSETS = Path(__file__).resolve().parents[3] / "assets/stategraph-viewer"
LOCK_NAME = "dependencies.lock.json"
MAX_ASSET_SIZE = 16 * 1024 * 1024
ALLOWED_HOSTS = {"cdn.jsdelivr.net", "raw.githubusercontent.com", "github.com"}


def locked_assets(directory):
    """Reject unsafe destinations and malformed pins before reading or writing files."""
    value = json.loads((Path(directory) / LOCK_NAME).read_text(encoding="utf-8"))
    if value.get("schema") != "vibelens-viewer-dependencies/v1":
        raise ValueError("Unsupported viewer dependency lock")
    entries = value.get("assets")
    if not isinstance(entries, list) or not entries:
        raise ValueError("The dependency lock must list reviewed assets")
    names = set()
    for entry in entries:
        name = entry.get("name", "")
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name)
            or name in names
            or name == LOCK_NAME
        ):
            raise ValueError("Unsafe or duplicate dependency name: " + name)
        names.add(name)
        if not re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", "")):
            raise ValueError("Missing SHA-256 pin: " + name)
        if type(entry.get("bytes")) is not int or not 0 < entry["bytes"] <= MAX_ASSET_SIZE:
            raise ValueError("Invalid dependency size: " + name)
        sources = entry.get("sources", [])
        if [item.get("kind") for item in sources] != ["cdn", "github"]:
            raise ValueError("Expected CDN then GitHub sources: " + name)
        for source in sources:
            parsed = urlsplit(source["url"])
            if (
                parsed.scheme != "https"
                or parsed.hostname not in ALLOWED_HOSTS
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 443)
                or parsed.fragment
                or parsed.query
            ):
                raise ValueError("Invalid pinned dependency URL: " + name)
        if urlsplit(sources[1]["url"]).hostname not in {"raw.githubusercontent.com", "github.com"}:
            raise ValueError("Fallback must use GitHub: " + name)
    return entries


def regular_path(path):
    """Do not follow symlinks or Windows junctions in managed output paths."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) in {
            0xA0000003,
            0xA000000C,
        }:
            raise ValueError("Dependency path contains a link: " + str(part))
    return path


def matches(path, entry):
    """Validate bytes, including warm installations and shared-cache hits."""
    if not path.is_file() or path.stat().st_size != entry["bytes"]:
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def cache_directory():
    """Keep downloaded assets outside both application source and Skill discovery."""
    configured = os.environ.get("VIBELENS_DEPENDENCY_CACHE")
    if configured:
        return Path(configured).expanduser()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
    return base / "VibeLens/dependencies"


def atomic_copy(data, target):
    """Publish a complete verified file; interrupted writes leave no partial asset."""
    regular_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".vibelens-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        regular_path(target)
        for attempt in range(8):
            try:
                # Another setup may have published these identical bytes while
                # we downloaded them. Avoid replacing a file it is verifying.
                if target.is_file() and target.read_bytes() == data:
                    return
                os.replace(temporary, target)
                break
            except PermissionError:
                # Windows denies replace while a short-lived reader holds the
                # destination open. Retry this sharing race, with a fixed bound.
                if os.name != "nt" or attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        Path(temporary).unlink(missing_ok=True)


def fetch(entry, source, *, opener=urlopen):
    """Read a bounded HTTPS response and reject a wrong version or partial download."""
    request = Request(source["url"], headers={"User-Agent": "VibeLens-dependency-setup/1"})
    with opener(request, timeout=15) as response:
        # urlopen follows redirects; reject HTTPS downgrades before consuming data.
        if urlsplit(response.geturl()).scheme != "https":
            raise ValueError("Dependency download redirected outside HTTPS")
        raw = response.read(entry["bytes"] + 1)
    if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError("Dependency checksum or length mismatch: " + entry["name"])
    return raw


def install_asset(directory, cache, entry, *, offline, repair, source, opener):
    """Use installed bytes, then cache, then the ordered download sources."""
    target = regular_path(directory / entry["name"])
    cached = regular_path(cache / entry["sha256"])
    if matches(target, entry):
        return {"name": entry["name"], "origin": "installed"}
    if target.exists() and not repair:
        raise ValueError(
            "Modified viewer dependency: " + entry["name"] + "; use --repair to restore it"
        )
    origin = "cache"
    attempts = []
    if matches(cached, entry):
        raw = cached.read_bytes()
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Dependency cache changed during setup: " + entry["name"])
    else:
        if offline:
            raise ValueError("Dependency unavailable offline: " + entry["name"])
        raw = None
        for location in entry["sources"]:
            if source == "github" and location["kind"] != "github":
                continue
            try:
                raw = fetch(entry, location, opener=opener)
                origin = location["kind"]
                break
            except (OSError, ValueError, URLError, HTTPException) as error:
                attempts.append({"source": location["kind"], "error": str(error)})
        if raw is None:
            raise ValueError("Cannot download " + entry["name"] + ": " + json.dumps(attempts))
        atomic_copy(raw, cached)
    # Recheck the target after a potentially slow download. Never overwrite a
    # concurrently edited file unless restoration was explicitly requested.
    if target.exists() and not repair and not matches(target, entry):
        raise ValueError("Viewer dependency changed during setup: " + entry["name"])
    atomic_copy(raw, target)
    return {"name": entry["name"], "origin": origin, "fallback": attempts}


def ensure_assets(
    directory=ASSETS, *, cache=None, offline=False, repair=False, source="auto", opener=urlopen
):
    """Materialize only locked files, preserving original viewer modules and views."""
    directory = regular_path(directory)
    entries = locked_assets(directory)
    cache = regular_path(cache or cache_directory())
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="vibelens-assets") as executor:
        results = list(
            executor.map(
                lambda entry: install_asset(
                    directory,
                    cache,
                    entry,
                    offline=offline,
                    repair=repair,
                    source=source,
                    opener=opener,
                ),
                entries,
            )
        )
    return {"valid": True, "assets": results, "bytes": sum(entry["bytes"] for entry in entries)}


def check_assets(directory=ASSETS):
    """Read-only verification; no network, cache repair or filesystem changes."""
    directory = regular_path(directory)
    problems = [
        entry["name"]
        for entry in locked_assets(directory)
        if not matches(regular_path(directory / entry["name"]), entry)
    ]
    return {"valid": not problems, "missing_or_modified": problems}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "check"), nargs="?", default="install")
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--repair", action="store_true", help="Restore only locked dependency files"
    )
    parser.add_argument("--source", choices=("auto", "github"), default="auto")
    args = parser.parse_args()
    try:
        result = (
            check_assets(args.assets)
            if args.action == "check"
            else ensure_assets(
                args.assets,
                cache=args.cache,
                offline=args.offline,
                repair=args.repair,
                source=args.source,
            )
        )
    except (OSError, ValueError) as error:
        result = {"valid": False, "error": str(error)}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
