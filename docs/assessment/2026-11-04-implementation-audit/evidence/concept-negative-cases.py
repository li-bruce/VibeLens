"""Read-only audit probes for conceptual-to-native association checks.

The shipped unit fixture is copied into memory. These probes assess declaration
gates only: they do not claim a complete project's acceptance workflow passes.
Run with the repository virtual environment and ``-B`` from the repository root.
"""

import importlib.util
import json
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / 'skills/vibelens').is_dir())
spec = importlib.util.spec_from_file_location(
    "concept_audit_fixture", ROOT / "tests/test_concept_models.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

from bo_observer.concepts import assess  # noqa: E402
from bo_observer.policy.projection import project, projection_errors  # noqa: E402
from bo_observer.policy.evidence import binding_errors  # noqa: E402
from bo_contracts import validate_runtime_definition  # noqa: E402


def collect(label, document, model, acceptance):
    """Check each independent declaration gate using an explicit synthetic fixture."""
    report = assess(document, model=model, acceptance=acceptance)
    try:
        validate_runtime_definition(model["machine"])
        state_errors = []
    except (ValueError, KeyError, TypeError) as error:
        state_errors = [str(error)]
    # Signature inventory below is synthetic and labelled as such. A whole
    # project's source and runtime checks are intentionally outside this probe.
    synthetic_structure = {
        "symbols": {
            "sharing.py::same_identity": {
                "path": "sharing.py",
                "symbol": "same_identity",
                "parameters": [
                    {"name": "left", "annotation": "str"},
                    {"name": "right", "annotation": "str"},
                ],
            }
        }
    }
    return {
        "case": label,
        "concept_valid": report["valid"],
        "concept_ready": report["ready"],
        "concept_errors": report["errors"],
        "policy_projection_errors": projection_errors(model),
        "native_state_definition_errors": state_errors,
        "synthetic_signature_binding_errors": binding_errors(
            model["policy"], synthetic_structure
        ),
        "full_project_acceptance": "not_run",
    }


results = []
document, model, acceptance = fixture.bound_fixture()
results.append(collect("baseline", document, model, acceptance))

document, model, acceptance = fixture.bound_fixture()
for operation in model["policy"]["operations"]:
    if operation["id"] == "read":
        operation["business_nodes"] = ["native:share"]
model = project(model)
results.append(
    collect(
        "confirmed read rule moved from native read to native share",
        document,
        model,
        acceptance,
    )
)

document, model, acceptance = fixture.bound_fixture()
document["confirmations"] = []
document["state_models"][0]["effects"]["store_grant"] = {
    "meaning": "Persist a grant row",
    "completion": "The grant transaction commits",
    "source_refs": ["U1"],
}
document["state_models"][0]["transitions"][0]["effects"] = ["store_grant"]
fixture.approve(document)
model["concepts"]["semantic_revision"] = assess(document)["semantic_revision"]
model["concepts"]["effects"] = {"effect:grant:store_grant": ["native:read"]}
results.append(
    collect(
        "confirmed share transition effect mapped to unrelated native read",
        document,
        model,
        acceptance,
    )
)

# A control mutation must still be rejected: the association omissions above do
# not mean semantic operator checking or immutable confirmations are absent.
document, model, acceptance = fixture.bound_fixture()
next(node for node in model["policy"]["nodes"] if node["id"] == "may_read")["op"] = "any"
model = project(model)
results.append(collect("control: native AND changed to OR", document, model, acceptance))

print(json.dumps({"scope": "in_memory_contract_audit", "results": results}, indent=2))
assert results[0]["concept_ready"]
assert results[1]["concept_ready"]
assert results[2]["concept_ready"]
assert not results[3]["concept_ready"]
