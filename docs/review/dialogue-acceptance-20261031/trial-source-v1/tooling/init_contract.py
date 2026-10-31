"""Freeze confirmed trial intent and independent expectations before coding."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(name, value):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    doc = json.loads((ROOT / "discovery.json").read_text(encoding="utf-8-sig"))
    answer = "【模拟用户确认】\n我打开当前业务图看过了，按最新的这一版继续：主人指定审核人，审核结果通知三方，通过后接收方才出现在文件列表里并能下载；待审核能取消，通过后能撤销，撤销后旧地址也不能再下载。这张业务网符合当前意图，可以开始开发。\n登录先用本地预置测试账号即可，暂时不做注册。请把确认后的简图也保留在对话里，方便回顾。"
    doc["sources"].append({"id":"U006","kind":"user","text":answer,"locator":"Simulated user graph confirmation supplied by coordinator in this conversation; review/design-dialogue.md#u006"})
    decision = next(item for item in doc["decisions"] if item["id"] == "D_GRAPH_CONFIRM")
    decision.update(status="resolved", resolution={"kind":"user_answer","text":"The current graph is confirmed for this independent trial. Start implementation using owner-selected reviewers, three-party results, and seeded local accounts without registration.","source_refs":["U006"]})
    save("discovery.json", doc)
    requirements = [
        ("R_LOGIN", "Seeded local accounts can log in and log out; no registration. Passwords are not captured."),
        ("R_UPLOAD", "An authenticated member uploads a private file owned by that member."),
        ("R_SHARE", "The file owner selects another existing member as recipient and an existing member as reviewer, creating a pending share."),
        ("R_REVIEW", "Only the selected reviewer may approve or reject a pending share. Approval grants recipient access; rejection does not."),
        ("R_MESSAGES", "Review results go to owner, selected reviewer, and recipient. Approval also sends a separate sharing message to all three. Users read only their own notifications."),
        ("R_DOWNLOAD", "Recipients see and download only currently approved shares. Pending, rejected, cancelled, and revoked shares confer no access. Every new download checks current authority."),
        ("R_CANCEL", "Only the owner can cancel a pending share. A cancelled request cannot subsequently be approved."),
        ("R_REVOKE", "Only the owner can revoke an approved share; new downloads using old URLs or unchanged pages are denied immediately. Local downloaded copies are not recovered."),
        ("R_STORAGE", "SQLite with SQLAlchemy persists records; file content remains inside the trial data directory. State and resulting messages commit together."),
        ("R_GRAPH", "Drive mode executes the confirmed declaration; maintain public graph, source mappings, database observations, real lifecycles and evidence independently of business authority."),
    ]
    save("intent.json", {"intent_id":"team-file-sharing-lifecycle","project_id":"team-file-sharing-lifecycle","revision":"1","goal":"Share team files through selected review, notifications and revocable download access.","requirements":[{"id":key,"text":text,"status":"confirmed","source":"review/design-dialogue.md U001-U006; trial answers, not production acceptance"} for key,text in requirements],"exclusions":["Public links","Registration","Cloud publication","Recovering downloaded copies","Production or arbitrary-schedule acceptance claims"]})
    expected = {
        "approved": {"state":"approved", "download_allowed":True, "recipient_visible":True, "review_results":3, "share_messages":3},
        "rejected": {"state":"rejected", "download_allowed":False, "recipient_visible":False, "review_results":3, "share_messages":0},
        "cancelled": {"state":"cancelled", "download_allowed":False, "recipient_visible":False, "review_results":0, "share_messages":0},
        "revoked": {"state":"revoked", "download_allowed":False, "recipient_visible":False, "review_results":3, "share_messages":3},
        "pending": {"state":"pending", "download_allowed":False, "recipient_visible":False, "review_results":0, "share_messages":0},
    }
    checks=[]
    for case, fields in expected.items():
        for field, value in fields.items():
            requirement = "R_MESSAGES" if field in {"review_results","share_messages"} else "R_DOWNLOAD" if field in {"download_allowed","recipient_visible"} else "R_REVIEW" if case in {"approved","rejected","pending"} else "R_CANCEL" if case == "cancelled" else "R_REVOKE"
            checks.append({"id":case+"-"+field,"requirement":requirement,"case":case,"path":[field],"equals":value})
    checks += [{"id":"unauthorized-no-state-change","requirement":"R_REVIEW","case":"unauthorized","path":["state"],"equals":"pending"},{"id":"unauthorized-no-message","requirement":"R_MESSAGES","case":"unauthorized","path":["review_results"],"equals":0}]
    save("acceptance.json", {"checks":checks,"model_checks":[]})
    cases=list(expected)+["unauthorized"]
    fields=[{"id":"state","node":"pending","actual":["state"],"mapped":["state"]},{"id":"revision","node":"pending","actual":["revision"],"mapped":["revision"]},{"id":"build","node":"pending","actual":["build_id"],"mapped":["build_id"]}]
    for field in ["file_id","owner_id","recipient_id","reviewer_id"]:
        fields.append({"id":field,"node":"share","actual":["context",field],"mapped":["context",field]})
    save("mapping.json", {"schema":"bo-mapping/v1","cases":cases,"modes":["on","off","fault"],"source":"Independent SQLite reads through app/storage.py::Store.snapshot","actual_collection":["authority_snapshot","instances"],"actual_id":["instance_id"],"fields":fields,"export":{"case":"approved","mode":"on"}})
    save("whitebox.json", {"schema_version":1,"rules":[],"checks":[]})
    baseline={"schema_version":3,"revision":"design-baseline","intent":"intent.json","source_files":["tooling/run_design.py"],"nodes":[{"id":"design_baseline","kind":"data","label":"Confirmed design baseline","capture":{}}],"edges":[],"overview":[],"scope":{"observable":["Confirmed design before behavior implementation"],"unknowns":["Business code has not been implemented"]},"machine":{}}
    save("behavior.json", baseline)
    save("sync.json", {"model":"behavior.json","manifest":"manifest.json","code_files":["tooling/run_design.py"],"watch_files":["intent.json","implementation.json"],"source_scope":{"roots":["."],"require_symbol_classification":True,"exclude":{".agents/**":"Project-local Skill checked through canonical tool fingerprints.",".trial/**":"Frozen Skill provenance.","observer_runtime/**":"Canonical runtime copy verified by upgrade hashes.","review/**":"Review evidence and finite test artifacts, not business code.","tooling/**":"Developer launch/build/check utilities, tracked explicitly.","bo_stategraph/__init__.py":"Canonical independent public query core.","bo_stategraph/bo_contracts.py":"Canonical declaration validation.","bo_stategraph/execution_contract.py":"Canonical activity validation.","bo_stategraph/native_executor.py":"Canonical flat native executor; parity checked.","bo_stategraph/native_policy/**":"Canonical pure native policy executor; parity checked.","data/**":"Application database and uploaded file content.","tests/**":"Independent tests, executed through test_commands."}},"stategraph":{"module":"bo_stategraph/__init__.py","development_mode":"drive","execution_mode":"drive","decision_source":"user","decision":"drive：声明驱动"},"require_mapping_witnesses":True,"mapping_contract":"mapping.json","acceptance":"acceptance.json","whitebox":"whitebox.json","discovery":"discovery.json","slice_depth":1,"probe_modes":["on","off","fault"],"probe_callees":["record","span"],"required_probes":[{"symbol":"app/service.py::Service.download","node":"download","phase":"return"}],"required_runtime_probes":[{"case":"approved","node":"download","phase":"return"}],"observations_command":["{python}","-B","-X","utf8","tooling/observe.py"],"test_commands":[["{python}","-B","-X","utf8","-m","unittest","discover","-s","tests","-v"]],"timeout_seconds":180})
    save("implementation.json", {"schema":"bo-implementation/v1","features":[],"support":{},"excluded":{}})
    with (ROOT / "review/design-dialogue.md").open("a",encoding="utf-8") as stream:
        stream.write("\n\n## U006\n\nProvenance: simulated user graph confirmation supplied by the coordinator. This authorizes implementation in the trial; it is not human or production acceptance.\n\n> " + answer.replace("\n","\n> ") + "\n")


if __name__ == "__main__":
    main()
