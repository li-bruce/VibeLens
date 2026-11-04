"""Bind confirmed meaning to the application's existing source and independent cases."""

# These portable entrypoints load the explicitly selected Skill before importing it.
# ruff: noqa: E402

from copy import deepcopy
import json
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parent
SKILL = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(SKILL / "scripts"))
from bo_observer import concepts
from bo_observer.policy.projection import project as project_policy
from bo_observer.graph.code_structure import scan, enrich
from bo_observer.protocol import validate_project
from bo_observer.data.catalog import collect
from bo_observer.data.projection import project_model
from bo_observer.data.contract import source_identity
from bo_observer.graph.behavior_model import digest


def write(name, value):
    """Persist a readable project declaration without executable code in JSON."""
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


document = json.loads((ROOT / "discovery.json").read_text(encoding="utf-8"))
from service import FileService

FileService(ROOT / "var")  # Application schema creation precedes read-only collection.
os.environ["BO_TRIAL_DATABASE_URL"] = "sqlite:///var/files.sqlite3"
state = document["state_models"][0]


def source(symbol):
    """Create one stable reference to a native service declaration."""
    return {"path": "service.py", "symbol": symbol}


machine = {
    "engine": "bo.fsm",
    "version": "1",
    "state_type": "enum",
    "states": state["states"],
    "values": state["states"],
    "initial": state["initial"],
    "events": state["events"],
    "context": {},
    "guards": {"may_manage": {"source": source("same_identity")}},
    "transitions": [
        {
            key: value
            for key, value in transition.items()
            if key in {"source", "dest", "trigger", "conditions", "unless"}
        }
        for transition in state["transitions"]
    ],
}
symbols = {
    "upload": "upload",
    "share": "share",
    "read": "download",
    "revoke": "revoke",
    "list": "received",
}
labels = {
    "upload": "Upload file",
    "share": "Share file",
    "read": "Download file",
    "revoke": "Revoke access",
    "list": "See received files",
}
inputs = {"actor": "string", "file_id": "string", "recipient": "string"}
outputs = {
    "file_id": "string",
    "recipient": "string",
    "state": "string",
    "revision": "number",
    "status": "number",
    "error": "string",
    "count": "number",
}
nodes = [
    {
        "id": name,
        "kind": "action",
        "layer": "business",
        "label": labels[name],
        "summary": labels[name],
        "source": source("FileService." + symbol),
        "capture": {"in": deepcopy(inputs), "out": deepcopy(outputs)},
        "requirements": ["R1"],
    }
    for name, symbol in symbols.items()
]
nodes += [
    {
        "id": name,
        "kind": "state",
        "layer": "state",
        "value": name,
        "label": name,
        "summary": "Current recipient access",
    }
    for name in state["states"]
]
nodes += [
    {
        "id": "facts",
        "kind": "function",
        "label": "Read current grant",
        "summary": "Read the current owner and recipient before authorization",
        "source": source("FileService.facts"),
        "capture": {
            "in": {"actor": "string", "file_id": "string"},
            "out": {
                "actor": "string",
                "owner": "string",
                "recipient": "string",
                "active": "boolean",
                "timing": "string",
                "scope": "string",
                "revision": "number",
            },
        },
    }
]
for name in ["home", "upload", "share", "revoke", "received", "download"]:
    nodes.append(
        {
            "id": "http." + name,
            "kind": "function",
            "label": "HTTP " + name,
            "summary": "Actual Flask request and response",
            "source": {"path": "app.py", "symbol": "create_app." + name},
            "capture": {"in": {"method": "string", "route": "string"}, "out": {"status": "number"}},
        }
    )
policy = deepcopy(document["policy"])
policy["stage"] = "bound"
policy["predicates"][0]["source"] = source("same_identity")
for operation in policy["operations"]:
    operation["business_nodes"] = (
        ["share", "revoke"] if operation["id"] == "manage" else ["read", "list"]
    )
    operation["cases"] = (
        ["owner-only"]
        if operation["id"] == "manage"
        else ["allowed-download", "revoke-denies-old-link"]
    )
