"""Parse pinned TLC tool messages and its deliberately small typed value grammar.

Success needs a completed nonempty exhaustive run. A process exit code alone,
truncated log or an arbitrary JSON status is never accepted as model evidence.
"""

import re
from copy import deepcopy

MESSAGE = re.compile(r"@!@!@STARTMSG (\d+):(\d+) @!@!@\s*\n(.*?)@!@!@ENDMSG \1 @!@!@", re.S)
TOKEN = re.compile(r'\s*(<<|>>|[{},]|TRUE\b|FALSE\b|-?\d+|"[sn][0-9a-f]*")')


def value(text):
    """Decode only values emitted by our exporter; reject unconsumed or unknown syntax."""
    tokens = []
    position = 0
    while position < len(text.strip()):
        match = TOKEN.match(text, position)
        if not match:
            raise ValueError("Unsupported TLC value: " + text[:100])
        tokens.append(match.group(1))
        position = match.end()

    def parse(index):
        token = tokens[index]
        index += 1
        if token in {"{", "<<"}:
            end = "}" if token == "{" else ">>"
            items = []
            while tokens[index] != end:
                item, index = parse(index)
                items.append(item)
                if tokens[index] == ",":
                    index += 1
                elif tokens[index] != end:
                    raise ValueError("Malformed TLC collection")
            return items, index + 1
        if token in {"TRUE", "FALSE"}:
            return token == "TRUE", index
        if token.startswith('"s'):
            return bytes.fromhex(token[2:-1]).decode("utf-8"), index
        if token == '"n"':
            return None, index
        return int(token), index

    try:
        result, end = parse(0)
    except (IndexError, UnicodeError) as error:
        raise ValueError("Malformed TLC value") from error
    if end != len(tokens):
        raise ValueError("Trailing TLC value tokens")
    return result


def parse_output(stdout, exit_code, source_map, *, stop_reason=None):
    """Classify actual tool output; retain tool messages for auditable diagnostics."""
    messages = [
        {"code": int(code), "severity": int(level), "text": body.strip()}
        for code, level, body in MESSAGE.findall(stdout)
    ]
    codes = {m["code"] for m in messages}
    result = {
        "status": "error",
        "reason": "tool_error",
        "completed": 2186 in codes,
        "exit_code": exit_code,
        "messages": messages,
        "trace": None,
        "stats": None,
    }
    stats = next((m["text"] for m in reversed(messages) if m["code"] == 2199), "")
    counts = re.search(
        r"([\d,]+) states generated, ([\d,]+) distinct states found, ([\d,]+) states left", stats
    )
    if counts:
        result["stats"] = dict(
            zip(
                ("generated", "distinct", "queued"),
                (int(v.replace(",", "")) for v in counts.groups()),
            )
        )
    if stop_reason:
        return {**result, "status": "incomplete", "reason": stop_reason, "completed": False}
    if stdout.count("@!@!@STARTMSG") != len(messages) or stdout.count("@!@!@ENDMSG") != len(
        messages
    ):
        return {**result, "reason": "truncated_tool_messages", "completed": False}
    failure = {2107, 2110, 2114, 2116} & codes
    if failure:
        result.update(status="fail", reason="deadlock" if 2114 in codes else "property_violation")
        for message in messages:
            if message["code"] in {2107, 2110}:
                checks = [
                    v
                    for v in source_map["variables"].values()
                    if re.search(r"\b" + re.escape(v["type_check"]) + r"\b", message["text"])
                ]
                if checks and any(
                    v["bound_origin"] in {"analysis_bound", "abstraction"} for v in checks
                ):
                    result.update(status="incomplete", reason="analysis_domain_exceeded")
                elif checks:
                    result["reason"] = "application_domain_violation"
        try:
            result["trace"] = logical_trace(messages, source_map)
        except (ValueError, KeyError, TypeError) as error:
            result.update(status="error", reason="trace_parse_error", trace_error=str(error))
        if not result["completed"]:
            result.update(status="incomplete", reason="unfinished_counterexample")
        return result
    if exit_code == 0 and 2193 in codes and result["completed"] and result["stats"]:
        if result["stats"]["distinct"] < 1:
            return {**result, "status": "error", "reason": "empty_initial"}
        if result["stats"]["queued"] == 0 and not any(m["severity"] == 1 for m in messages):
            result.update(status="pass", reason="exhaustive_selected_design")
    return result


def logical_trace(messages, source_map):
    """Keep initial state, original action IDs, exact parameters and explicit loop closure."""
    states = []
    steps = []
    loop = None
    for message in messages:
        code = message["code"]
        body = message["text"]
        # An initial invariant violation embeds the complete state in the error
        # message itself, rather than emitting a separate STATE_PRINT message.
        if code in {2107, 2216, 2217}:
            assignments = re.findall(r"(?:^|\n)/\\ (\w+) = (.*?)(?=\n/\\ |\Z)", body, re.S)
            parsed = {key: value(text.strip()) for key, text in assignments}
            required = set(source_map["variables"]) | {"VLCheck", "VLStep"}
            if set(parsed) != required:
                raise ValueError("Incomplete model state")
            if states:
                action = source_map["actions"].get(str(parsed["VLStep"]))
                if not action:
                    raise ValueError("Unknown model action")
                steps.append(
                    {"action": action["action"], "parameters": deepcopy(action["parameters"])}
                )
            states.append(
                {v["id"]: parsed[symbol] for symbol, v in source_map["variables"].items()}
            )
        elif code in {2218, 2122}:
            if not states:
                raise ValueError("Loop without states")
            if code == 2218:
                loop = len(states) - 1
                steps.append({"action": None, "parameters": {}})
            else:
                number = re.search(r"(?:Back to state\s+)?(\d+)", body)
                if not number:
                    raise ValueError("Loop has no target")
                loop = int(number.group(1)) - 1
                if not 0 <= loop < len(states):
                    raise ValueError("Unknown loop target")
                operator = re.search(r"<(A\d+)\b", body)
                action = next(
                    (
                        a
                        for a in source_map["actions"].values()
                        if operator and a["operator"] == operator.group(1)
                    ),
                    None,
                )
                if not action:
                    raise ValueError("Loop has no original action")
                steps.append(
                    {"action": action["action"], "parameters": deepcopy(action["parameters"])}
                )
            states.append(deepcopy(states[loop]))
    if not states:
        raise ValueError("Failure has no counterexample states")
    return {
        "schema": "bo-analysis-trace/v1",
        "origin": "model_analysis",
        "subject": "design_model",
        "analysis_id": source_map.get("analysis_id", "tlc"),
        "definition_sha256": source_map["definition_sha256"],
        "property_refs": [source_map["property"]],
        "states": states,
        "steps": steps,
        "loop_back": loop,
    }
