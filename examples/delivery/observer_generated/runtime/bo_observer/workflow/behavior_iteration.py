"""Attach behavior evidence to the existing iteration receipt and recall.

This adapter owns no execution engine, acceptance baseline or dialogue store.
The original coordinator still runs, reviews and accepts every required check.
"""

from ..concepts.common import digest
from ..behavior.coverage import reports
from ..behavior.evidence import issue, applicability


def previous_evidence(receipt, current):
    """Explain freshness of saved native results without rerunning or accepting them."""
    return {
        name: applicability(value, current)
        for name, value in receipt.get("behavior_receipts", {}).items()
    }


def finalize(current, receipt, *, formal_results=(), analysis_tools=None, root=None):
    """Add mandatory gaps without converting any original failure into success."""
    if current.get("behavior") is None:
        return receipt
    if root is not None:
        from ..analysis.artifacts import collect

        formal_results, analysis_tools, diagnostics = collect(root, current)
        receipt["analysis_artifacts"] = diagnostics
    coverage = reports(
        current, receipt["reports"], formal_results=formal_results, analysis_tools=analysis_tools
    )
    receipt["behavior_coverage"] = coverage
    receipt["errors"].extend({"behavior_evidence_missing": name} for name in coverage["blocking"])
    receipt["valid"] = bool(receipt["valid"] and not coverage["blocking"])
    contract = current["behavior"]
    roots = [
        prefix + "/" + item["id"]
        for section, prefix in (
            ("variables", "variable"),
            ("actions", "action"),
            ("interactions", "interaction"),
        )
        for item in contract.get(section, [])
    ]
    receipts = {}
    if roots:
        for subject, category in (("native_mapping", "mapping"), ("native_runtime", "capture")):
            report = coverage["categories"][category]
            if report["status"] == "pending":
                continue
            artifacts = {"coverage": digest(report)}
            if subject == "native_runtime":
                if not receipt.get("observations_hash"):
                    continue
                artifacts["observations"] = receipt["observations_hash"]
            else:
                artifacts["source_index"] = digest(current["structure"])
            receipts[subject] = issue(
                current,
                subject,
                roots,
                outcome="pass" if report["status"] == "passed" else "fail",
                artifacts=artifacts,
            )
    receipt["behavior_receipts"] = receipts
    return receipt
