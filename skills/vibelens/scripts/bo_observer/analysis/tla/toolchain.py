"""Resolve the optional observer-local TLC tool; never install it in an app.

The distribution is hash pinned. Java 17 is supplied by the developer and its
exact executable/version is recorded. Verification never triggers a download.
"""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import urllib.request

VERSION = "1.7.4"
JAR_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"
MAX_JAR_BYTES = 8 * 1024 * 1024


def sha256(path):
    """Hash file bytes without loading a whole tool or artifact into memory."""
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_path():
    return Path.home() / ".cache" / "vibelens" / "tools" / ("tlc-" + VERSION) / "tla2tools.jar"


def install():
    """Explicit opt-in download; replace the cache only after checksum verification."""
    target = cache_path()
    if target.is_file() and sha256(target) == JAR_SHA256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    import tempfile

    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            with urllib.request.urlopen(URL, timeout=30) as source:
                data = source.read(MAX_JAR_BYTES + 1)
            if len(data) > MAX_JAR_BYTES or hashlib.sha256(data).hexdigest() != JAR_SHA256:
                raise ValueError("TLC download does not match the pinned distribution")
            output.write(data)
        except BaseException:
            output.close()
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(target)
    return target


def isolated_environment(directory):
    """Keep only OS essentials; application credentials and Java option injection stay out."""
    result = {
        key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "COMSPEC") if key in os.environ
    }
    result.update(TEMP=str(directory), TMP=str(directory), TMPDIR=str(directory), LANG="C.UTF-8")
    return result


def resolve(java=None, jar=None):
    """Validate caller-selected tooling, returning paths plus reproducible identity."""
    import shutil

    java = java or os.environ.get("VIBELENS_JAVA") or shutil.which("java")
    jar = Path(jar or os.environ.get("VIBELENS_TLC_JAR") or cache_path()).resolve()
    if not java or not Path(java).is_file() or not jar.is_file():
        raise FileNotFoundError(
            "Install Java 17 and run bo_analyze.py install-tool, or select VIBELENS_TLC_JAR"
        )
    java = Path(java).resolve()
    if sha256(jar) != JAR_SHA256:
        raise ValueError("TLC checksum differs from the tested distribution")
    output = subprocess.run(
        [str(java), "-Dfile.encoding=UTF-8", "-version"],
        capture_output=True,
        timeout=10,
        env=isolated_environment(jar.parent),
        encoding="utf-8",
        errors="replace",
    )
    version = output.stdout + output.stderr
    if output.returncode or not re.search(r'version "17[.\"]', version):
        raise ValueError("This adapter requires a Java 17 runtime")
    release = java.parent.parent / "release"
    identity = {
        "tlc_version": VERSION,
        "tlc_sha256": JAR_SHA256,
        "java_version": version.strip(),
        "java_executable_sha256": sha256(java),
        "java_release_sha256": sha256(release) if release.is_file() else None,
    }
    return java, jar, identity
