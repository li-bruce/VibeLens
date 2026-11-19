"""Compute finite representation sizes without enumerating states or huge integers.

A missing count can mean a finite but impractically large domain. It is distinct
from an unbounded domain and from a completed model-checking result.
"""

from math import comb

SAFE_COUNT = 9007199254740991


def _power(base, exponent):
    """Return an exact portable count, or None once the JSON range is exceeded."""
    result = 1
    while exponent:
        if exponent & 1:
            result *= base
            if result > SAFE_COUNT:
                return None
        exponent >>= 1
        if exponent:
            base = min(base * base, SAFE_COUNT + 1)
    return result


def collection_size(kind, size, element, key=None):
    """Classify a container; finite length alone does not bound payload or keys."""
    if size == 0:
        return {"supported": True, "cardinality": 1}
    if size is None and kind == "sequence":
        return {"supported": False, "reason": "unbounded_length"}
    for role, domain in (("element", element), ("key", key)):
        if domain is not None and not domain["supported"]:
            return {
                "supported": False,
                "reason": "unbounded_" + role,
                "dependency_reason": domain["reason"],
            }
    n = element["cardinality"]
    k = key["cardinality"] if key is not None else None
    count = None
    if kind == "sequence" and n is not None:
        if n == 1:
            count = size + 1
        else:
            # The geometric-series numerator can exceed JSON's safe range while
            # the actual sum still fits. Summation stops after at most 54 terms
            # for a non-singleton element domain, regardless of the length cap.
            count, term = 1, 1
            for _ in range(size):
                term *= n
                count += term
                if count > SAFE_COUNT:
                    count = None
                    break
    elif kind == "set" and n is not None:
        limit = n if size is None else min(size, n)
        if limit == n:
            count = _power(2, n)
        else:
            count = 1
            for length in range(1, limit + 1):
                count += comb(n, length)
                if count > SAFE_COUNT:
                    count = None
                    break
    elif kind == "map" and n is not None and k is not None:
        limit = k if size is None else min(size, k)
        if limit == k:
            count = _power(n + 1, k)
        else:
            count = 1
            for length in range(1, limit + 1):
                term = _power(n, length)
                if term is None:
                    count = None
                    break
                count += comb(k, length) * term
                if count > SAFE_COUNT:
                    count = None
                    break
    if count is not None and count > SAFE_COUNT:
        count = None
    result = {"supported": True, "cardinality": count}
    if count is None:
        result["cardinality_note"] = "finite_count_exceeds_portable_range"
    return result
