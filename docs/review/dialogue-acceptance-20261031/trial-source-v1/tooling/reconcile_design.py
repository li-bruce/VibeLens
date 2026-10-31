"""Reconcile recorded trial replies without implementing application behavior."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "discovery.json"
REVIEW = ROOT / "review"


def source(identifier, text, locator, kind="user"):
    return {"id": identifier, "kind": kind, "text": text, "locator": locator}


def main():
    doc = json.loads(DESIGN.read_text(encoding="utf-8-sig"))
    if any(item["id"] == "U005" for item in doc["sources"]):
        raise RuntimeError("This reconciliation has already been applied.")
    (REVIEW / "discovery-round-2.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    doc["sources"].extend([
        source("U003", "【模拟用户回答】\n待审核的共享也可以由文件主人取消；已通过的共享可以撤销。撤销后立即失去下载权限，即使接收方没刷新页面、还拿着旧下载地址，再次请求下载也要拒绝。已经下载到本地的文件不追回。\n采用 SQLite + SQLAlchemy，文件放在本项目自己的数据目录。", "Simulated user answer supplied by test coordinator; review/design-dialogue.md#u003"),
        source("U004", "谁负责审核共享申请：文件主人指定审核人。\n审核通过、驳回的结果和共享消息分别通知谁：相关的所有人。\nVibeLens 运行模式：drive：声明驱动。\n能否取消待审核共享、未刷新页面再次下载是否立即拒绝：可以，是的。\n存储选择：采用 SQLite + SQLAlchemy。", "Actual in-conversation question-tool reply; trial evidence, no independent human-acceptance claim; review/design-dialogue.md#u004"),
        source("A006", "“相关的所有人”是否指文件主人、指定审核人、接收成员三方，都收到通过／驳回结果和通过后的共享通知？接收方的文件列表仍只显示已获授权的文件。", "Actual assistant clarification; review/design-dialogue.md#a006", "assistant"),
        source("U005", "是，三方都通知，列表规则不变", "Actual in-conversation question-tool reply to A006; trial evidence; review/design-dialogue.md#u005"),
    ])
    resolutions = {
        "D_REVIEWER": ("The owner selects the reviewer when requesting sharing with a specified recipient. This supersedes the earlier fixed-administrator trial answer.", ["U004"]),
        "D_NOTIFICATIONS": ("The owner, selected reviewer, and recipient all receive approval/rejection results and sharing notifications after approval. The recipient file list includes only currently authorized files; pending and rejected requests remain absent.", ["U004", "U005"]),
        "D_MODE": ("drive: the confirmed state declaration drives business transitions.", ["U002", "U004"]),
        "D_REVOCATION": ("The owner can cancel pending requests and revoke approved shares. Revocation immediately denies every new download request, including requests from an unchanged page or an old URL. Already downloaded local copies are not recovered.", ["U003", "U004"]),
        "D_STORAGE": ("Use SQLite with SQLAlchemy and store file content inside this project's own data directory.", ["U003", "U004"]),
    }
    changes = doc.setdefault("changes", [])
    for decision in doc["decisions"]:
        text, refs = resolutions[decision["id"]]
        previous = deepcopy(decision)
        decision["status"] = "resolved"
        decision["resolution"] = {"kind": "user_answer", "text": text, "source_refs": refs}
        if previous.get("status") == "resolved" and previous.get("resolution") != decision["resolution"]:
            changes.append({"id": "C_" + decision["id"] + "_LATEST_REPLY", "decision": decision["id"], "previous": previous, "source_refs": refs, "reason": "Use the later in-conversation answer and retain the earlier resolved decision in full."})

    network = doc["networks"][0]
    network["actors"] = ["文件主人", "主人指定的审核人", "接收成员"]
    network["outcome"] = "Review controls recipient access; all three parties receive results. The owner can cancel pending requests or revoke approved access."
    for node in network["nodes"]:
        updates = {
            "review": ("主人指定的审核人审核", ["U004"]),
            "notification": ("审核结果通知三方", ["U004", "U005"]),
            "share_message": ("通过后共享消息通知三方", ["U005"]),
            "share": ("主人选择接收方及审核人", ["U004"]),
            "revoked": ("已撤销：旧地址新请求也拒绝", ["U003", "U004"]),
            "download": ("每次请求检查当前下载权限", ["U003", "U004"]),
            "received_files": ("接收方仅查看获授权文件", ["U002", "U005"]),
        }
        if node["id"] in updates:
            node["label"], refs = updates[node["id"]]
            node["source_refs"] = list(dict.fromkeys(node["source_refs"] + refs))
    network["nodes"].extend([
        {"id": "cancel_share", "kind": "action", "label": "主人取消待审核申请", "source_refs": ["U003", "U004"]},
        {"id": "cancelled", "kind": "state", "label": "已取消：不授予权限", "source_refs": ["U003", "U004"]},
        {"id": "download_denied", "kind": "effect", "label": "拒绝新的下载请求", "source_refs": ["U003", "U004"]},
    ])
    for edge in network["edges"]:
        if edge["id"] == "flow_pending_review":
            edge["label"] = "所选审核人处理"
            edge["source_refs"] = ["U004"]
        if edge["id"] == "flow_revoke_revoked":
            edge["label"] = "立即失去下载权限"
            edge["source_refs"] = ["U003", "U004"]
    network["edges"].extend([
        {"id": "flow_pending_cancel", "from": "pending", "to": "cancel_share", "relation": "cancel", "label": "主人可取消", "source_refs": ["U003", "U004"]},
        {"id": "flow_cancel_cancelled", "from": "cancel_share", "to": "cancelled", "relation": "flow", "label": "结束待审核申请", "source_refs": ["U003", "U004"]},
        {"id": "flow_revoked_denied", "from": "revoked", "to": "download_denied", "relation": "guard", "label": "再次请求下载", "source_refs": ["U003", "U004"]},
    ])

    policy = doc["policy"]
    policy["revision"] = "draft-3"
    policy["inputs"].pop("reviewer_is_admin")
    policy["inputs"].update({"actor_is_selected_reviewer": "boolean", "share_is_pending": "boolean", "share_is_approved": "boolean"})
    policy["nodes"] = [node for node in policy["nodes"] if node["id"] not in {"admin_fact", "admin_rule", "reviewer_session"}]
    for identifier, name, label, refs in [
        ("selected_reviewer", "actor_is_selected_reviewer", "操作者是所选审核人", ["U004"]),
        ("pending", "share_is_pending", "申请仍在待审核", ["U003", "U004"]),
        ("approved", "share_is_approved", "共享处于已通过", ["U003", "U004"]),
    ]:
        policy["nodes"].extend([
            {"id": identifier + "_fact", "op": "input", "name": name, "label": label, "source_refs": refs},
            {"id": identifier + "_rule", "op": "predicate", "predicate": "flag_enabled", "arguments": {"value": identifier + "_fact"}, "label": label, "source_refs": refs},
        ])
    for identifier, inputs, label, refs in [
        ("reviewer_pending", ["signed_in_rule", "selected_reviewer_rule", "pending_rule"], "所选审核人处理待审核申请", ["U004"]),
        ("owner_pending", ["owner_session", "pending_rule"], "主人取消待审核申请", ["U003", "U004"]),
        ("owner_approved", ["owner_session", "approved_rule"], "主人撤销已通过共享", ["U003", "U004"]),
    ]:
        policy["nodes"].append({"id": identifier, "op": "all", "inputs": inputs, "label": label, "source_refs": refs})
    for operation in policy["operations"]:
        if operation["id"] == "review":
            operation.update(root="reviewer_pending", cases=["selected_reviewer_approves", "selected_reviewer_rejects", "unselected_reviewer_denied", "cancelled_request_review_denied"], source_refs=["U004"])
        if operation["id"] == "revoke":
            operation.update(root="owner_approved", source_refs=["U003", "U004"])
        if operation["id"] == "download":
            operation["cases"].extend(["revoked_old_url_denied", "revoked_stale_page_denied"])
            operation["source_refs"] = ["U001", "U003", "U004"]
        if operation["id"] == "received_files":
            operation["cases"].extend(["cancelled_file_hidden", "revoked_file_hidden"])
    policy["operations"].append({"id": "cancel_share", "root": "owner_pending", "business_nodes": ["cancel_share"], "cases": ["owner_cancels_pending", "nonowner_cancel_denied"], "source_refs": ["U003", "U004"]})
    doc["decisions"].append({"id": "D_GRAPH_CONFIRM", "topic": "scope", "blocking": True, "status": "open", "priority": 1, "source_refs": ["U001", "P001"], "affects": [node["id"] for node in network["nodes"]], "question": "请确认更新后的业务网是否正确；确认后才开始开发。", "why": "The user explicitly requires graph confirmation before behavior implementation."})
    DESIGN.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (REVIEW / "policy-draft.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
