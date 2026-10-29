"""Assemble the static product story from an actual, immutable trial export.

The material bundle owns source, event and screenshot evidence. The story file
selects a readable region and captions; it cannot replace captured values.
"""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.code_graph.query import query
from bo_observer.control.selection import build_plan


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inside(root, name):
    """Keep the explicit export bundle as the only source of material."""
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Material path escapes the export: " + name)
    return path


def source_matches(text, expected, raw=None):
    """A recorded UTF-8 text may normalize Windows newlines, but no code bytes."""
    normalized = text.replace("\r\n", "\n")
    if raw is not None:
        return (
            sha256(raw).hexdigest() == expected
            and raw.decode("utf-8-sig").replace("\r\n", "\n") == normalized
        )
    return expected in {
        sha256(value.encode("utf-8")).hexdigest()
        for value in (text, normalized, normalized.replace("\n", "\r\n"))
    }


def compact_slice(value):
    """Retain the native projection by identity, rather than repeating its nodes."""

    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        if isinstance(item, float) and item.is_integer():
            return int(item)
        return item

    encoded = json.dumps(
        normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return {
        **{key: child for key, child in value.items() if key not in {"nodes", "edges", "bindings"}},
        "encoding": "code-slice-refs/v1",
        "node_ids": [node["id"] for node in value["nodes"]],
        "boundary_ids": [node["id"] for node in value["nodes"] if node.get("code_boundary")],
        "edge_ids": [edge["id"] for edge in value["edges"]],
        "projection_sha256": sha256(encoded.encode("utf-8")).hexdigest(),
    }


def assemble(material, spec, target):
    """Keep original facts intact and precompute bounded native code queries."""
    material, target = material.resolve(), target.resolve()
    site = ROOT / "docs/site"
    if not target.is_relative_to(site):
        raise ValueError("The presentation output must stay inside docs/site")
    view = read(inside(material, spec.get("view", "api-view.json")))
    recording = read(inside(material, spec["recording"]))
    code = read(inside(material, spec.get("code", "code-graph-status.json")))
    business = read(inside(material, spec["business_result"]))
    if type(business.get("passed")) is not bool:
        raise ValueError("An actual Boolean business-case result is required")
    if recording["gaps"] or code["errors"] or code["omitted_nodes"]:
        raise ValueError("Incomplete recording or source export")
    context = recording["context"]
    if recording["build_id"] != context["manifest"]["build_id"]:
        raise ValueError("Recording and captured source build differ")
    if view["manifest"]["build_id"] != recording["build_id"]:
        raise ValueError("The exported view belongs to another build")
    if recording["final"]["binding_status"]["status"] != "current":
        raise ValueError("The recording ended with stale source bindings")
    if recording["final"]["health"]["errors"]:
        raise ValueError("The recording has observation errors")
    sources = recording["sources"]
    archive_path = inside(material, spec.get("source_archive", "source.zip"))
    source_checks = {}
    archive = zipfile.ZipFile(archive_path) if archive_path.is_file() else None
    for name, text in sources.items():
        expected = context["manifest"]["files"].get(name)
        raw = archive.read(name) if archive else None
        if not expected or not source_matches(text, expected, raw):
            raise ValueError("Recorded source differs from the build: " + name)
        source_checks[name] = {
            "manifest_sha256": expected,
            "recorded_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "archive_sha256": sha256(raw).hexdigest() if raw is not None else None,
        }
    if archive:
        archive.close()

    # A same-build restart can have no live events. Reconstruct the recorded
    # view only from retained context, final facts and its original frames.
    view.update(deepcopy(recording["final"]))
    view.update(
        model=deepcopy(context["model"]),
        manifest=deepcopy(context["manifest"]),
        events=deepcopy(recording["events"]),
        runtime_frames=deepcopy(recording["runtime_frames"]),
        stage="runtime",
        program_url=None,
        instances=[],
    )
    model, story = view["model"], deepcopy(spec["story"])
    path_plan = build_plan(
        view,
        {
            "action": "view",
            "label": "Business overview",
            "anchors": story.pop("business_anchors"),
            "depth": 0,
            "direction": "both",
            "nodes": ["business"],
            "edges": ["flow", "guard", "data"],
            "layout": "layered",
        },
    )
    story["business"] = path_plan["node_ids"]
    identities = {node["id"] for node in model["nodes"]}
    if not set(story["business"] + story["states"] + [story["inspection_node"]]) <= identities:
        raise ValueError("The selected story references missing graph nodes")
    events = {event["id"]: event for event in recording["events"]}
    inspection = events.get(story["inspection_event"])
    if not inspection or inspection["node"] != story["inspection_node"]:
        raise ValueError("The inspected node is not in the actual recording")
    for action in story["actions"]:
        if any(
            ident not in events
            or events[ident]["node"] != action["node"]
            or events[ident]["phase"] != action["phase"]
            for ident in action.get("event_ids", [])
        ):
            raise ValueError("An application action targets a different recorded event")
        if not any(
            event["node"] == action["node"] and event["phase"] == action["phase"]
            for event in recording["events"]
        ):
            raise ValueError("Application action is absent from the recording: " + action["id"])

    # The exported full native query includes authored binding edges. Restore
    # only its original code-to-code edges before requesting neighborhoods.
    raw = deepcopy(code)
    code_ids = {node["id"] for node in raw["nodes"]}
    raw["edges"] = [
        edge for edge in raw["edges"] if edge["from"] in code_ids and edge["to"] in code_ids
    ]
    raw["symbols"] = {
        node["code_symbol"]: node["id"]
        for node in raw["nodes"]
        if node.get("code_role") in {"function", "class"} and node.get("code_symbol")
    }
    focused = {}
    for node in model["nodes"]:
        if node.get("source"):
            focused[node["id"]] = query(raw, model, focus=node["id"], depth=1, limit=400)
    if story["source_focus"] not in focused or not focused[story["source_focus"]]["nodes"]:
        raise ValueError("The story has no actual source neighborhood")

    frames = []
    screenshot_map = read(inside(material, spec.get("screenshots", "event-screenshot-map.json")))
    image_dir = target.parent / (target.stem + "-frames")
    image_dir.mkdir(parents=True, exist_ok=True)
    app_stages = set(spec["application_stages"])
    if not app_stages:
        raise ValueError("Select actual application captures for the app window")
    for stage in screenshot_map["stages"]:
        if stage["stage"] not in app_stages:
            continue
        stage_events = stage.get("event_ids") or [stage.get("event_id")]
        if not stage_events or any(ident not in events for ident in stage_events):
            raise ValueError("Screenshot is outside the recording: " + stage["stage"])
        if stage.get("build_id", recording["build_id"]) != recording["build_id"]:
            raise ValueError("Screenshot belongs to another build")
        source = inside(material, stage.get("artifact_screenshot") or stage["screenshot"])
        data = source.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Expected an actual PNG screenshot")
        destination = image_dir / source.name
        shutil.copyfile(source, destination)
        caption = spec["frame_captions"].get(stage["stage"])
        if not caption:
            raise ValueError("Missing concise frame caption: " + stage["stage"])
        frames.append(
            {
                "event_id": stage_events[-1],
                "event_ids": stage_events,
                "images": {"en": destination.relative_to(site).as_posix()},
                "caption": caption,
                "status": stage["stage"],
                "sha256": sha256(data).hexdigest(),
            }
        )
    order = {event["id"]: index for index, event in enumerate(recording["events"])}
    frames.sort(key=lambda frame: order[frame["event_id"]])
    if len(frames) != len(app_stages):
        raise ValueError("A selected application stage has no recorded screenshot")
    result = {
        "schema": "vibelens-case/v1",
        "version": spec["version"],
        "provenance": {
            "kind": "real-local-execution",
            "build_id": recording["build_id"],
            "teaching_defect": spec["teaching_defect"],
            "source_stage": spec["source_stage"],
        },
        "view": view,
        "recording": recording,
        "code": code,
        "codeFocus": {key: compact_slice(value) for key, value in focused.items()},
        "catalog": read(inside(material, spec.get("catalog", "recording-catalog.json"))),
        "sources": sources,
        "source_checks": source_checks,
        "business": business,
        "story": story,
        "application_frames": frames,
        "application_overview": frames[0] if frames else None,
    }
    if spec.get("application_start"):
        source = inside(material, spec["application_start"])
        destination = image_dir / ("initial-" + source.name)
        shutil.copyfile(source, destination)
        result["application_start"] = {
            "images": {"en": destination.relative_to(site).as_posix()},
            "caption": spec["application_start_caption"],
            "sha256": sha256(source.read_bytes()).hexdigest(),
            "provenance": "Actual application capture before the recorded operation",
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "build": recording["build_id"],
        "events": len(events),
        "frames": len(frames),
        "code_nodes": len(code["nodes"]),
        "bytes": target.stat().st_size,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material", type=Path, required=True)
    parser.add_argument("--story", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(args.material, read(args.story), args.out)))
