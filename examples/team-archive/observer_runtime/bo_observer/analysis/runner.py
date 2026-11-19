"""Run an admitted design profile and retain immutable, replay-verifiable evidence.

Tools and analysis are optional. All model execution is in a separate JVM;
native state ownership, business tests and observation are unchanged.
"""

import json
from pathlib import Path
import time
import uuid

from ..concepts.common import digest
from ..graph.behavior_model import contained
from ..behavior.evidence import issue
from .capabilities import admit
from .tla.exporter import export_model, EXPORTER
from .tla.values import ExportLimit
from .tla.toolchain import resolve, sha256
from .tla.process import execute
from .tla.results import parse_output
from .trace import project_trace


def write_json(path, value):
    """Write an analysis artifact; callers own a fresh, project-contained attempt folder."""
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def adapter_identity():
    """Invalidate receipts after any change to export, protocol or concept semantics."""
    package = Path(__file__).resolve().parents[1]
    files = {}
    for name in ("analysis", "behavior", "concepts", "schemas"):
        for path in sorted((package / name).rglob("*")):
            if path.suffix in {".py", ".json"}:
                files[path.relative_to(package).as_posix()] = sha256(path)
    for name in ("protocol.py", "value_types.py"):
        files[name] = sha256(package / name)
    return {"exporter": EXPORTER, "adapter_sha256": digest(files)}


def aggregate(results):
    """All requested properties must finish; a counterexample is retained alongside errors."""
    return next(
        (
            status
            for status in ("error", "fail", "incomplete", "unsupported")
            if any(r["status"] == status for r in results)
        ),
        "pass" if results else "incomplete",
    )


def run_profile(root, snapshot, profile_id, *, java=None, jar=None, cancel=None):
    """Resolve a configured profile ID; no arbitrary command or output path is accepted."""
    root = Path(root).resolve()
    profile = next(
        (p for p in snapshot.get("analysis_profiles", []) if p["id"] == profile_id), None
    )
    if not profile:
        raise ValueError("Unknown configured analysis profile: " + profile_id)
    contract, discovery = snapshot["behavior"], snapshot["behavior_discovery"]
    admission = admit(contract, discovery, profile)
    attempt = uuid.uuid4().hex
    relative = ".stategraph/analysis/" + attempt
    folder = contained(root, relative)
    folder.mkdir(parents=True, exist_ok=False)
    inputs = {"contract": contract, "discovery": discovery, "profile": profile}
    write_json(folder / "inputs.json", inputs)
    write_json(folder / "admission.json", admission)
    identity = adapter_identity()
    results = []
    if not admission["eligible"]:
        results = [
            {
                "status": (
                    "unsupported"
                    if admission["status"] in {"unsupported", "unresolved"}
                    else "error"
                ),
                "reason": "admission",
                "diagnostics": admission["diagnostics"],
            }
        ]
    else:
        try:
            java, jar, tool = resolve(java, jar)
            identity.update(tool)
        except (OSError, ValueError) as error:
            results = [{"status": "incomplete", "reason": "tool_unavailable", "detail": str(error)}]
    deadline = time.monotonic() + profile["budget"]["wall_seconds"]
    if not results:
        for index, property_id in enumerate(profile["property_refs"]):
            directory = folder / ("property-" + str(index))
            directory.mkdir()
            try:
                model = export_model(contract, discovery, profile, property_id)
                model["source_map"]["analysis_id"] = attempt
                (directory / "Model.tla").write_text(model["tla"], encoding="utf-8")
                (directory / "Model.cfg").write_text(model["cfg"], encoding="utf-8")
                write_json(directory / "source-map.json", model["source_map"])
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    results.append(
                        {
                            "status": "incomplete",
                            "reason": "profile_timeout",
                            "property": property_id,
                        }
                    )
                    break
                execution = execute(
                    java,
                    jar,
                    directory,
                    {**profile["budget"], "wall_seconds": remaining},
                    cancel=cancel,
                )
                write_json(directory / "execution.json", execution)
                result = parse_output(
                    (directory / "stdout.log").read_text(encoding="utf-8"),
                    execution["exit_code"],
                    model["source_map"],
                    stop_reason=execution["stop_reason"],
                )
                if result["trace"]:
                    projected = project_trace(result["trace"], contract, discovery)
                    write_json(directory / "logical-trace.json", projected)
                result["property"] = property_id
            except ExportLimit as error:
                result = {
                    "status": "incomplete",
                    "reason": "export_budget",
                    "detail": str(error),
                    "property": property_id,
                }
            except (OSError, ValueError, KeyError) as error:
                result = {
                    "status": "error",
                    "reason": "adapter_error",
                    "detail": str(error),
                    "property": property_id,
                }
            results.append(result)
            write_json(directory / "result.json", result)
    report = {
        "schema": "bo-analysis-run/v1",
        "id": attempt,
        "profile": profile_id,
        "subject": "design_model",
        "status": aggregate(results),
        "results": results,
        "tool_identity": identity,
        "claim": "Selected finite design only; native correspondence is checked separately",
    }
    write_json(folder / "report.json", report)
    artifacts = {
        path.relative_to(root).as_posix(): sha256(path)
        for path in folder.rglob("*")
        if path.is_file()
        and "states" not in path.relative_to(folder).parts
        and "tmp" not in path.relative_to(folder).parts
    }
    receipt = issue(
        snapshot,
        "design_model",
        ["profile/" + profile_id],
        outcome=report["status"],
        artifacts=artifacts,
        tool_identity=identity,
    )
    write_json(folder / "receipt.json", receipt)
    return {**report, "directory": relative, "receipt": receipt}
