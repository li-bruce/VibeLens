"""Reproject the preserved pre-fix draft; do not touch the live trial or its evidence."""

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "skills/vibelens").is_dir())
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer import concepts  # noqa: E402
from bo_observer.concepts.model import build  # noqa: E402
from bo_observer.graph.focus_graph import extract  # noqa: E402
from bo_observer.graph.relation_identity import relation_ids, relation_index  # noqa: E402
from bo_observer.web.design_preview import markdown  # noqa: E402


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def save(name, value):
    (HERE / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    before = read("before.json")
    for source in before["source_files"]:
        assert hashlib.sha256((HERE / source["file"]).read_bytes()).hexdigest() == source["sha256"]
    document = read("before-discovery.presented.json")
    old_preview = read("before-state-preview.json")
    data = build(document)
    report = concepts.assess(document)
    assert report["semantic_revision"] == before["semantic_revision"]
    graph = {**data["graph"], "revision": old_preview["focus"]["base"]["model_revision"]}
    selection = old_preview["focus"]["selection"]
    focus = extract(
        graph,
        selection["nodes"],
        depth=selection["depth"],
        max_nodes=selection["max_nodes"],
        max_edges=selection["max_edges"],
        relations=selection["relations"],
    )
    effect_edges = [edge for edge in graph["edges"] if edge["type"] == "has_effect"]
    assert len(before["canonical_effect_edges"]) == 4
    assert len(effect_edges) == 2
    represented = {ident for edge in effect_edges for ident in relation_ids(edge)}
    assert represented == {edge["id"] for edge in before["canonical_effect_edges"]}
    index = relation_index(graph["edges"])
    for ident in represented:
        assert ident in data["records"] and ident in data["index"]
        assert data["dependencies"][ident] == [index[ident]["from"], index[ident]["to"]]
    rendered = markdown(
        focus, document, old_preview["url"], old_preview["view"], old_preview["locale"]
    )
    save("after-state-preview.json", {**old_preview, "focus": focus, "markdown": rendered})
    (HERE / "after-state-preview.md").write_text(rendered, encoding="utf-8")
    result = {
        "stage": "after_fix",
        "semantic_revision": report["semantic_revision"],
        "semantic_revision_unchanged": True,
        "original_assertion_ids": sorted(represented),
        "canonical_effect_edges": effect_edges,
        "all_original_records_and_dependencies_retained": True,
        "source_files_sha256_unchanged": True,
        "runtime_exercised": False,
    }
    save("after.json", result)
    print(
        json.dumps(
            {"passed": True, "before_edges": 4, "after_edges": 2, "original_ids": len(represented)}
        )
    )


if __name__ == "__main__":
    main()
