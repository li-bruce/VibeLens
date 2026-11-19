"""Shared pure diagnostics for conceptual and behavior definitions."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    """Locate one invalid supplied value without normalizing it away."""

    code: str
    path: str
    message: str

    def as_dict(self):
        return asdict(self)


class ContractError(ValueError):
    """A definition error, distinct from unsupported optional analysis."""

    def __init__(self, code, path, message):
        self.diagnostic = Diagnostic(code, path, message)
        super().__init__(message)


def require(condition, code, path, message):
    if not condition:
        raise ContractError(code, path, message)


def pointer(path, token):
    """Append a dictionary key with JSON-pointer escaping."""
    return path.rstrip("/") + "/" + str(token).replace("~", "~0").replace("/", "~1")


def index_records(records, path):
    """Index validated envelopes while retaining the duplicate's exact location."""
    result = {}
    for number, record in enumerate(records):
        ident = record["id"]
        require(ident not in result, "duplicate_id", f"{path}/{number}/id", ident)
        result[ident] = record
    return result
