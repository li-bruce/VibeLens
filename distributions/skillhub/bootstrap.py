"""Verify and materialize bundled VibeLens source without network access.

Catalogs can limit file counts. The transport archive preserves canonical files;
this loader only expands that archive into a versioned directory beside itself.
Existing extracted files are verified on every invocation, never overwritten.
The canonical Skill separately prepares pinned viewer dependencies on first use.
"""

import base64
import binascii
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


def linked_path(path):
    """Recognize symlinks and Windows junctions, including on Python 3.11."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    # pathlib.is_junction is only available from Python 3.12 onward.
    return stat.S_ISLNK(info.st_mode) or getattr(info, "st_reparse_tag", 0) in {
        0xA0000003,  # IO_REPARSE_TAG_MOUNT_POINT (directory junction)
        0xA000000C,  # IO_REPARSE_TAG_SYMLINK
    }


def materialize(directory):
    """Return the verified canonical entrypoint, rejecting unsafe or modified files."""
    directory = Path(directory).absolute()
    manifest = json.loads((directory / "resources.json").read_text(encoding="utf-8"))
    # The catalog preserves text resources but filters nested ZIP files. Decode
    # the explicitly named transport, then verify the original archive checksum.
    encoded = (directory / "resources.zip.b64.txt").read_bytes().strip()
    payload = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
        raise ValueError("The bundled VibeLens resources do not match their checksum")
    version = manifest["version"]
    if not version or any(character not in "0123456789." for character in version):
        raise ValueError("Invalid package version")
    output = directory / "runtime" / version
    # Do not follow an existing user-created link out of the installation.
    for parent in (directory, directory / "runtime", output):
        if linked_path(parent):
            raise ValueError("VibeLens resource directories cannot be symbolic links")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        expected = {"vibelens/" + name: digest for name, digest in manifest["files"].items()}
        if set(archive.namelist()) != set(expected) or len(archive.namelist()) != len(expected):
            raise ValueError("Unexpected or duplicate resource members")
        # Validate the entire archive before creating any output.
        verified = []
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in member.filename
                or ":" in member.filename
                or relative.parts[0] != "vibelens"
                or (member.external_attr >> 16) & 0o170000 not in (0, 0o100000)
            ):
                raise ValueError("Unsafe resource path")
            raw = archive.read(member)
            if hashlib.sha256(raw).hexdigest() != expected[member.filename]:
                raise ValueError("Modified resource: " + member.filename)
            target = output.joinpath(*relative.parts)
            for parent in (target, *target.parents):
                if parent == directory:
                    break
                if linked_path(parent):
                    raise ValueError("Resource path contains a symbolic link")
            if target.exists() and target.read_bytes() != raw:
                raise ValueError("Installed resource was modified: " + member.filename)
            verified.append((target, raw))
        for target, raw in verified:
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation preserves an existing file on concurrent runs.
            try:
                with target.open("xb") as stream:
                    stream.write(raw)
            except FileExistsError:
                if target.read_bytes() != raw:
                    raise ValueError("Concurrent resource write: " + str(target))
    return output / "vibelens/SKILL.md"


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        raise SystemExit("VibeLens requires Python 3.11 or newer")
    try:
        print(materialize(Path(__file__).parent))
    except (OSError, ValueError, KeyError, binascii.Error, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from error
