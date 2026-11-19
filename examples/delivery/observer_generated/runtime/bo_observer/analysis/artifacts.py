"""Revalidate saved analysis bytes before the normal iteration gate consumes them.

Hashes detect accidental drift, not malicious forgery by a filesystem owner.
Statuses are reconstructed from raw pinned-tool messages and regenerated model
text; editing a report to say pass cannot satisfy the normal verification gate.
"""

from pathlib import Path
import re
from copy import deepcopy

from ..behavior.evidence import applicability
from ..concepts.common import digest
from ..graph.behavior_model import contained
from .runner import adapter_identity, aggregate
from .tla.exporter import export_model
from .tla.toolchain import JAR_SHA256, VERSION, sha256
from .tla.results import parse_output
from .tla.process import command


def read_json(path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Analysis artifact exceeds read budget")
    from ..project_artifacts import parse

    return parse(path.read_bytes())


def verify_attempt(root, folder, snapshot):
    """Return a current executed receipt, or fail closed with a local diagnostic."""
    root = Path(root).resolve()
    folder = contained(root, folder)
    receipt = read_json(folder / "receipt.json")
    tool = receipt.get("tool_identity", {})
    if any(tool.get(key) != value for key, value in adapter_identity().items()):
        raise ValueError("Analysis adapter changed")
    fresh = applicability(receipt, snapshot, tool_identity=tool)
    if not fresh["current"]:
        raise ValueError("Stale analysis: " + fresh["reason"])
    for name, expected in receipt["artifacts"].items():
        path = contained(root, name)
        if not path.is_relative_to(folder) or not path.is_file() or sha256(path) != expected:
            raise ValueError("Analysis artifact missing, escaped or modified: " + name)
    required = {folder / "inputs.json", folder / "report.json", folder / "admission.json"}
    inputs = read_json(folder / "inputs.json")
    report = read_json(folder / "report.json")
    if report["tool_identity"] != tool:
        raise ValueError("Report tool differs from receipt")
    profile = inputs["profile"]
    results = []
    frozen = deepcopy(snapshot)
    frozen.update(
        behavior=inputs["contract"],
        behavior_discovery=inputs["discovery"],
        analysis_profiles=[profile],
    )
    if not applicability(receipt, frozen, tool_identity=tool)["current"]:
        raise ValueError("Frozen inputs differ from the receipt dependencies")
    if receipt["roots"] != ["profile/" + profile["id"]]:
        raise ValueError("Analysis profile identity differs")
    # Unavailable tools, rejected definitions and exhausted export budgets are
    # useful diagnostics. They cannot establish a logical result, and acceptance
    # remains blocked when the profile is required. Preserve their exact status.
    if receipt["outcome"] in {"incomplete", "unsupported", "error"}:
        if (
            aggregate(report["results"]) != receipt["outcome"]
            or report["status"] != receipt["outcome"]
        ):
            raise ValueError("Negative analysis outcome differs from report")
        if not {p.relative_to(root).as_posix() for p in required} <= set(receipt["artifacts"]):
            raise ValueError("Receipt omits required analysis artifacts")
        return receipt
    if tool.get("tlc_sha256") != JAR_SHA256 or tool.get("tlc_version") != VERSION:
        raise ValueError("Analysis has no tested tool identity")
    if not re.search(r'version "17[.\"]', tool.get("java_version", "")):
        raise ValueError("Analysis Java version is unsupported")
    if len(report["results"]) != len(profile["property_refs"]):
        raise ValueError("Analysis properties are incomplete")
    for index, ident in enumerate(profile["property_refs"]):
        directory = folder / ("property-" + str(index))
        generated = export_model(inputs["contract"], inputs["discovery"], profile, ident)
        generated["source_map"]["analysis_id"] = report["id"]
        for name, key in (("Model.tla", "tla"), ("Model.cfg", "cfg")):
            if (directory / name).read_text(encoding="utf-8") != generated[key]:
                raise ValueError("Analysis export differs from the frozen definition")
        source = read_json(directory / "source-map.json")
        if source != generated["source_map"]:
            raise ValueError("Analysis source map differs")
        execution = read_json(directory / "execution.json")
        arguments = execution["arguments"]
        if arguments != command(
            arguments[0], arguments[8], execution["working_directory"], profile["budget"]
        ):
            raise ValueError("Execution arguments differ from the fixed checker command")
        raw = parse_output(
            (directory / "stdout.log").read_text(encoding="utf-8"),
            execution["exit_code"],
            source,
            stop_reason=execution["stop_reason"],
        )
        raw["property"] = ident
        if raw != read_json(directory / "result.json") or raw != report["results"][index]:
            raise ValueError("Saved outcome differs from actual tool output")
        required.update(
            directory / name
            for name in (
                "Model.tla",
                "Model.cfg",
                "source-map.json",
                "execution.json",
                "stdout.log",
                "stderr.log",
                "result.json",
            )
        )
        results.append(raw)
    if not {p.relative_to(root).as_posix() for p in required} <= set(receipt["artifacts"]):
        raise ValueError("Receipt omits required execution artifacts")
    if aggregate(results) != receipt["outcome"] or report["status"] != receipt["outcome"]:
        raise ValueError("Receipt outcome differs from execution")
    return receipt


def collect(root, snapshot):
    """Read only the analysis ledger; never scan source/dependencies or start a tool."""
    receipts = []
    tools = {}
    diagnostics = []
    if not snapshot.get("analysis_profiles"):
        return receipts, tools, diagnostics
    directory = contained(root, ".stategraph/analysis")
    if not directory.is_dir():
        return receipts, tools, diagnostics
    for folder in sorted(directory.iterdir()):
        if not re.fullmatch("[0-9a-f]{32}", folder.name) or not folder.is_dir():
            continue
        try:
            receipt = verify_attempt(root, folder.relative_to(root), snapshot)
            receipts.append(receipt)
            key = receipt["roots"][0].removeprefix("profile/")
            identities = tools.setdefault(key, [])
            if receipt["tool_identity"] not in identities:
                identities.append(receipt["tool_identity"])
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            diagnostics.append({"attempt": folder.name, "reason": str(error)})
    # A cancelled/partial exploration makes no logical claim against a completed
    # proof of the same dependencies and adapter, including a previously missing
    # tool. Retain it on disk and explain the
    # replacement. Contradicting completed pass/fail evidence still reaches the
    # original strict coverage gate together, where it blocks acceptance.
    completed = {
        (tuple(r["roots"]), r["tool_identity"]["adapter_sha256"], digest(r["dependencies"]))
        for r in receipts
        if r["outcome"] == "pass"
    }
    retained = []
    for receipt in receipts:
        key = (
            tuple(receipt["roots"]),
            receipt["tool_identity"]["adapter_sha256"],
            digest(receipt["dependencies"]),
        )
        if receipt["outcome"] == "incomplete" and key in completed:
            diagnostics.append(
                {
                    "receipt": receipt["fingerprint"],
                    "reason": "Superseded incomplete exploration; completed evidence has the same dependencies and adapter",
                }
            )
        else:
            retained.append(receipt)
    return (
        retained,
        {key: values[0] if len(values) == 1 else values for key, values in tools.items()},
        diagnostics,
    )