model = {
    "schema_version": 3,
    "revision": "2",
    "project_id": document["project_id"],
    "intent": "intent.json",
    "source_files": ["app.py", "service.py"],
    "nodes": nodes,
    "edges": [
        {
            "id": edge["id"],
            "from": edge["from"],
            "to": edge["to"],
            "type": "flow",
            "label": edge["label"],
            "evidence": "Confirmed synthetic trial dialogue",
        }
        for edge in document["networks"][0]["edges"]
    ],
    "overview": [{"node": name} for name in symbols],
    "scope": {"unknowns": []},
    "machine": machine,
    "policy": policy,
}
model = project_policy(model)
database = {
    "protocol": "bo-databases/v1",
    "stores": [
        {
            "id": "files",
            "label": "File storage",
            "engine": "sqlalchemy",
            "url_env": "BO_TRIAL_DATABASE_URL",
            "selection": {
                "source": "user",
                "answer": "信息用SQLite吧。",
                "locator": "Synthetic trial U2",
            },
            "model_layer": "Application-owned SQLite DDL",
            "source_files": ["service.py"],
        }
    ],
    "operations": [
        {
            "id": "db." + name,
            "label": labels[name],
            "parent": name,
            "source": source("FileService." + symbol),
            "store": "files",
            "action": "read" if name in {"read", "list"} else "write",
            "targets": ["table:files"] if name == "upload" else ["table:files", "table:grants"],
            **(
                {"target_actions": {"table:files": "read", "table:grants": "read_write"}}
                if name in {"share", "revoke"}
                else {}
            ),
            "parameters": {},
            "before": {},
            "after": {},
            "required_cases": ["allowed-download"],
        }
        for name, symbol in symbols.items()
        if name != "read"
    ],
}
database["operations"].append(
    {
        "id": "db.facts",
        "label": "Read current grant",
        "parent": "facts",
        "source": source("FileService.facts"),
        "store": "files",
        "action": "read",
        "targets": ["table:files", "table:grants"],
        "parameters": {},
        "before": {},
        "after": {},
        "required_cases": ["allowed-download"],
    }
)
write("bo_stategraph/databases.json", database)
catalog = collect(database["stores"][0], root=ROOT)
bundle = {
    "source_id": source_identity(ROOT, database),
    "catalog_id": digest(catalog),
    "catalogs": [catalog],
    "declarations": [],
}
write("bo_stategraph/database-catalog.json", bundle)
model = project_model(model, database, bundle)
for name in ["actor", "owner", "recipient", "active"]:
    model["edges"].append(
        {
            "id": "fact:" + name,
            "from": "facts",
            "to": "policy:" + name,
            "type": "data",
            "label": name,
            "evidence": "Current request's native facts",
        }
    )
for name, business in [
    ("upload", "upload"),
    ("share", "share"),
    ("revoke", "revoke"),
    ("received", "list"),
    ("download", "read"),
]:
    model["edges"].append(
        {
            "id": "http-call:" + name,
            "from": "http." + name,
            "to": business,
            "type": "flow",
            "code_relation": "calls",
            "label": "Calls",
            "evidence": "Actual Flask handler source",
        }
    )
fields = {
    "actor-id": "actor",
    "owner-id": "owner",
    "recipient-id": "recipient",
    "active-grant": "active",
}
crosslinks = {
    **{
        name
        + "-requests-event": {
            "relation": "action_requests_event",
            "from": [name],
            "to": [name],
            "native_event": name,
            "edges": [],
        }
        for name in ["share", "revoke"]
    },
    "share-guard": ["policy:operation:manage:share"],
    "revoke-guard": ["policy:operation:manage:revoke"],
    "replace-guard": ["policy:operation:manage:share"],
    **{"read-" + fact: ["fact:" + field] for fact, field in fields.items()},
}
model["concepts"] = {
    "schema": "bo-concept-bindings/v1",
    "semantic_revision": concepts.assess(document)["semantic_revision"],
    "primary_state_model": "grant",
    "objects": {"grant": state["subject"]},
    "business": {name: [name] for name in symbols},
    "facts": {
        fact: [
            {
                "node": "facts",
                "direction": "out",
                "field": field,
                "basis_checks": [{"case": "revoke-denies-old-link", "path": ["reads", fact]}],
            }
        ]
        for fact, field in fields.items()
    },
    "expectations": {item["id"]: [item["id"]] for item in document["expectations"]},
    "crosslinks": crosslinks,
    "events": {
        "event:grant:" + name: {"node": name, "event": name} for name in ["share", "revoke"]
    },
}
acceptance = {
    "checks": [
        {"case": item["id"], **assertion}
        for item in document["expectations"]
        for assertion in item["then"]
    ]
}
for fact in document["facts"]:
    acceptance["checks"].append(
        {
            "case": "revoke-denies-old-link",
            "path": ["reads", fact["id"]],
            "equals": {
                "node": "facts",
                "direction": "out",
                "field": fields[fact["id"]],
                "read_basis": fact["read_basis"],
            },
        }
    )
for index, check in enumerate(acceptance["checks"]):
    check.update(id="check-" + str(index + 1), requirement="R1")
write("acceptance.json", acceptance)
# Each mapped boundary declares only fields that this adapter actually captures.
selected_inputs = {
    "upload": {"actor": "string", "name": "string", "content_size": "number"},
    "share": inputs,
    "revoke": {"actor": "string", "file_id": "string", "recipient": "string"},
    "read": {"actor": "string", "file_id": "string"},
    "list": {"actor": "string"},
}
selected_outputs = {
    "upload": {"file_id": "string", "owner": "string", "name": "string"},
    "share": {"file_id": "string", "recipient": "string", "state": "string", "revision": "number"},
    "revoke": {"file_id": "string", "recipient": "string", "state": "string", "revision": "number"},
    "read": {"count": "number"},
    "list": {"count": "number"},
}
for node in model["nodes"]:
    if node["id"] in selected_inputs:
        node["capture"] = {"in": selected_inputs[node["id"]], "out": selected_outputs[node["id"]]}
    if node["id"] in {"http.share", "http.revoke", "http.download"}:
        node["capture"]["in"]["file_id"] = "string"
