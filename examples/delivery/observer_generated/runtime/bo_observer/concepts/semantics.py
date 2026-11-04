"""Scoped immutable semantic snapshots and dependency-aware change summaries."""

from copy import deepcopy

from .common import digest, encoded, records
from .model import build


def resolve_index(index, reference):
    if reference in index:
        return reference
    matches = [key for key, value in index.items() if reference in value["aliases"]]
    if len(matches) != 1:
        raise ValueError("unknown or ambiguous concept reference: " + str(reference))
    return matches[0]


def resolve(doc, reference):
    """Resolve exact IDs first; a shared raw alias never selects an arbitrary node."""
    return resolve_index(build(doc)["index"], reference)


def selection(data, requested=None, *, expand_networks=True):
    """Expand semantic prerequisites and explicit obligations, not arbitrary reachability."""
    index, dependencies = data["index"], data["dependencies"]
    if requested is None or requested == ["*"]:
        return sorted(index)
    if not isinstance(requested, list) or not requested:
        raise ValueError("concept scope must be nonempty")
    pending = [resolve_index(index, ref) for ref in requested]
    selected = set()
    while pending:
        ident = pending.pop()
        if ident in selected:
            continue
        selected.add(ident)
        pending.extend(dependencies[ident])
        # A selected operation carries its declared applicability and independent
        # examples. Neither may be omitted by selecting the action alone.
        pending.extend(
            key
            for key, value in data["records"].items()
            if (value["kind"] == "applicability" and value["operation"] == ident)
            or (value["kind"] == "expectation" and ident in dependencies[key])
        )
        if index[ident]["kind"] == "state_model":
            member_kinds = {
                "state",
                "event",
                "guard",
                "logical_effect",
                "transition",
                "activity",
                "resource",
                "join",
            }
            pending.extend(
                key
                for key, deps in dependencies.items()
                if ident in deps and index[key]["kind"] in member_kinds
            )
        if index[ident]["kind"] == "business_network":
            # Selecting a network explicitly includes its behavior and routes.
            # A node's context dependency alone does not silently approve peers.
            if expand_networks and ident in [resolve_index(index, ref) for ref in requested]:
                pending.extend(key for key, deps in dependencies.items() if ident in deps)
    # Include relationships only when both meanings are in this explicit scope.
    for key, value in data["records"].items():
        if value["kind"] == "relation" and set(dependencies[key]) <= selected:
            selected.add(key)
    return sorted(selected)


def semantic_projection(doc, scope=None):
    data = build(doc)
    selected = selection(data, scope if scope is not None else doc.get("scope"))
    return {key: deepcopy(data["records"][key]) for key in selected}


def snapshot(doc, scope=None):
    """Create a detached meaning snapshot; this is not itself a confirmation."""
    selected = semantic_projection(doc, scope)
    return snapshot_records(selected)


def snapshot_records(selected):
    """Hash an already selected closure without reinterpreting its grouping roots."""
    payload = {
        "schema": "bo-concept-snapshot/v1",
        "scope": sorted(selected),
        "records": deepcopy(selected),
    }
    return {**payload, "semantic_revision": digest(payload)}


def valid_snapshot(value):
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "scope",
        "records",
        "semantic_revision",
    }:
        return False
    return (
        value["schema"] == "bo-concept-snapshot/v1"
        and isinstance(value["records"], dict)
        and value["scope"] == sorted(value["records"])
        and value["semantic_revision"]
        == digest({key: value[key] for key in ["schema", "scope", "records"]})
    )


def confirm(doc, scope, source_refs, id):
    """Return a proposed confirmation record from exact user evidence, without writes.

    The coding host must obtain the actual confirmation. This checks its recorded
    provenance; it cannot authenticate a quotation or infer assent from silence.
    """
    data = build(doc)
    if (
        not isinstance(id, str)
        or not id.strip()
        or not isinstance(source_refs, list)
        or not source_refs
        or len(set(source_refs)) != len(source_refs)
    ):
        raise ValueError("confirmation needs identity and distinct user sources")
    evidence = []
    for ref in source_refs:
        value = data["sources"].get(ref)
        if not value or value["kind"] != "user":
            raise ValueError("confirmation must cite actual recorded user sources")
        evidence.append(deepcopy(value))
    snap = snapshot(doc, scope)
    return {
        "id": id,
        "scope": snap["scope"],
        "source_refs": list(source_refs),
        "source_evidence": evidence,
        "snapshot": snap,
    }


