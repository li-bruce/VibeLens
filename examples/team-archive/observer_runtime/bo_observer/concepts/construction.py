"""Source-backed construction work, distinct from executable concept definitions.

Targets can name work that has no valid model yet. They never enter the graph's
executable identity registry. Obligations are checked independently of questions.
"""

from copy import deepcopy

from ..definition_errors import index_records, require
from .common import digest

MODEL_KINDS = {"business_network", "state_model", "rule_operation"}


def affects_scope(reference, index, targets, coverage):
    """Include pending work without pretending that it is an executable node."""
    from .semantics import resolve_index

    if reference not in targets:
        return resolve_index(index, reference) in coverage
    item = targets[reference]
    if item.get("promoted_to"):
        return item["promoted_to"] in coverage
    # A not-yet-located target cannot silently disappear from the question list.
    # Known scopes can defer unrelated construction work to a later increment.
    return not item["scope_refs"] or any(
        ref in targets or resolve_index(index, ref) in coverage for ref in item["scope_refs"]
    )


def validate(doc, data):
    """Check provenance/references and derive gaps against the strict concept graph."""
    construction, registry, sources = doc["construction"], data["records"], data["sources"]
    targets = index_records(construction["targets"], "/construction/targets")
    obligations = index_records(construction["obligations"], "/construction/obligations")
    index_records(construction["presentations"], "/construction/presentations")
    gaps = []

    def resolve(ref, path):
        require(ref in registry or ref in targets, "unknown_construction_reference", path, ref)
        return targets[ref].get("promoted_to") if ref in targets else ref

    def provenance(item, path):
        require(
            set(item["source_refs"]) <= set(sources),
            "unknown_source",
            path,
            "Construction work must cite recorded requirements or interpretation",
        )

    for position, item in enumerate(construction["targets"]):
        path = f"/construction/targets/{position}"
        provenance(item, path + "/source_refs")
        require(item["id"] not in registry, "construction_identity_collision", path, item["id"])
        for ref in item["scope_refs"]:
            resolve(ref, path + "/scope_refs")
        promoted = item.get("promoted_to")
        if promoted:
            require(
                promoted in registry, "unknown_promoted_concept", path + "/promoted_to", promoted
            )
            expected = "relation" if item["kind"] == "interaction" else item["kind"]
            require(
                registry[promoted]["kind"] == expected,
                "promotion_kind",
                path,
                "Promoted concept differs from the requested model kind",
            )
            require(
                not item["unresolved"],
                "promotion_unresolved",
                path,
                "Resolve the target's declared gaps before promotion",
            )
        else:
            gaps.append(
                {
                    "id": item["id"],
                    "kind": "missing_model",
                    "target": item["id"],
                    "source_refs": item["source_refs"],
                    "meaning": item["meaning"],
                }
            )
    for position, item in enumerate(construction["obligations"]):
        path = f"/construction/obligations/{position}"
        provenance(item, path + "/source_refs")
        satisfied = False
        if item["kind"] == "model":
            ref = resolve(item["target_ref"], path + "/target_ref")
            expected = "relation" if item["target_kind"] == "interaction" else item["target_kind"]
            satisfied = ref in registry and registry[ref]["kind"] == expected
        elif item["kind"] == "state_owner":
            ref = resolve(item["object_ref"], path + "/object_ref")
            require(
                ref is None or registry[ref]["kind"] == "object",
                "state_owner_kind",
                path,
                "A state owner must be an object",
            )
            satisfied = any(
                value["kind"] == "state_model" and ref in data["dependencies"][ident]
                for ident, value in registry.items()
            )
        elif item["kind"] == "relation":
            source = resolve(item["from_ref"], path + "/from_ref")
            target = resolve(item["to_ref"], path + "/to_ref")
            satisfied = any(
                value["kind"] == "relation"
                and value["from"] == source
                and value["to"] == target
                and value["relation"] == item["relation"]
                for value in registry.values()
            )
        if not satisfied:
            gaps.append(
                {
                    "id": item["id"],
                    "kind": "missing_" + item["kind"],
                    "source_refs": item["source_refs"],
                    "meaning": item["meaning"],
                }
            )
    from .semantics import valid_snapshot

    for position, item in enumerate(construction["presentations"]):
        path = f"/construction/presentations/{position}"
        provenance(item, path + "/source_refs")
        require(
            valid_snapshot(item["snapshot"]) and item["scope"] == item["snapshot"]["scope"],
            "invalid_presentation_snapshot",
            path,
            "Presentation needs an exact semantic snapshot",
        )
        groups = [set(item[name]) for name in ("visible_refs", "explained_refs", "omitted_refs")]
        require(
            not any(groups[a] & groups[b] for a, b in ((0, 1), (1, 2), (0, 2)))
            and set.union(*groups) == set(item["scope"]),
            "presentation_scope",
            path,
            "Visible, explained and omitted scopes partition the presentation",
        )
        require(
            item["source_evidence"] == [sources[ref] for ref in item["source_refs"]],
            "presentation_source_changed",
            path,
            "Preserve the original presentation source",
        )
        require(
            set(item["targets"]) <= set(targets),
            "unknown_presentation_target",
            path,
            "Presentation target is not recorded",
        )
    if not registry and not targets:
        gaps.append(
            {
                "id": "construction:inventory",
                "kind": "unconfigured_inventory",
                "meaning": "Construct source-backed targets before reviewing an empty model",
            }
        )
    if not targets and not obligations:
        gaps.append(
            {
                "id": "construction:obligations",
                "kind": "unconfigured_obligations",
                "meaning": "Record source-backed modeling obligations before completeness review",
            }
        )
    return {
        "configured": bool(targets or obligations),
        "gaps": gaps,
        "ready": not gaps and bool(registry),
        "targets": deepcopy(targets),
        "obligations": sorted(obligations),
        "model_roots": sorted(
            ref for ref, value in registry.items() if value["kind"] in MODEL_KINDS
        ),
    }


