"""Build complete, reproducible Skill and Harness packages from owned files.

The canonical Skill is copied byte-for-byte into both archives. Packaging never
rewrites the state engine or installs into a user's agent configuration.
"""

import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def owned_files(folder):
    """Use Git's source boundary, including new owned files, excluding caches."""
    result = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            folder,
        ],
        cwd=ROOT,
    )
    files = {}
    for name in sorted(set(result.decode("utf-8").split("\0")) - {""}):
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Package member leaves the source tree: {name}")
        if path.is_file():
            files[path.relative_to(ROOT / folder).as_posix()] = path.read_bytes()
    return files


def write_zip(path, files):
    """Fix member order, timestamps and permissions so equal sources hash alike."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def write_npm_tarball(path, files):
    """Use npm's package/ layout, with no installation-time build scripts."""
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed,
    ):
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, data in sorted(files.items()):
                info = tarfile.TarInfo("package/" + name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                archive.addfile(info, io.BytesIO(data))


def build(output):
    """Return artifact identities and exact source hashes for later verification."""
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(
        (ROOT / "plugins/deepseek-harness/package.json").read_text(encoding="utf-8")
    )
    version = manifest["version"]
    skill = owned_files("skills/vibelens")
    if f'version: "{version}"' not in skill["SKILL.md"].decode("utf-8"):
        raise ValueError("Skill metadata and Harness version differ")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a release version, not a path or moving branch")
    plugin = owned_files("plugins/deepseek-harness")
    # Only runtime, translations and consumer documentation enter the plugin.
    plugin = {
        name: data
        for name, data in plugin.items()
        if name in {"package.json", "index.mjs", "cordis.patch.yml", "README.md"}
        or name.startswith("locale/")
    }
    plugin.update({"skill/" + name: data for name, data in skill.items()})
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        plugin[name] = (ROOT / name).read_bytes()
    zip_path = output / f"vibelens-v{version}.zip"
    plugin_path = output / f"dsh-vibelens-{version}.tgz"
    write_zip(zip_path, {"vibelens/" + name: data for name, data in skill.items()})
    write_npm_tarball(plugin_path, plugin)
    # SkillHub accepts at most 200 files. Ship the complete archive as one local
    # resource with a small, checksummed bootstrap; do not omit runtime modules.
    catalog = owned_files("distributions/skillhub")
    catalog.update(
        {
            # SkillHub drops nested binary archives during upload. This named
            # text encoding carries the same ZIP bytes, not a reduced runtime.
            "resources.zip.b64.txt": base64.b64encode(zip_path.read_bytes()) + b"\n",
            "resources.json": (
                json.dumps(
                    {
                        "version": version,
                        "sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                        "files": {
                            name: hashlib.sha256(data).hexdigest() for name, data in skill.items()
                        },
                    },
                    indent=2,
                )
                + "\n"
            ).encode(),
            "README.md": skill["README.md"],
            # Catalog uploads reject extensionless files; preserve the license bytes.
            "LICENSE.txt": (ROOT / "LICENSE").read_bytes(),
            "agents/openai.yaml": skill["agents/openai.yaml"],
        }
    )
    catalog_path = output / f"vibelens-skillhub-v{version}.zip"
    write_zip(catalog_path, {"vibelens/" + name: data for name, data in catalog.items()})
    artifacts = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (zip_path, plugin_path, catalog_path)
    }
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in artifacts.items()),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "version": version,
        "artifacts": artifacts,
        "skill_files": {name: hashlib.sha256(data).hexdigest() for name, data in skill.items()},
    }
    (output / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / ".validation/distribution")
    args = parser.parse_args()
    result = build(args.out.resolve())
    print(
        json.dumps(
            {
                "version": result["version"],
                "artifacts": result["artifacts"],
                "skill_files": len(result["skill_files"]),
            }
        )
    )
