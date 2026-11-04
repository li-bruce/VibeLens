"""Resolve preserved assertion IDs for narrowly consolidated concept relations.

These are original semantic assertions, not renamed edges or inferred paths.
Only a transition's declared effect and its identical argument-free crosslink
share a display edge. Native events and semantic validation retain their IDs.
"""

_ASSERTION_FIELDS = {"id", "from", "to", "type", "label", "origin", "evidence_kind", "source_refs"}


def relation_assertions(edge):
    """Return the representative and original assertions, rejecting unsafe aliases.

    An unknown field may carry parameters, timing, scope or guard semantics. Such
    an edge must never acquire an equivalence merely because endpoints match.
    """
    originals = edge.get("equivalent_relations", [])
    if not isinstance(originals, list):
        raise ValueError("invalid equivalent concept relation: " + str(edge.get("id")))
    if not originals:
        return [edge]
    if (
        set(edge) - (_ASSERTION_FIELDS | {"equivalent_relations"})
        or edge.get("type") != "has_effect"
        or edge.get("origin") != "concept-design"
        or edge.get("evidence_kind") != "conceptual"
    ):
        raise ValueError("invalid equivalent concept relation: " + str(edge.get("id")))
    for original in originals:
        if (
            not isinstance(original, dict)
            or set(original) - _ASSERTION_FIELDS
            or not isinstance(original.get("id"), str)
            or not original["id"]
            or original.get("type") != "transition_has_effect"
            or original.get("from") != edge.get("from")
            or original.get("to") != edge.get("to")
            or original.get("origin") != "concept-design"
            or original.get("evidence_kind") != "conceptual"
        ):
            raise ValueError("invalid equivalent concept relation: " + str(edge.get("id")))
    return [edge, *originals]


def relation_ids(edge):
    """List stable source IDs represented by this display edge."""
    return [assertion["id"] for assertion in relation_assertions(edge)]


def matches_relation(edge, types):
    """Allow a focus filter to select either original assertion's relation type."""
    return types is None or any(item["type"] in types for item in relation_assertions(edge))


def relation_index(edges):
    """Map every original ID to one display edge; ambiguous identities are errors."""
    result = {}
    for edge in edges:
        for ident in relation_ids(edge):
            if ident in result:
                raise ValueError("duplicate or ambiguous relation identity: " + str(ident))
            result[ident] = edge
    return result