model = enrich(model, scan(ROOT, model["source_files"]), depth=1)
routes = {
    "home": ("GET", "/"),
    "upload": ("POST", "/api/files"),
    "share": ("POST", "/api/files/<file_id>/share"),
    "revoke": ("POST", "/api/files/<file_id>/revoke"),
    "received": ("GET", "/api/received"),
    "download": ("GET", "/api/files/<file_id>/download"),
}
telemetry = {
    "protocol": "bo-telemetry/v1",
    "backend": "opentelemetry",
    "registrations": [
        {
            "node": "http." + name,
            "source": {"path": "app.py", "symbol": "create_app." + name},
            "match": {"name": method + " " + path},
            "capture": {
                "in": {"method": "http.request.method", "route": "http.route"},
                "out": {"status": "http.response.status_code"},
            },
        }
        for name, (method, path) in routes.items()
    ],
}
write("bo_stategraph/telemetry.json", telemetry)
model["source_files"] = sorted(
    set(
        model["source_files"]
        + [
            "bo_integration.py",
            "bo_projection.py",
            "bo_stategraph/telemetry.json",
            "bo_stategraph/databases.json",
        ]
    )
)
# Register every observed boundary, including policy/data projections, with its
# independent real-HTTP acceptance case. Helpers remain source-mapped support.
index = scan(ROOT, ["app.py", "service.py", "bo_integration.py", "bo_projection.py"])
model = enrich(model, index, depth=1)
feature_sources = ["service.py::FileService." + value for value in symbols.values()]
feature_sources += ["app.py::create_app." + name for name in routes]
parameters = []
by_symbol = {"service.py::FileService." + value: key for key, value in symbols.items()}
by_symbol.update({"app.py::create_app." + name: "http." + name for name in routes})
for sid in feature_sources:
    for parameter in index["symbols"][sid]["parameters"]:
        name = parameter["name"]
        if name == "self":
            continue
        field = "content_size" if name == "content" else name
        parameters.append(
            {
                "source": sid,
                "name": name,
                "node": by_symbol[sid],
                "field": field,
                **(
                    {"policy": "derived", "reason": "Observe byte count, not uploaded file content"}
                    if name == "content"
                    else {}
                ),
            }
        )
support, excluded = {}, {}
for sid, symbol in index["symbols"].items():
    if symbol["kind"] != "function" or sid in feature_sources:
        continue
    if symbol["path"].startswith("bo_"):
        excluded[sid] = {
            "category": "observer",
            "reason": "Project-local graph adapter and read-only state projection",
        }
    elif symbol["symbol"].split(".")[-1] in {"__init__", "__enter__", "__exit__"}:
        excluded[sid] = {
            "category": "construction",
            "reason": "Object creation and resource lifetime",
        }
    else:
        found = next(
            (
                n
                for n in model["nodes"]
                if n.get("source") == {"path": symbol["path"], "symbol": symbol["symbol"]}
            ),
            None,
        )
        if found is None:
            found = {
                "id": "support:" + sid,
                "kind": "function",
                "label": symbol["symbol"],
                "summary": "Native application helper",
                "source": {"path": symbol["path"], "symbol": symbol["symbol"]},
            }
            model["nodes"].append(found)
        support[sid] = {
            "node": found["id"],
            "reason": "Native request, persistence or permission helper",
        }
# Source scanning must not project observation helpers into application nodes.

model["implementation"] = {
    "schema": "bo-implementation/v1",
    "features": [
        {
            "id": "files",
            "label": "Share local files",
            "business_node": "upload",
            "requirements": ["R1"],
            "nodes": [n["id"] for n in model["nodes"] if any(n.get("capture", {}).values())],
            "sources": feature_sources,
            "parameters": parameters,
            "cases": [
                {"case": "roundtrip", "node": n["id"], "phase": phase}
                for n in model["nodes"]
                if any(n.get("capture", {}).values())
                for phase in (
                    ["decision"] if n.get("origin") == "policy-definition" else ["enter", "return"]
                )
            ],
        }
    ],
    "support": support,
    "excluded": excluded,
}
model = enrich(model, index, depth=1)
envelope = {
    "protocol": "bo-project/v1",
    "project_id": document["project_id"],
    "selection": {
        "mode": "observe",
        "source": "user",
        "answer": "保留我自己的代码组织，只用图观察。",
        "locator": "Synthetic trial U2; not a human acceptance",
    },
    "model": model,
}
write("review/project-candidate.json", envelope)
validate_project(envelope)
write("bo_stategraph/project.json", envelope)
result = concepts.assess(document, model=model, acceptance=acceptance)
write("review/concept-binding.json", result)
from bo_observer.data.sync import synchronize

sync_report = synchronize(ROOT, model_path="bo_stategraph/project.json", update=True)
if not sync_report["valid"]:
    raise ValueError(sync_report["errors"])
print(
    json.dumps(
        {"valid": result["valid"], "ready": result["ready"], "errors": result["errors"]},
        ensure_ascii=False,
    )
)
if not result["ready"]:
    raise SystemExit(1)
