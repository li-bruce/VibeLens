"""Compare selected observations with independently read native records.

Rows join by declared model/object/invocation/attempt/build keys, never by arrival
order or nearby timestamps. Mapping accuracy is separate from domain validity.
"""

from dataclasses import replace

from .domains import value_key


def at(value, path):
    """Missing differs from an explicit null; invalid path types remain errors."""
    for part in path:
        if isinstance(value, dict) and type(part) is str:
            value = value[part]
        elif isinstance(value, list) and type(part) is int and 0 <= part < len(value):
            value = value[part]
        else:
            raise ValueError("Missing native/observed path: " + repr(path))
    return value


def matches(event, site):
    """Match explicit recorded selectors; no label, time or owner inference."""
    if event.get("node") != site["node"] or event.get("phase") != site["phase"]:
        return False
    try:
        return all(
            value_key(at(event, item["path"])) == value_key(item["equals"])
            for item in site.get("when", [])
        )
    except (KeyError, ValueError, TypeError):
        return False


def application_domain(domain):
    """Remove analysis-only restrictions for diagnostics of actual application values."""
    changes = {}
    if domain.bound_origin in {"analysis_bound", "abstraction"}:
        changes.update(minimum=None, maximum=None, max_items=None)
        if domain.kind == "identity":
            changes.update(identity_policy="generated", values=())
    if domain.element is not None:
        changes["element"] = application_domain(domain.element)
    if domain.key is not None:
        changes["key"] = application_domain(domain.key)
    return replace(domain, **changes)


def compare_values(run, witness, *, build_id, owners, domain=None):
    """Return actual correspondence checks and separate domain findings.

    Independent values come from the configured reader's native collection.
    This service consumes that evidence; source checks and independent tests
    establish how it was collected. It never calls the reader or repairs data.
    """
    errors, checks, domains = [], [], []
    native = witness["native"]
    pairs = native["keys"]

    def identity(item, side):
        values = {pair["name"]: at(item, pair[side]) for pair in pairs}
        if values["model"] not in owners or values["build"] != build_id:
            raise ValueError("Native/observed model or build differs from the binding")
        if any(v is None or isinstance(v, (dict, list, bool)) for v in values.values()):
            raise ValueError("Missing or ambiguous native identity")
        return tuple(value_key(values[pair["name"]]) for pair in pairs)

    try:
        rows = at(run, native["collection"])
        if not isinstance(rows, list) or not rows:
            raise ValueError("Independent native records are missing")
        keyed = {}
        for row in rows:
            key = identity(row, "actual")
            if key in keyed:
                raise ValueError(
                    "Duplicate native identity; bind a sample/revision key for repeated reads"
                )
            keyed[key] = row
        events = [
            event
            for event in run.get("events", [])
            if not event.get("context_only") and matches(event, witness["observation"])
        ]
        seen = set()
        for event in events:
            try:
                key = identity(event, "observed")
                if key not in keyed:
                    raise ValueError("Observed value has no independently read native record")
                actual = at(keyed[key], native["value"])
                observed = at(event, witness["observation"]["path"])
                if key in seen:
                    raise ValueError("Repeated observation needs its own sample/revision identity")
                seen.add(key)
                # Invalid native values still need faithful capture. Normalize
                # collections only when their representations are valid; a bad
                # application value must not become a failed mapping by accident.
                accepted = domain is not None and application_domain(domain).accepts(actual)
                compare = domain.value_key if accepted else value_key
                equal = compare(actual) == compare(observed)
                checks.append(
                    {"event": event["id"], "matches": equal, "actual": actual, "observed": observed}
                )
                if not equal:
                    errors.append({"code": "native_value_differs", "event": event["id"]})
                if domain is not None and not domain.accepts(actual):
                    domains.append(
                        {
                            "event": event["id"],
                            "actual": actual,
                            "status": (
                                "outside_analysis_domain"
                                if application_domain(domain).accepts(actual)
                                else "outside_application_domain"
                            ),
                        }
                    )
            except (KeyError, ValueError, TypeError) as error:
                errors.append(
                    {
                        "code": "native_value_unmatched",
                        "event": event.get("id"),
                        "message": str(error),
                    }
                )
        if set(keyed) - seen:
            errors.append({"code": "native_value_not_captured", "count": len(set(keyed) - seen)})
    except (KeyError, ValueError, TypeError) as error:
        errors.append({"code": "native_reader_evidence", "message": str(error)})
    return {"valid": not errors, "errors": errors, "checks": checks, "domains": domains}
