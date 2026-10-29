"""Reuse prior evidence auditing with new explicit candidate scope; preserve prior files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREVIOUS = ROOT / "review/framework-upgrade-b78f03a"
def adapt(name, replacements):
    text = (PREVIOUS / name).read_text(encoding="utf-8")
    for old, new in replacements:
        assert old in text, (name, old)
        text = text.replace(old, new)
    (OUT / name).write_text(text, encoding="utf-8")

adapt("finalize.py", [
    ('"static/graph/analysis.js", "static/graph/recording.js"', '"static/graph/semantic-view.js"'),
    ('name == "v2-source.zip"', 'name == "b78-source.zip"'),
    ('"review/browser/20261029T034258Z-7c262b/recording.json"):',
     '"review/browser/20261029T034258Z-7c262b/recording.json",\n             "review/framework-upgrade-b78f03a/keyboard-source-acceptance.json",\n             "review/framework-upgrade-b78f03a/summary.json",\n             "review/framework-upgrade-b78f03a/index.md",\n             "review/framework-upgrade-b78f03a/browser-native/recording.json"):'),
    ('ROOT / ".stategraph/framework-upgrade-b78f03a"', 'ROOT / ".stategraph/framework-upgrade-3458366"'),
    ('ROOT.parent / "vibelens-policy-graph"', 'ROOT.parent / "vibelens-focus-fix"'),
    ('assert browser["status"] == audit["status"] == "passed"',
     'assert browser["status"] == audit["status"] == "passed"\nassert keyboard["status"] == "passed"\nassert read(OUT / "keyboard-details.json")["status"] == "passed"\nassert all(item["byte_identical"] for item in read(OUT / "unchanged-test-copies.json").values())'),
    ('"native_upgrade_applied_acceptance_failed_keyboard_path"', '"independent_project_acceptance_passed"'),
    ('"not_passed_pending_upstream_fix"', '"passed_for_this_project"'),
    ('"Focus-restoration re-selection/panel dismissal reproduced; HTTP/build/source identities match. See source-focus-finding.md. Unrepaired and not claimed passed."',
     '"Original byte-identical strict keyboard test passed without rerender; full source/highlight/version identity and focus return also passed in live/replay."'),
    ('"checked_at": datetime.now(timezone.utc).isoformat()',
     '"upstream_wider_verification": "Reported in progress at authorization; this report establishes independent project acceptance, not an unverified repository-wide result.",\n    "checked_at": datetime.now(timezone.utc).isoformat()'),
])
adapt("account_resources.py", [
    ('Framework upgrade b78f03a', 'Focus-fix candidate 3458366'),
    ('"pytest_seconds": 78.66', '"pytest_seconds": summary["pytest_seconds"]'),
    ('"current_short_capture_drain_seconds": 53.775', '"current_short_capture_drain_seconds": summary["drain_seconds"]'),
    ('result = {', 'summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))\nresult = {'),
    ('"business_iteration_reference": "../revocation-summary.json; historical evidence and resource facts remain separate."',
     '"previous_framework_round_reference": "../framework-upgrade-b78f03a/resources.json",\n    "business_iteration_reference": "../revocation-summary.json; all earlier iteration counters are excluded from this window."'),
])
text = (OUT / "finalize.py").read_text(encoding="utf-8")
text = text.replace('import json\n', 'import json\nimport re\n', 1)
text = text.replace('"pytest": 35,', '"pytest": 35, "pytest_seconds": float(re.search(r"35 passed in ([0-9.]+)s", tests["stdout"]).group(1)),', 1)
(OUT / "finalize.py").write_text(text, encoding="utf-8")
print("Prepared independent candidate audit/resource helpers; prior evidence is untouched.")