def present(doc, scope, visible_refs, explained_refs, source_refs, identity, target_refs=()):
    """Create review evidence from a declared presentation; this does not confirm it."""
    from .model import build
    from .semantics import snapshot

    data = build(doc)
    require(
        doc["schema"] == "business-discovery/v3",
        "construction_version",
        "/schema",
        "Use discovery v3",
    )
    snap = snapshot(doc, scope)
    visible, explained = set(visible_refs), set(explained_refs)
    require(
        not visible & explained and visible | explained <= set(snap["scope"]),
        "presentation_scope",
        "/presentation",
        "Presented concepts must belong to this snapshot",
    )
    require(
        bool(source_refs) and set(source_refs) <= set(data["sources"]),
        "unknown_source",
        "/presentation/source_refs",
        "Record where the model was shown",
    )
    targets = {item["id"]: item for item in doc["construction"]["targets"]}
    require(
        set(target_refs) <= set(targets),
        "unknown_presentation_target",
        "/presentation/targets",
        "Unknown target",
    )
    return {
        "id": identity,
        "scope": snap["scope"],
        "snapshot": snap,
        "visible_refs": sorted(visible),
        "explained_refs": sorted(explained),
        "omitted_refs": sorted(set(snap["scope"]) - visible - explained),
        "source_refs": list(source_refs),
        "source_evidence": [deepcopy(data["sources"][r]) for r in source_refs],
        "targets": {ref: digest(targets[ref]) for ref in target_refs},
    }


def check_presentation(doc, snapshot, identity, *, current=False):
    """Reject unseen or revised meaning without discarding historical presentations."""
    item = next((p for p in doc["construction"]["presentations"] if p["id"] == identity), None)
    require(
        item is not None, "missing_presentation", "/confirmation/presentation_ref", str(identity)
    )
    reviewed = set(item["visible_refs"]) | set(item["explained_refs"])
    require(
        set(snapshot["scope"]) <= reviewed,
        "unreviewed_boundary",
        "/confirmation/scope",
        "The confirmation includes omitted or unseen meaning",
    )
    require(
        all(
            item["snapshot"]["records"].get(ref) == value
            for ref, value in snapshot["records"].items()
        ),
        "stale_presentation",
        "/confirmation/snapshot",
        "Review the changed meaning before confirming",
    )
    if current:
        targets = {t["id"]: t for t in doc["construction"]["targets"]}
        require(
            all(digest(targets.get(ref)) == checksum for ref, checksum in item["targets"].items()),
            "stale_presentation_target",
            "/confirmation",
            "Construction targets changed since presentation",
        )


def promote(doc, target_id, candidate, concept_ref, expected_revision):
    """Return one validated replacement; invalid drafts never partially promote."""
    from .model import build

    require(
        digest(doc) == expected_revision,
        "stale_construction_revision",
        "/construction",
        "Reload the current draft",
    )
    build(doc)
    result = deepcopy(candidate)
    old = {t["id"]: t for t in doc["construction"]["targets"]}
    require(target_id in old, "unknown_construction_target", "/construction", target_id)
    items = {t["id"]: t for t in result["construction"]["targets"]}
    require(
        target_id in items and items[target_id] == old[target_id],
        "construction_target_changed",
        "/construction",
        "Preserve target provenance while adding the candidate model",
    )
    require(not old[target_id].get("promoted_to"), "already_promoted", "/construction", target_id)
    items[target_id].update(promoted_to=concept_ref, unresolved=[])
    build(result)
    from . import assess

    require(
        all(items.get(ref) == original for ref, original in old.items() if ref != target_id),
        "construction_target_changed",
        "/construction",
        "Preserve unrelated construction work",
    )
    review = assess(result, doc)
    require(
        review["valid"],
        "promotion_history",
        "/construction",
        "Preserve prior confirmation and presentation evidence: " + str(review["errors"]),
    )
    return result
