"""Audit the semantic-to-display projection without changing any project inputs."""

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / 'skills/vibelens').is_dir())
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.concepts.model import build

document = json.loads(
    (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_text(encoding="utf-8")
)
negated = deepcopy(document)
transition = negated["state_models"][0]["transitions"][0]
transition["unless"] = transition.pop("conditions")
positive = build(document)
negative = build(negated)

def guards(projected):
    return [edge for edge in projected["graph"]["edges"] if edge["type"] == "guarded_by"]

result = {
    "audit_commit": "ce0a1fa6",
    "mutation": "First transition: conditions [may_manage] becomes unless [may_manage]",
    "positive_guard_edges": guards(positive),
    "negative_guard_edges": guards(negative),
    "positive_guard_records": {
        edge["id"]: positive["records"][edge["id"]] for edge in guards(positive)
    },
    "negative_guard_records": {
        edge["id"]: negative["records"][edge["id"]] for edge in guards(negative)
    },
    "positive_transition_detail": next(
        node["concept_definition"] for node in positive["graph"]["nodes"]
        if node["id"] == "transition:grant:grant-share"
    ),
    "negative_transition_detail": next(
        node["concept_definition"] for node in negative["graph"]["nodes"]
        if node["id"] == "transition:grant:grant-share"
    ),
    "display_guard_edges_identical": guards(positive) == guards(negative),
    "semantic_records_differ": positive["records"] != negative["records"],
}
target = Path(__file__).with_suffix(".json")
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
