"""Versioned definition capabilities, independent of executors and optional tools.

This parser/type-checking contract is broader than the optional analysis adapter.
Each exporter declares its own supported subset and performs separate admission.
"""

from copy import deepcopy

DEFINITION_CAPABILITIES = {
    "id": "behavior-definition/3",
    "wire_schema": "bo-behavior/v1",
    "domains": [
        "boolean",
        "enum",
        "integer",
        "number",
        "string",
        "set",
        "sequence",
        "map",
        "identity",
    ],
    "expressions": [
        "literal",
        "var",
        "param",
        "all",
        "any",
        "not",
        "implies",
        "eq",
        "ne",
        "lt",
        "le",
        "add",
        "sub",
        "member",
        "select",
        "forall",
        "exists",
        "policy_ref",
        "length",
        "append",
        "tail",
        "set_add",
        "set_remove",
    ],
    "policy": {
        "canonical_operations": True,
        "exact_reachable_input_bindings": True,
        "native_predicate_execution": False,
        "opaque_predicate_analysis": "unsupported",
    },
    "collection_values": {
        "set": "unordered_unique_array",
        "sequence": "ordered_array_with_duplicates",
        "map": "unordered_unique_key_value_entries",
        "select": "zero_based_sequence_or_map_key_with_required_default",
    },
    "definition_checks": ["schema", "references", "ownership", "types", "frames"],
    "finite_export": {"status": "optional_design_subset", "runner_available": True},
    "native_binding": "not_checked",
}


def describe():
    """Return detached capability data so consumers cannot mutate the declaration."""
    return deepcopy(DEFINITION_CAPABILITIES)
