"""Check published text and recordings against the archived original file bytes."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check():
    count = 0
    for version, phase in [(1, "red"), (2, "green")]:
        case = json.loads(
            (ROOT / f"docs/site/case-data/v{version}.json").read_text(encoding="utf-8")
        )
        with zipfile.ZipFile(
            ROOT / f"docs/review/file-sharing-demo/materials/{phase}.zip"
        ) as material:
            original = json.loads(material.read("recording.json"))
            assert case["recording"] == original, "Published recordings must remain original"
            with zipfile.ZipFile(BytesIO(material.read("source.zip"))) as archive:
                for name, text in case["sources"].items():
                    raw = archive.read(name)
                    expected = case["view"]["manifest"]["files"][name]
                    assert sha256(raw).hexdigest() == expected, name
                    assert raw.decode("utf-8-sig").replace("\r\n", "\n") == text.replace(
                        "\r\n", "\n"
                    ), name
                    assert text == original["sources"][name], name
                    assert case["source_checks"][name] == {
                        "manifest_sha256": expected,
                        "recorded_sha256": sha256(text.encode("utf-8")).hexdigest(),
                        "archive_sha256": sha256(raw).hexdigest(),
                    }
                    count += 1
    print(
        f"PASS: {count} source files match original archive bytes, captured text and build fingerprints."
    )


if __name__ == "__main__":
    check()
