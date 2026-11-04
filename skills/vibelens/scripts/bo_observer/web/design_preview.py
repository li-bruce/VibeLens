"""Compact, localized conversation diagrams without changing concept identities.

The focus artifact retains original relation identities, including source
assertions represented by one display edge. This renderer reuses one external
glyph per node ID. Captions never establish identity or merge relations.
"""

import html

from ..concepts.registry import RELATION_LABELS
from .interface_language import LOCALES


RELATIONS_ZH = {
    "contains": "包含",
    "describes_fact": "说明",
    "state_subject": "所属对象",
    "declares_event": "事件",
    "declares_guard": "条件",
    "declares_effect": "效果",
    "requests_transition": "触发",
    "guarded_by": "条件成立",
    "has_effect": "执行",
    "declares_target": "进入",
    "guard": "条件成立",
    "data": "输入",
    "decision_result": "结果",
    "guard_resolves_decision": "判断",
    "action_requests_event": "触发",
    "transition_guarded_by": "条件成立",
    "decision_reads_fact": "读取",
    "transition_has_effect": "执行",
    "reads_state": "读取状态",
    "changes_state": "改变状态",
    "requires_decision": "依据判断",
    "resource": "使用名额",
    "join": "汇合",
    "enables_event": "允许触发",
    "flow": "接着",
    "condition": "条件",
    "depends": "依赖",
    "reads": "读取",
    "writes": "写入",
    "event": "事件",
    "retry": "重试",
    "cancel": "取消",
}


def _escape(value):
    """Keep authored captions on one safe Mermaid line."""
    return html.escape(str(value), quote=True).replace("\n", " ").replace("`", "&#96;")


def _relation_label(edge, locale):
    """Translate generated vocabulary while preserving authored relation meaning."""
    kind = edge["type"]
    label = edge.get("label", kind)
    defaults = {kind, kind.replace("_", " ").capitalize(), RELATION_LABELS.get(kind)}
    if kind in {"guarded_by", "transition_guarded_by"}:
        defaults.update({"Requires true", "Requires false"})
    if label in defaults:
        if edge.get("negated") and kind in {"guarded_by", "transition_guarded_by"}:
            return "条件不成立" if locale == "zh-CN" else "Unless"
        return RELATIONS_ZH.get(kind, label) if locale == "zh-CN" else label
    return label


def diagram(view, locale):
    """Render a focus without duplicating external objects or rewriting evidence."""
    if locale not in LOCALES:
        raise ValueError("Preview language must be en or zh-CN")
    aliases = {node["id"]: "n" + str(index) for index, node in enumerate(view["nodes"])}
    lines = ["flowchart LR"]
    for node in view["nodes"]:
        operator = " · " + node["operator"] if node.get("operator") else ""
        lines.append(f'  {aliases[node["id"]]}["{_escape(node["label"] + operator)}"]')
    for edge in view["edges"]:
        lines.append(
            f'  {aliases[edge["from"]]} -->|"{_escape(_relation_label(edge, locale))}"| '
            f'{aliases[edge["to"]]}'
        )

    external = {}
    for boundary in view["boundaries"]:
        for node in boundary["outside"]:
            if node["id"] not in external:
                alias = "b" + str(len(external))
                external[node["id"]] = alias
                suffix = "关联" if locale == "zh-CN" else "related"
                lines.append(f'  {alias}["{_escape(node["label"])} · {suffix}"]')
        if boundary["outside"]:
            endpoints = {**aliases, **external}
            edge = boundary["relation"]
            lines.append(
                f'  {endpoints[boundary["from"]]} -.->|"'
                f'{_escape(_relation_label(edge, locale))}"| {endpoints[boundary["to"]]}'
            )
    return "\n".join(lines)


def markdown(view, document, url, concern, locale):
    """Keep the conversation preview limited to the diagram and actual questions."""
    titles = {
        "business": ("Business network", "业务网"),
        "state": ("State model", "状态网"),
        "rules": ("Rule network", "规则网"),
        "all": ("Concept models", "业务、状态与规则"),
    }
    chinese = locale == "zh-CN"
    title = titles[concern][int(chinese)]
    text = f"# {title}\n\n```mermaid\n{diagram(view, locale)}\n```\n\n"
    link = "打开动态图" if chinese else "Open the live graph"
    text += f"[{link}]({url})\n\n"
    if view["coverage"]["crossing_or_omitted_edges"]:
        text += (
            "虚线连接当前范围外的关联内容，完整关系可在网页中查看。\n\n"
            if chinese
            else "Dashed links continue into related content outside this view. Open Web for the complete graph.\n\n"
        )
    pending = [item for item in document["decisions"] if item["status"] != "resolved"]
    if pending:
        text += "待确认：\n\n" if chinese else "Still to confirm:\n\n"
        text += "\n".join("- " + item["question"].replace("\n", " ") for item in pending) + "\n\n"
    text += (
        "请在对话中确认这份理解，或说明需要调整的地方。\n"
        if chinese
        else "Confirm this understanding in the conversation, or describe a correction.\n"
    )
    return text
