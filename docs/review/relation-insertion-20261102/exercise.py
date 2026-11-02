"""Save actual insertion, restoration and ID-conflict evidence for review."""

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.graph.relations import RelationIndex
from bo_observer.workflow.sync_io import write


def main():
    rules = {
        "schema": "bo-relation-rules/v1",
        "definitions": [
            {
                "id": "implements",
                "mode": "direct",
                "match": {"type": "maps", "origin": "implementation"},
            },
            {"id": "reads", "mode": "direct", "match": {"type": "data", "origin": "source"}},
            {
                "id": "uses-data",
                "mode": "summary",
                "match": {
                    "type": "maps",
                    "origin": "relation-summary",
                    "semantic_relation": "uses-data",
                },
            },
        ],
        "compositions": [
            {"id": "implementation-read", "result": "uses-data", "path": ["implements", "reads"]}
        ],
    }
    context = {
        "scope": "sharing",
        "revision": "v1",
        "basis": "confirmed:review-fixture",
        "bindings": {},
        "conditions": {},
    }

    def registration(ident, start, end, relation, kind, origin):
        edge = {
            "id": ident,
            "from": start,
            "to": end,
            "type": kind,
            "origin": origin,
            "evidence": "review-fixture",
        }
        if relation == "uses-data":
            edge["semantic_relation"] = relation
        return {"edge": edge, "relation": relation, "context": deepcopy(context)}

    index = RelationIndex(["business.share", "function.read", "table.files"], rules)
    summary = registration(
        "share-files", "business.share", "table.files", "uses-data", "maps", "relation-summary"
    )
    index.insert(summary)
    snapshots = {"01_summary_without_path": index.export()}
    implementation = registration(
        "share-read", "business.share", "function.read", "implements", "maps", "implementation"
    )
    implementation["definition_key"] = "share-implementation"
    read = registration("read-files", "function.read", "table.files", "reads", "data", "source")
    index.apply([{"op": "insert", "entry": value} for value in [implementation, read]])
    snapshots["02_typed_path_arrives"] = index.export()
    assert index.decision("share-files")["leaf_path"] == ["share-read", "read-files"]
    alias = deepcopy(implementation)
    alias["edge"].update(id="share-read-alias", label="Read the file")
    index.insert(alias)
    snapshots["03_duplicate_definition"] = index.export()
    assert index.decision("share-read-alias")["duplicate_of"] == "share-read"
    observed = deepcopy(summary)
    observed["edge"]["event_id"] = "actual-independent-fact"
    index.update("share-files", observed)
    snapshots["04_independent_witness"] = index.export()
    assert index.decision("share-files")["reason"] == "independent_evidence"
    index.update("share-files", summary)
    index.remove("read-files")
    snapshots["05_witness_removed"] = index.export()
    assert index.decision("share-files")["status"] == "retained"
    before = index.export()
    conflict = deepcopy(summary)
    conflict["edge"]["to"] = "function.read"
    try:
        index.insert(conflict)
    except ValueError as exc:
        snapshots["06_conflict"] = {"error": str(exc), "unchanged": index.export() == before}
    else:
        raise AssertionError("Conflicting edge ID was admitted")
    assert RelationIndex.restore(index.export()).export() == index.export()
    write(OUT / "insertion-exercise.json", {"valid": True, "snapshots": snapshots})
    print(
        json.dumps({"valid": True, "steps": len(snapshots), "evidence": "insertion-exercise.json"})
    )


if __name__ == "__main__":
    main()
