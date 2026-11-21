"""Detach validated JSON documents at display and persistence boundaries."""

import json


def copy_json(value):
    """Copy a JSON tree without walking every scalar through Python's deepcopy.

    Use this only after the JSON contract boundary: keys are strings, values are
    finite JSON primitives, and identity/aliasing is not part of the document.
    General native Python objects still require their original copy mechanism.
    No result is shared with the input or cached across source revisions.
    """
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
