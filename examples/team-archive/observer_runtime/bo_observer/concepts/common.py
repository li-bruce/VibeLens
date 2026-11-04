"""Small portable identities and checks shared by conceptual design modules."""

from copy import deepcopy
from hashlib import sha256
import json
from urllib.parse import quote


def canonical_id(kind, *parts):
    """Keep concepts independent of labels and avoid separator collisions."""
    return kind + ":" + ":".join(quote(str(part), safe="") for part in parts)


def encoded(value):
    """Use type-preserving, portable JSON for semantic equality."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(encoded(value).encode("utf-8")).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def fields(value, allowed, required, name):
    if not isinstance(value, dict):
        raise ValueError(name + " must be an object")
    missing, unknown = set(required) - set(value), set(value) - set(allowed)
    if missing or unknown:
        raise ValueError(
            name + " fields: missing=" + str(sorted(missing)) + "; unknown=" + str(sorted(unknown))
        )


def records(values, name, *, empty=True):
    if not isinstance(values, list) or (not empty and not values):
        raise ValueError(name + " must be " + ("a nonempty" if not empty else "a") + " list")
    result = {}
    for item in values:
        if not isinstance(item, dict) or not text(item.get("id")) or item["id"] in result:
            raise ValueError(name + " needs unique nonempty IDs")
        result[item["id"]] = item
    return result


def references(item, sources, name):
    refs = item.get("source_refs")
    if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs):
        raise ValueError(name + " needs distinct source_refs")
    if any(not isinstance(ref, str) or ref not in sources for ref in refs):
        raise ValueError(name + " references an unknown source")


DISPLAY = {"label", "summary", "description", "source_refs", "documentation", "presentation"}


def without_display(value):
    """Remove metadata from one known record envelope, preserving its values.

    Fields named ``label`` or ``description`` inside a parameter map, payload,
    domain meaning or expected result are business data. Never recursively drop
    keys by spelling. Callers normalize nested *record envelopes* explicitly.
    """
    if isinstance(value, dict):
        return {key: deepcopy(item) for key, item in value.items() if key not in DISPLAY}
    return deepcopy(value)
