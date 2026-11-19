"""Stable machine-readable failures for the portable behavior contract."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    """Locate one invalid definition without discarding its actual supplied value."""

    code: str
    path: str
    message: str

    def as_dict(self):
        return asdict(self)


class ContractError(ValueError):
    """A definition error; unsupported analysis is reported separately."""

    def __init__(self, code, path, message):
        self.diagnostic = Diagnostic(code, path, message)
        super().__init__(message)


def require(condition, code, path, message):
    if not condition:
        raise ContractError(code, path, message)


def index_records(records, path):
    """Index validated record envelopes, retaining a precise duplicate location."""
    result = {}
    for number, record in enumerate(records):
        ident = record["id"]
        require(ident not in result, "duplicate_id", f"{path}/{number}/id", ident)
        result[ident] = record
    return result
