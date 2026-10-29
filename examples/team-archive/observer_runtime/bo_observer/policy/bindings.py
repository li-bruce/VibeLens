"""Check the supplied callable against the current source without importing it."""

import hashlib
import inspect
import marshal
from pathlib import Path
from types import CodeType


def code_signature(code):
    """Ignore line offsets, retaining executable bytecode, constants and names."""
    return (
        code.co_code,
        tuple(code_signature(c) if isinstance(c, CodeType) else c for c in code.co_consts),
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_cellvars,
        code.co_argcount,
        code.co_posonlyargcount,
        code.co_kwonlyargcount,
        code.co_flags,
    )


def callable_binding(callback, source, root):
    """Reject stale loaded functions even when the file on disk was updated."""
    actual = inspect.unwrap(callback)
    root = Path(root).resolve()
    path = (root / source["path"]).resolve()
    actual_path = inspect.getsourcefile(actual)
    symbol = getattr(actual, "__qualname__", "").replace(".<locals>.", ".")
    if (
        not path.is_relative_to(root)
        or actual_path is None
        or Path(actual_path).resolve() != path
        or symbol != source["symbol"]
        or not hasattr(actual, "__code__")
    ):
        raise ValueError("native predicate source differs: " + source["symbol"])
    raw = path.read_bytes()
    compiled = compile(raw, str(path), "exec", dont_inherit=True)
    candidates = []

    def walk(code):
        if code.co_qualname.replace(".<locals>.", ".") == symbol:
            candidates.append(code)
        for value in code.co_consts:
            if isinstance(value, CodeType):
                walk(value)

    walk(compiled)
    if len(candidates) != 1 or code_signature(candidates[0]) != code_signature(actual.__code__):
        raise ValueError("loaded policy function differs from current source: " + symbol)
    return {
        **source,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "code_sha256": hashlib.sha256(marshal.dumps(code_signature(actual.__code__))).hexdigest(),
    }
