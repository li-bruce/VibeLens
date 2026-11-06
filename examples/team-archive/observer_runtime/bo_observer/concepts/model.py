"""Assemble peer conceptual models through one typed identity registry.

Validation is source-free. Runtime bindings and independent observations are
checked later, without substituting this model for the application executor.
"""

from ..protocol import schema_check
from .common import records, text
from .business import add_business, add_objects
from .state import validate_objects, validate_states, validate_facts
from .state_projection import add_states
from .rules import add_rules, policy_semantics as policy_semantics
from .registry import ConceptGraph
from .obligations import add_crosslinks, add_applicability, add_expectations
from .presentation import apply_routes

VERSION = "business-discovery/v2"


def build(doc):
    """Validate the portable design and assemble display/semantic representations."""
    if not isinstance(doc, dict) or doc.get("schema") != VERSION:
        raise ValueError("expected " + VERSION)
    schema_check(doc, "discovery")
    sources = records(doc["sources"], "sources", empty=False)
    for ident, source in sources.items():
        if (
            source.get("kind") not in {"user", "project_rule", "assistant", "inference"}
            or not text(source.get("text"))
            or not text(source.get("locator"))
        ):
            raise ValueError("source needs kind, original text and locator: " + ident)
    objects = validate_objects(doc, sources)
    state_indexes = validate_states(doc, objects, sources)
    facts = validate_facts(doc, objects, sources)
    graph = ConceptGraph()
    business = add_business(graph, doc, sources)
    add_objects(graph, objects, facts)
    models = add_states(graph, doc, state_indexes)
    policy = add_rules(graph, doc, sources)
    graph.resolve_dependencies()
    crosslinks = add_crosslinks(graph, doc, sources)
    add_applicability(graph, doc, sources, business, models, policy, crosslinks)
    add_expectations(graph, doc, sources)
    result = graph.result(sources)
    apply_routes(result, doc.get("presentation"), sources)
    return result
