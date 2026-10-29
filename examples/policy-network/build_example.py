"""A compact shared network covering file grants and direct-parent task ownership."""

import json
from pathlib import Path


def definition():
    inputs = {name: "string" for name in ("actor", "owner", "parent_owner", "recipient")}
    inputs.update(
        {name: "boolean" for name in ("logged_in", "grant_active", "role_allowed", "changes_owner")}
    )
    predicates = [
        {
            "id": "same_identity",
            "parameters": {"left": "string", "right": "string"},
            "source": {"path": "predicates.py", "symbol": "same_identity"},
            "source_refs": ["U1"],
        },
        {
            "id": "flag_enabled",
            "parameters": {"value": "boolean"},
            "source": {"path": "predicates.py", "symbol": "flag_enabled"},
            "source_refs": ["U1"],
        },
    ]
    nodes = [
        {
            "id": name,
            "op": "input",
            "name": name,
            "label": name.replace("_", " "),
            "source_refs": ["U1"],
        }
        for name in inputs
    ]

    def predicate(ident, function, **arguments):
        nodes.append(
            {
                "id": ident,
                "op": "predicate",
                "predicate": function,
                "arguments": arguments,
                "label": ident.replace("_", " "),
                "source_refs": ["U1"],
            }
        )

    def logical(ident, op, *children):
        nodes.append(
            {
                "id": ident,
                "op": op,
                "inputs": list(children),
                "label": ident.replace("_", " "),
                "source_refs": ["U1"],
            }
        )

    predicate("signed_in", "flag_enabled", value="logged_in")
    predicate("is_owner", "same_identity", left="actor", right="owner")
    predicate("is_parent_owner", "same_identity", left="actor", right="parent_owner")
    predicate("is_recipient", "same_identity", left="actor", right="recipient")
    predicate("active_grant", "flag_enabled", value="grant_active")
    predicate("role_grant", "flag_enabled", value="role_allowed")
    predicate("owner_change", "flag_enabled", value="changes_owner")
    logical("owned_session", "all", "signed_in", "is_owner")
    logical("received_active", "all", "is_recipient", "active_grant")
    logical("file_access", "any", "is_owner", "received_active")
    logical("download_allowed", "all", "signed_in", "file_access")
    logical("parent_session", "all", "signed_in", "is_parent_owner")
    logical("ordinary_edit", "not", "owner_change")
    logical("transfer_edit", "all", "owner_change", "is_parent_owner")
    logical("role_edit", "all", "ordinary_edit", "role_grant")
    logical("edit_basis", "any", "transfer_edit", "role_edit")
    logical("edit_allowed", "all", "signed_in", "edit_basis")
    operations = [
        {
            "id": name,
            "root": root,
            "business_nodes": [name],
            "cases": [name + "-case"],
            "source_refs": ["U1"],
        }
        for name, root in (
            ("share", "owned_session"),
            ("revoke", "owned_session"),
            ("download", "download_allowed"),
            ("transfer", "parent_session"),
            ("edit", "edit_allowed"),
        )
    ]
    return {
        "schema": "bo-policy/v1",
        "revision": "shared-example-1",
        "stage": "bound",
        "inputs": inputs,
        "predicates": predicates,
        "nodes": nodes,
        "operations": operations,
    }


if __name__ == "__main__":
    Path(__file__).with_name("policy.json").write_text(
        json.dumps(definition(), indent=2) + "\n", encoding="utf-8"
    )
