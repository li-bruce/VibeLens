"""Export a named trial's visible dialogue and token counters for review.

Only public messages, explicitly delivered trial prompts and usage metadata are
selected. Reasoning, system/developer instructions and arbitrary tool output are
never copied. Run this explicitly against the requested local session file.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


def public_record(record):
    """Select externally visible dialogue without collecting internal context."""
    if record.get("type") != "response_item":
        return None
    item = record.get("payload", {})
    kind, role = item.get("type"), item.get("role")
    if kind == "function_call_output" and item.get("name") in {
        "create_thread",
        "send_message_to_thread",
    }:
        prompt = re.search(r"<input>(.*?)</input>", str(item.get("output", "")), re.S)
        if prompt:
            return {"role": "scripted-user", "text": prompt.group(1)}
    if kind == "function_call" and item.get("name") in {
        "request_user_input",
        "request_user_input_async",
    }:
        return {"role": "assistant-question", "text": item.get("arguments", "")}
    if kind != "message" or role not in {"user", "assistant"}:
        return None
    if role == "assistant" and item.get("phase") not in {"commentary", "final_answer"}:
        return None
    text = "\n".join(
        part.get("text", "")
        for part in item.get("content", [])
        if part.get("type") in {"input_text", "output_text", "text"}
    )
    if not text.strip() or text.lstrip().startswith("<environment_context>"):
        return None
    return {"role": role, "text": text, "phase": item.get("phase")}


def readable_text(text):
    """Keep captured local paths readable without making dead repository links."""
    return re.sub(
        r"!?\[([^\]]*)\]\((<?(?:WORKSPACE[/\\]|[A-Za-z]:[/\\])[^)\n]*>?)\)",
        lambda match: match[1] + " (`" + match[2].strip("<>") + "`)",
        text,
    )


def export(sessions, destination, title, replacements=()):
    """Keep original ordering and provenance; normalize only declared local paths."""
    records, counters, settings, origins = [], [], [], []
    for path in sessions:
        turn_id = None
        data = path.read_bytes()
        origins.append({"file": path.name, "sha256": sha256(data).hexdigest()})
        for line in data.decode("utf-8").splitlines():
            record = json.loads(line)
            visible = public_record(record)
            if visible:
                for original, replacement in replacements:
                    visible["text"] = visible["text"].replace(original, replacement)
                records.append({"timestamp": record.get("timestamp"), **visible})
            payload = record.get("payload", {})
            if record.get("type") == "turn_context":
                turn_id = payload.get("turn_id") or payload.get("id")
                value = {k: payload[k] for k in ("model", "effort") if k in payload}
                if value and value not in settings:
                    settings.append(value)
            if record.get("type") == "event_msg" and payload.get("type") == "token_count":
                info = payload.get("info") or {}
                if info.get("total_token_usage"):
                    counters.append(
                        {
                            "timestamp": record.get("timestamp"),
                            "turn_id": turn_id,
                            "usage": info["total_token_usage"],
                        }
                    )
    destination.mkdir(parents=True, exist_ok=True)
    report = {
        "title": title,
        "source_sessions": origins,
        "settings": settings,
        "path_normalization": list(replacements),
        "dialogue": records,
        "counters": counters,
        "provenance": "Trial prompts and follow-ups delivered by the coordinating AI are scripted-user records. They are not independent human usability evidence.",
    }
    (destination / "dialogue.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# " + title,
        "",
        report["provenance"],
        "",
        "Local paths are normalized as listed in dialogue.json. Original trial answers and checks are archived separately.",
        "",
    ]
    for index, item in enumerate(records, 1):
        lines += [
            f"## {index:02d} · {item['role']} · {item['timestamp']}",
            "",
            readable_text(item["text"]),
            "",
        ]
    (destination / "dialogue.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return {
        "messages": len(records),
        "usage_samples": len(counters),
        "settings": settings,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--workspace", help="Local workspace path to replace with WORKSPACE")
    args = parser.parse_args()
    replacements = []
    if args.workspace:
        replacements = [
            (args.workspace.replace("\\", "/"), "WORKSPACE"),
            (args.workspace.replace("/", "\\"), "WORKSPACE"),
        ]
    print(json.dumps(export(args.session, args.out, args.title, replacements), ensure_ascii=False))
