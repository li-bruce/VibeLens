"""Summarize completed release gates without replacing their original evidence."""

import json
from pathlib import Path


def main():
    """Require every named check and retain pending independent-trial scope."""
    directory = Path(__file__).resolve().parent
    receipts = (
        "full-verification-04.json",
        "source-quality-frozen-final.json",
        "package-frozen-final.json",
        "document-links-release-final.json",
        "clean-staged-export-final.json",
        "clean-staged-export-report.json",
        "skill-validation-final.json",
        "independent-final-audit.json",
        "examples-delivery-api-focus-final-acceptance-summary.json",
        "examples-team-archive-api-focus-final-acceptance-summary.json",
    )
    checks = []
    for name in receipts:
        result = json.loads((directory / name).read_text(encoding="utf-8"))
        assert result.get("valid") is True, name
        checks.append({"receipt": name, "valid": True})
    report = {
        "valid": True,
        "checks": checks,
        "scope": "Release gates; original failures and retests remain separate",
        "fresh_dialogue": "Pending publication and GitHub installation",
    }
    (directory / "final-release-gate.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
