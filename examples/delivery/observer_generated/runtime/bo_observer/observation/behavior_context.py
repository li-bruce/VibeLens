"""Pin read-only behavior details and protect their artifact freshness in a session."""

from copy import deepcopy
import json

from ..behavior.presentation import project
from ..graph.source_files import SourceFiles
from ..project_artifacts import byte_hash, references
from ..concepts.common import digest


def design_context(root, discovery):
    """Optionally enrich a draft using its own pinned behavior, not another revision.

    An invalid/incomplete project remains inspectable as a design. Its behavior
    details are explicitly unavailable; native loading retains its strict errors.
    """
    from ..project_artifacts import load_bundle, parse

    sources = SourceFiles(root)
    try:
        raw = sources.read("sync.json")
        config = parse(raw) if raw else {}
        name = config.get("model", "bo_stategraph/project.json")
        raw = sources.read(name)
        if raw is None:
            return None
        envelope = parse(raw)
        if not envelope.get("contracts", {}).get("behavior"):
            return None
        envelope, documents = load_bundle(root, name)
        if digest(documents["discovery"]) != digest(discovery):
            raise ValueError("Draft and pinned behavior have different definitions")
        return BehaviorContext(root, envelope, documents).view()
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"status": "unavailable", "error": str(error)}


class BehaviorContext:
    """Use the same loaded bundle as native admission, without a second state engine."""

    def __init__(self, root, envelope, documents):
        self.sources = SourceFiles(root)
        self.inputs = {ref["path"]: ref["sha256"] for _, ref in references(envelope)}
        contract = documents.get("behavior")
        self.details = (
            project(contract, documents["discovery"], envelope["model"]) if contract else None
        )

    def changed_inputs(self):
        """Check actual bytes, including same-size edits with unchanged timestamps."""
        changed = []
        for name, expected in self.inputs.items():
            try:
                raw = self.sources.read(name)
                if raw is None or byte_hash(raw) != expected:
                    changed.append(name)
            except (OSError, ValueError):
                changed.append(name)
        return changed

    def last_verification(self):
        """Display the latest recorded check; do not claim it certifies this live build.

        Reuse/current acceptance remains the coordinator's responsibility. This
        lightweight reader carries the original candidate and date, not a forged
        successful status inferred from a saved graph or a receipt's existence.
        """
        try:
            raw = self.sources.read(".stategraph/active.json")
            if raw is None:
                return None
            path = json.loads(raw)["change"] + "/verification.json"
            raw = self.sources.read(path)
            if raw is None:
                return None
            record = json.loads(raw)
            categories = record.get("behavior_coverage", {}).get("categories", {})
            return {
                "candidate_id": record["candidate_id"],
                "checked_at": record["checked_at"],
                "valid": record["valid"],
                "freshness": "recorded",
                "categories": {
                    key: {field: value[field] for field in ("status", "coverage") if field in value}
                    for key, value in categories.items()
                },
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return {"freshness": "unavailable"}

    def view(self):
        """Return detached metadata only at a full viewer/recording boundary."""
        if self.details is None:
            return None
        return {**deepcopy(self.details), "last_verification": self.last_verification()}
