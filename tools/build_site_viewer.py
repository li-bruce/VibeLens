"""Assemble the Pages case viewer from the exact maintained VibeLens assets.

Generated copies stay out of Git. The only HTML changes are relative asset URLs
and the static-case entrypoint; renderer, layout and interaction code is unchanged.
"""

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/vibelens/assets/stategraph-viewer"
TARGET = ROOT / "docs/site/viewer"


def build():
    """Copy canonical files and retain their hashes for reproducibility checks."""
    TARGET.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for source in SOURCE.iterdir():
        if not source.is_file():
            continue
        target = TARGET / source.name
        shutil.copyfile(source, target)
        hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    html = (SOURCE / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/', 'href="./').replace('src="/', 'src="./')
    html = html.replace('src="./viewer.js"', 'src="../case-viewer.mjs?rev=story-1"')
    (TARGET / "index.html").write_text(html, encoding="utf-8")
    (TARGET / "asset-proof.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(f"Built Pages case viewer from {len(hashes)} canonical files")


if __name__ == "__main__":
    build()
