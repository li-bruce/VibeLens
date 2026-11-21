"""Reuse a canonical model hash only when its full in-memory value is unchanged."""

import marshal


class CanonicalDigest:
    """Keep one exact serialization beside its previously computed JSON digest.

    Source files are still read independently at each admission boundary. This
    cache covers only a loaded JSON declaration, whose sorted JSON encoding is
    otherwise repeated for every event batch. ``marshal`` is used solely as a
    fast, type-sensitive equality key in this process: it is never loaded,
    persisted, sent over the protocol, or substituted for the canonical digest.
    Different dictionary ordering or aliasing can miss the cache harmlessly.
    Nested edits and changes such as ``1`` to ``True`` invalidate the key.
    """

    def __init__(self, canonical):
        self._canonical = canonical
        self._entry = None

    def __call__(self, value):
        """Return the original digest, recomputing it whenever any value changes.

        Only one entry is retained. Publishing the pair together also keeps
        concurrent readers from combining one declaration's key with another's
        digest. Unsupported native values use the original validator/serializer;
        a failed canonical encoding is never cached.
        """
        try:
            signature = marshal.dumps(value, 4)
        except (ValueError, TypeError, OverflowError):
            return self._canonical(value)
        entry = self._entry
        if entry is not None and signature == entry[0]:
            return entry[1]
        result = self._canonical(value)
        self._entry = (signature, result)
        return result