def check_confirmations(doc, previous=None, *, scope=None):
    """Keep historical snapshots immutable; stale confirmations cannot approve new meaning."""
    data = build(doc)
    requested = scope if scope is not None else doc.get("scope")
    selected = selection(data, requested)
    confirmations = records(doc["confirmations"], "confirmations")
    errors, matched = [], set()
    old = records(previous.get("confirmations", []), "previous confirmations") if previous else {}
    for ident, item in old.items():
        if confirmations.get(ident) != item:
            errors.append({"code": "immutable_confirmation_changed", "item": ident})
    # A shared dependency cannot be changed under a narrowed active scope while
    # leaving previously confirmed consumers silently stale. Historical semantic
    # snapshots provide the impact boundary even without a previous document.
    historic = set()
    changed = set()
    for item in confirmations.values():
        snap = item.get("snapshot", {})
        if not valid_snapshot(snap):
            continue
        historic.update(snap["records"])
        changed.update(
            key
            for key, value in snap["records"].items()
            if encoded(data["records"].get(key)) != encoded(value)
        )
    if previous and previous.get("schema") == "business-discovery/v2":
        changed.update(diff(previous, doc)["affected"])
    impacted = set(changed)
    growing = True
    while growing:
        growing = False
        for key, deps in data["dependencies"].items():
            if key not in impacted and impacted.intersection(deps):
                impacted.add(key)
                growing = True
    selected = sorted(set(selected) | (impacted & historic & set(data["index"])))
    prior_sources = {s["id"] for c in old.values() for s in c.get("source_evidence", [])}
    source_meanings = {}
    for ident, item in confirmations.items():
        if (
            set(item) != {"id", "scope", "source_refs", "source_evidence", "snapshot"}
            or not valid_snapshot(item.get("snapshot"))
            or item.get("scope") != item["snapshot"]["scope"]
        ):
            errors.append({"code": "invalid_confirmation_snapshot", "item": ident})
            continue
        refs, evidence = item.get("source_refs"), item.get("source_evidence")
        if (
            not isinstance(refs, list)
            or not refs
            or not isinstance(evidence, list)
            or len(refs) != len(evidence)
            or len(set(refs)) != len(refs)
        ):
            errors.append({"code": "invalid_confirmation_sources", "item": ident})
            continue
        if any(
            data["sources"].get(ref) != original
            or original.get("kind") != "user"
            or original.get("id") != ref
            for ref, original in zip(refs, evidence)
        ):
            errors.append({"code": "confirmation_source_changed", "item": ident})
            continue
        actual = item["snapshot"]["records"]
        # Persisted history is sufficient to reject reusing the same utterance
        # for conflicting meanings, even when a runtime caller has no separate
        # previous-document file available.
        conflict = any(
            key in source_meanings.get(ref, {}) and source_meanings[ref][key] != encoded(value)
            for ref in refs
            for key, value in actual.items()
        )
        if conflict:
            errors.append({"code": "changed_meaning_needs_new_user_source", "item": ident})
            continue
        for ref in refs:
            source_meanings.setdefault(ref, {}).update(
                {key: encoded(value) for key, value in actual.items()}
            )
        if ident not in old and old and set(refs) <= prior_sources:
            # Reusing a previous acknowledgment is not authorization for a new
            # semantic snapshot. Labels/source-only changes need no new snapshot.
            if not any(encoded(c["snapshot"]["records"]) == encoded(actual) for c in old.values()):
                errors.append({"code": "changed_meaning_needs_new_user_source", "item": ident})
                continue
        current = data["records"]
        for key in selected:
            if key in actual and encoded(actual[key]) == encoded(current[key]):
                # A dependency changed even if this node's own local fields did not.
                required = selection(data, [key], expand_networks=False)
                if all(encoded(actual.get(dep)) == encoded(current[dep]) for dep in required):
                    matched.add(key)
    blocked = sorted(set(selected) - matched)
    removed = historic - set(data["index"])
    if removed:
        # A narrowed scope must not silently retire previously confirmed work.
        # A fresh full-current-model acknowledgment can confirm a displayed
        # removal diff; a scoped acknowledgment cannot attest to missing nodes.
        removal_sources = {
            ref
            for item in confirmations.values()
            if removed.intersection(item.get("snapshot", {}).get("records", {}))
            for ref in item.get("source_refs", [])
        }
        retirement_confirmed = any(
            valid_snapshot(item.get("snapshot"))
            and encoded(item["snapshot"]["records"]) == encoded(data["records"])
            and set(item.get("source_refs", [])) - removal_sources
            for item in confirmations.values()
        )
        if not retirement_confirmed:
            blocked.extend("retired:" + ident for ident in sorted(removed))
    return {
        "valid": not errors,
        "ready": not errors and not blocked,
        "errors": errors,
        "blocked": blocked,
        "coverage_scope": selected,
        "retired": sorted(removed),
        "shared_dependents_requiring_review": sorted(impacted & historic & set(data["index"])),
    }


def diff(previous, current, scope=None):
    """Report structural semantic changes and all explicit shared dependents."""
    if previous.get("schema") == "business-discovery/v1":
        # V1 has no complete source-free state/rule contract to compare. Treat
        # the first v2 snapshot as new evidence rather than claiming equivalence
        # or manufacturing a semantic delta from display-only legacy nodes.
        current_snapshot = snapshot(current, scope)
        return {
            "semantic_change": True,
            "migration": "legacy-v1",
            "added": current_snapshot["scope"],
            "removed": [],
            "changed": [],
            "affected": current_snapshot["scope"],
        }
    old, new = build(previous), build(current)
    before, after = old["records"], new["records"]
    allowed = set(before) | set(after)
    if scope is not None:
        allowed = set(selection(new, scope))
    added, removed = sorted((set(after) - set(before)) & allowed), sorted(
        (set(before) - set(after)) & allowed
    )
    changed = sorted(
        key
        for key in set(before) & set(after) & allowed
        if encoded(before[key]) != encoded(after[key])
    )
    affected = set(added + removed + changed)
    growing = True
    while growing:
        growing = False
        for model in [old, new]:
            for key, deps in model["dependencies"].items():
                if key not in affected and affected.intersection(deps):
                    affected.add(key)
                    growing = True
    return {
        "semantic_change": bool(added or removed or changed),
        "added": added,
        "removed": removed,
        "changed": [
            {"id": key, "before": deepcopy(before[key]), "after": deepcopy(after[key])}
            for key in changed
        ],
        "affected": sorted(affected),
    }
