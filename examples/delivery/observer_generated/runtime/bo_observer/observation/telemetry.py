"""Source-bound registrations for optional technical instrumentation.

Registrations are project-owned JSON. They select known graph nodes, never create
business nodes from HTTP names, and never replace the application state machine.
"""

from pathlib import Path
import json

CONFIG = "bo_stategraph/telemetry.json"


def validate_registrations(value, model):
    """Reject ambiguous selectors, stale source bindings and undeclared payload fields."""
    if not isinstance(value, dict) or set(value) != {"protocol", "backend", "registrations"}:
        raise ValueError("invalid telemetry configuration fields")
    if value["protocol"] != "bo-telemetry/v1" or value["backend"] != "opentelemetry":
        raise ValueError("unsupported telemetry backend/protocol")
    items = value["registrations"]
    if not isinstance(items, list) or len(items) > 512:
        raise ValueError("invalid telemetry registrations")
    nodes, selectors = {n["id"]: n for n in model["nodes"]}, set()
    for item in items:
        if not isinstance(item, dict) or set(item) - {"node", "source", "match", "capture"}:
            raise ValueError("invalid telemetry registration")
        node = nodes.get(item.get("node"))
        if not node or not node.get("source") or item.get("source") != node["source"]:
            raise ValueError("telemetry registration needs an exact current source binding")
        if node.get("layer") == "business":
            raise ValueError("automatic technical spans require API/execution/data nodes")
        match = item.get("match")
        if not isinstance(match, dict) or set(match) - {"name", "attributes"}:
            raise ValueError("invalid telemetry selector")
        if not match or not (match.get("name") or match.get("attributes")):
            raise ValueError("empty telemetry selector")
        if "name" in match and (not isinstance(match["name"], str) or not match["name"]):
            raise ValueError("invalid span name selector")
        attributes = match.get("attributes", {})
        if not isinstance(attributes, dict) or any(
            not isinstance(k, str) or not k or type(v) not in (str, int, bool)
            for k, v in attributes.items()
        ):
            raise ValueError("telemetry selectors require scalar attribute equality")
        key = json.dumps(match, sort_keys=True)
        if key in selectors:
            raise ValueError("duplicate telemetry selector")
        selectors.add(key)
        capture = item.get("capture", {})
        if not isinstance(capture, dict) or set(capture) - {"in", "out"}:
            raise ValueError("invalid telemetry capture mapping")
        for direction, mapping in capture.items():
            if not isinstance(mapping, dict) or set(mapping) - set(
                node.get("capture", {}).get(direction, {})
            ):
                raise ValueError("telemetry capture field is not declared on its node")
            if any(not isinstance(attr, str) or not attr for attr in mapping.values()):
                raise ValueError("telemetry capture needs attribute names")
    return value


def load_registrations(root, model):
    """Absence keeps the native backend; an invalid selected backend is a hard error."""
    path = Path(root) / CONFIG
    if not path.is_file():
        return None
    if CONFIG not in model.get("source_files", []):
        raise ValueError(
            "telemetry configuration must be included in model.source_files for build identity"
        )
    return validate_registrations(json.loads(path.read_text(encoding="utf-8")), model)


def automatic_sites(configuration, index):
    """A registration is a static site declaration; runtime cases still prove capture."""
    sites = []
    for item in (configuration or {}).get("registrations", []):
        symbol = item["source"]["path"] + "::" + item["source"]["symbol"]
        if symbol not in index.get("symbols", {}):
            raise ValueError(
                "automatic instrumentation source is absent from independent inventory"
            )
        sites.extend(
            {
                "symbol": symbol,
                "node": item["node"],
                "phase": phase,
                "instrumentation": "opentelemetry",
            }
            for phase in ("enter", "return", "error")
        )
    return sites


def runtime_errors(configuration, payload):
    """Selected tracing must actually run; configuration alone is not evidence."""
    if configuration is None:
        return []
    errors = []
    registered = {item["node"] for item in configuration["registrations"]}
    for run in payload.get("runs", []):
        if run.get("mode") != "on":
            continue
        if (run.get("probe_health") or {}).get("tracing", {}).get("backend") != "opentelemetry":
            errors.append({"case": run.get("case"), "missing_tracing_backend": True})
        for event in run.get("events", []):
            if (
                event.get("lifecycle") == "span" or event.get("node") in registered
            ) and not event.get("trace"):
                errors.append({"event": event.get("id"), "missing_trace_identity": True})
    return errors


def match_registration(items, name, attributes):
    matches = [
        item
        for item in items
        if ("name" not in item["match"] or item["match"]["name"] == name)
        and all(attributes.get(k) == v for k, v in item["match"].get("attributes", {}).items())
    ]
    if len(matches) > 1:
        raise ValueError("ambiguous automatic span registration")
    return matches[0] if matches else None


def business_layer_errors(model):
    """Catch generic transport wrappers mislabeled as user-facing business actions."""
    technical = {"http request", "web request", "网页请求", "网络请求", "http请求"}
    return [
        f"{node['id']}: generic request boundary belongs to API/execution, not business"
        for node in model.get("nodes", [])
        if (node.get("layer") == "business" or "business" in node.get("semantic_roles", []))
        and str(node.get("label", "")).strip().lower() in technical
    ]
