"""Generate the unified graph from confirmed design, native source and database metadata."""

from copy import deepcopy
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]

from bo_observer.graph.code_structure import scan,enrich
from bo_observer.policy.projection import project as project_policy
from bo_observer.data.catalog import export_sqlalchemy_metadata
from bo_observer.data.sync import synchronize
from bo_observer.graph.behavior_model import capture
from app.models import metadata
from app.storage import Store


def save(name,value):
    path=ROOT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    discovery=json.loads((ROOT/"discovery.json").read_text(encoding="utf-8-sig"))
    sync=json.loads((ROOT/"sync.json").read_text(encoding="utf-8-sig"))
    definitions={
        "login":("app/service.py","Service.login",{"username":"string","password_supplied":"boolean"},{"allowed":"boolean","user_id":"string","error":"string"},"R_LOGIN"),
        "logout":("app/service.py","Service.logout",{"actor_id":"string"},{"logged_out":"boolean"},"R_LOGIN"),
        "upload":("app/service.py","Service.upload",{"actor_id":"string","filename":"string","size":"number"},{"file_id":"string","saved":"boolean","size":"number"},"R_UPLOAD"),
        "share":("app/service.py","Service.request_share",{"actor_id":"string","file_id":"string","recipient_id":"string","reviewer_id":"string"},{"share_id":"string","state":"string","revision":"number"},"R_SHARE"),
        "review":("app/service.py","Service.change_share",{"actor_id":"string","share_id":"string","event":"string"},{"state":"string","revision":"number","changed":"boolean"},"R_REVIEW"),
        "cancel_share":("app/service.py","Service.change_share",{"actor_id":"string","share_id":"string","event":"string"},{"state":"string","revision":"number","changed":"boolean"},"R_CANCEL"),
        "revoke":("app/service.py","Service.change_share",{"actor_id":"string","share_id":"string","event":"string"},{"state":"string","revision":"number","changed":"boolean"},"R_REVOKE"),
        "download":("app/service.py","Service.download",{"actor_id":"string","file_id":"string"},{"allowed":"boolean","size":"number","file_id":"string"},"R_DOWNLOAD"),
        "received_files":("app/service.py","Service.dashboard",{"actor_id":"string"},{"owned_count":"number","received_count":"number","review_count":"number","message_count":"number"},"R_DOWNLOAD"),
        "read_notification":("app/service.py","Service.read_notification",{"actor_id":"string","notification_id":"string"},{"is_read":"boolean"},"R_MESSAGES"),
        "notification":("app/service.py","Service._messages",{"share_id":"string","kind":"string","recipients":["string"]},{"count":"number","state":"string"},"R_MESSAGES"),
        "share_message":("app/service.py","Service._messages",{"share_id":"string","kind":"string","recipients":["string"]},{"count":"number","state":"string"},"R_MESSAGES"),
        "http_action":("app/web.py","create_app.page",{"action":"string"},{"status":"number"},"R_LOGIN"),
        "http_page":("app/web.py","create_app.page",{"actor_id":"string"},{"status":"number"},"R_LOGIN"),
        "http_download":("app/web.py","create_app.download",{"file_id":"string"},{"status":"number"},"R_DOWNLOAD"),
    }
    state_ids={"pending":"pending","approved":"granted","rejected":"rejected","cancelled":"cancelled","revoked":"revoked"}
    labels={node["id"]:node["label"] for network in discovery["networks"] for node in network["nodes"]}
    labels.update(logout="Sign out",read_notification="Read notification",http_action="Submit form",http_page="Open workspace",http_download="Download response")
    summaries={"login":"Verify seeded account credentials without collecting the password.","logout":"End the current local user session.","upload":"Store a private file and its owner after checking the current session.","share":"Create a pending request for the owner's selected recipient and reviewer.","review":"The selected reviewer approves or rejects a pending request within one transaction.","cancel_share":"The owner cancels a request that is still pending.","revoke":"The owner removes an approved sharing grant.","download":"Read current authority for every new request before returning file bytes.","received_files":"Return the member's authorized files and private workspace records.","read_notification":"Mark a notification read only for its recipient.","notification":"Insert review-result records for all three involved members in the state transaction.","share_message":"Insert a separate sharing message for all three parties after approval.","http_action":"Dispatch a CSRF-protected submitted form to its business operation.","http_page":"Render the authenticated member's current workspace.","http_download":"Return an attachment or the current authorization rejection over HTTP."}
    nodes=[]
    for identifier,(path,symbol,inputs,outputs,requirement) in definitions.items():
        node={"id":identifier,"kind":"action","layer":"business","label":labels[identifier],"summary":summaries[identifier],"source":{"path":path,"symbol":symbol},"capture":{"in":inputs,"out":outputs},"requirements":[requirement]}
        states=[{"id":"running","label":"Running","kind":"active"},{"id":"returned","label":"Returned","kind":"ended"}]
        bindings=[{"phase":"enter","boundary":"start","state":"running"},{"phase":"return","boundary":"end","state":"returned"}]
        if identifier in {"share","review","cancel_share","revoke"}:
            bindings=bindings[:1]
            for value in ["pending","approved","rejected","cancelled","revoked"]:
                states.append({"id":value,"label":value.title(),"kind":"ended"})
                bindings.append({"phase":"return","boundary":"end","state":value,"when":{"direction":"out","field":"state","equals":value}})
        if identifier=="login":
            states.extend([{"id":"allowed","label":"Signed in","kind":"ended"},{"id":"denied","label":"Credentials rejected","kind":"ended"}])
            bindings=[bindings[0],{"phase":"return","boundary":"end","state":"allowed","when":{"direction":"out","field":"allowed","equals":True}},{"phase":"error","boundary":"end","state":"denied","when":{"direction":"out","field":"error","equals":"BusinessError"}}]
        node["lifecycle"]={"states":states,"bindings":bindings}
        nodes.append(node)
    for value,identifier in state_ids.items():
        nodes.append({"id":identifier,"kind":"state","layer":"state","value":value,"label":labels[identifier],"summary":"Persisted sharing state: "+value+".","capture":{}})
    nodes.append({"id":"download_denied","kind":"data","label":labels["download_denied"],"summary":"A current authorization rejection prevents returning file bytes.","event_node":"download","capture":{}})
    edges=[]
    for network in discovery["networks"]:
        for edge in network["edges"]:
            edges.append({"id":edge["id"],"from":edge["from"],"to":edge["to"],"type":"guard" if edge["relation"]=="guard" else "flow","label":edge["label"],"evidence":"confirmed trial intent; execution requires recorded facts"})
    machine={"engine":"bo.fsm","version":"1","states":list(state_ids),"values":list(state_ids),"initial":"pending","state_type":"enum","context":{field:{"type":"string"} for field in ["file_id","owner_id","recipient_id","reviewer_id"]},"events":{event:{"payload":{}} for event in ["approve","reject","cancel","revoke"]},"guards":{"authorized":{"source":{"path":"bo_stategraph/workflow.py","symbol":"SharingWorkflow.authorized"}}},"transitions":[{"source":before,"dest":after,"trigger":event,"conditions":["authorized"]} for before,after,event in [("pending","approved","approve"),("pending","rejected","reject"),("pending","cancelled","cancel"),("approved","revoked","revoke")]]}
    policy=deepcopy(discovery["policy"])
    policy.update(stage="bound",revision="sharing-policy-1")
    policy["predicates"][0]["source"]={"path":"app/policy.py","symbol":"flag_enabled"}
    cases=sorted(set(["approved","rejected","pending","cancelled","revoked","unauthorized","invalid_login"]+[case for operation in policy["operations"] for case in operation["cases"]]))
    mapping=json.loads((ROOT/"mapping.json").read_text(encoding="utf-8"))
    mapping["cases"]=cases
    save("mapping.json",mapping)
    code_files=sorted(path.relative_to(ROOT).as_posix() for folder in ["app","integrations"] for path in (ROOT/folder).rglob("*.py"))+["bo_stategraph/workflow.py"]
    sync["code_files"]=code_files
    sync["source_scope"]["exclude"]["static/graph/**"]="Unchanged canonical viewer assets validated by managed runtime fingerprints."
    sync["source_scope"]["frozen_sources"]={".trial/source":"review/frozen-archive-hashes.json","bo_stategraph/native_policy":"review/native-policy-hashes.json","bo_stategraph":"review/native-executor-hashes.json"}
    sync["probe_callees"]=list(dict.fromkeys(sync["probe_callees"]+["self.monitor.operation","self.monitor.record"]))
    sync["model"]="bo_stategraph/project.json"
    sync["watch_files"]=["tooling/build_model.py","tooling/observe.py","tooling/dev.py","tooling/check.py","tests/test_sharing.py","templates/base.html","templates/login.html","templates/workspace.html","templates/error.html","static/app.css","implementation.json","bo_stategraph/__init__.py","bo_stategraph/bo_contracts.py","bo_stategraph/execution_contract.py","bo_stategraph/native_executor.py","bo_stategraph/native_policy/runtime.py","bo_stategraph/native_policy/definition.py","bo_stategraph/native_policy/bindings.py"]
    save("sync.json",sync)
    model={"schema_version":3,"project_id":"team-file-sharing-lifecycle","revision":"sharing-1","title":"Team file sharing","intent":"intent.json","source_files":sorted(set(code_files+[path for path in sync["watch_files"] if (ROOT/path).is_file()]+["discovery.json","implementation.json"])),"nodes":nodes,"edges":edges,"overview":[{"node":node["id"],"x":index%4*280,"y":index//4*170} for index,node in enumerate(nodes[:10])],"scope":{"observable":["Selected account operations, file sharing, policy evaluations, SQLite operations, sharing states and notification effects"],"unknowns":["Finite local trial only; no distributed or production acceptance","Static unresolved calls are candidates, not observed execution","Already delivered local file copies cannot be recovered"]},"machine":machine,"policy":policy,"layout_id":"team-file-sharing-lifecycle","graph_roots":[node["id"] for node in nodes if node.get("layer")=="business"],"presentation":{"subject":"团队文件共享","layout_id":"team-file-sharing-lifecycle","names":{"nodes":{node["id"]:{"en":node["id"].replace('_',' ').title(),"zh-CN":node["label"]} for node in nodes},"states":{"pending":{"en":"Pending review","zh-CN":"待审核"},"approved":{"en":"Approved","zh-CN":"已通过"},"rejected":{"en":"Rejected","zh-CN":"已驳回"},"cancelled":{"en":"Cancelled","zh-CN":"已取消"},"revoked":{"en":"Revoked","zh-CN":"已撤销"}}}}}
    model=project_policy(model)
    save("bo_stategraph/project.json",{"protocol":"bo-project/v1","project_id":model["project_id"],"selection":{"mode":"drive","source":"user","answer":"drive：声明驱动","locator":"review/design-dialogue.md U004 and U006; independent trial"},"model":model})
    targets=["table:"+name for name in ["users","files","shares","notifications","journal"]]
    operations=[]
    for identifier,action,symbol in [("db_read","read","Store.read"),("db_write","write","Store.write"),("db_transaction","transaction","Store.transaction"),("db_transform","transform","clean_filename")]:
        is_transform=action=="transform"
        operations.append({"id":identifier,"label":{"db_read":"Read records","db_write":"Write records","db_transaction":"Commit or roll back","db_transform":"Normalize filename"}[identifier],"parent":"upload","source":{"path":"app/service.py" if is_transform else "app/storage.py","symbol":symbol},"store":"application","action":action,"targets":[] if action in {"transaction","transform"} else targets if action=="read" else [value for value in targets if value!="table:users"],"parameters":{},"before":{"filename":"string"} if is_transform else {},"after":{"filename":"string"} if is_transform else {"count":"number"} if action in {"read","write"} else {},"inputs":[],"required_cases":["approved"],"requirements":["R_STORAGE"]})
    config={"protocol":"bo-databases/v1","stores":[{"id":"application","label":"SQLite application records","engine":"sqlalchemy","url_env":"TRIAL_DATABASE_URL","selection":{"source":"user","answer":"采用 SQLite + SQLAlchemy，文件放在本项目自己的数据目录。","locator":"review/design-dialogue.md U003-U004"},"model_layer":"SQLAlchemy Core MetaData","source_files":["app/models.py","tooling/export_database.py"],"declaration":"bo_stategraph/database-declaration.json"}],"operations":operations,"exporters":[{"store":"application","output":"bo_stategraph/database-declaration.json","command":["{python}","-B","-X","utf8","tooling/export_database.py"]}]}
    for operation in operations:
        if operation["action"]=="write":
            operation["target_actions"]={target:"write" for target in operation["targets"]}
    save("bo_stategraph/databases.json",config)
    Store(ROOT/"data").initialize()
    os.environ["TRIAL_DATABASE_URL"]="sqlite:///"+(ROOT/"data/application.sqlite3").as_posix()
    save("bo_stategraph/database-declaration.json",export_sqlalchemy_metadata(metadata,"application"))
    report=synchronize(ROOT,update=True)
    if not report["valid"]:
        raise RuntimeError(report["errors"])
    project=json.loads((ROOT/"bo_stategraph/project.json").read_text(encoding="utf-8"))
    model=project["model"]
    index=scan(ROOT,code_files)
    if index["errors"]:
        raise RuntimeError(index["errors"])
    feature_sources={}
    features=[]
    for identifier in ["login","logout","upload","share","review","download","received_files","read_notification","http_action","http_download"]:
        path,symbol,inputs,outputs,req=definitions[identifier]
        source_id=path+"::"+symbol
        owned=[identifier]
        if identifier=="review":
            owned += ["cancel_share","revoke","notification","share_message"]
        if identifier=="http_action":
            owned += ["http_page"]
        feature_sources[source_id]=identifier
        parameters=[]
        for parameter in index["symbols"][source_id]["parameters"]:
            name=parameter["name"]
            if name=="self":
                continue
            field="password_supplied" if name=="password" else "size" if name=="content" else name
            parameters.append({"source":source_id,"name":name,"node":identifier,"direction":"in","field":field,"policy":"derived" if field!=name else "value",**({"reason":"Capture presence or byte length only; never collect credential or file content."} if field!=name else {})})
        feature_cases=[]
        for node in owned:
            case="cancelled" if node=="cancel_share" else "revoked" if node=="revoke" else "approved"
            feature_cases.extend({"case":case,"node":node,"phase":phase} for phase in ["enter","return"])
        if identifier=="login":
            feature_cases.append({"case":"invalid_login","node":"login","phase":"error"})
        features.append({"id":identifier,"label":labels[identifier],"business_node":identifier,"nodes":owned,"sources":[source_id],"parameters":parameters,"cases":feature_cases,"requirements":[req]})
    policy_nodes=[node for node in model["nodes"] if node.get("origin")=="policy-definition" and any(node.get("capture",{}).values())]
    policy_cases=[]
    for node in policy_nodes:
        case="revoked" if node["id"].split(":")[-1] in {"approved_fact","approved_rule","owner_approved"} else "cancelled" if node["id"].split(":")[-1]=="owner_pending" else "approved"
        policy_cases.append({"case":case,"node":node["id"],"phase":"decision"})
    features.append({"id":"permissions","label":"Current authorization rules","business_node":"download","nodes":[node["id"] for node in policy_nodes],"sources":["app/policy.py::flag_enabled"],"parameters":[{"source":"app/policy.py::flag_enabled","name":"value","node":"policy:grant_rule","direction":"in","field":"value","policy":"value"}],"cases":policy_cases,"requirements":["R_REVIEW","R_DOWNLOAD"]})
    for operation in operations:
        source=operation["source"]["path"]+"::"+operation["source"]["symbol"]
        parameters=[]
        for parameter in index["symbols"][source]["parameters"]:
            name=parameter["name"]
            if name=="self":
                continue
            parameters.append({"source":source,"name":name,"node":operation["id"],"direction":"out" if operation["action"]=="transform" else "in","field":"before" if operation["action"]=="transform" else "statement","policy":"derived","reason":"Represent the native call with its literal-free statement or selected transformation fields; do not collect connection objects."})
        features.append({"id":operation["id"],"label":operation["label"],"business_node":"upload","nodes":[operation["id"]],"sources":[source],"parameters":parameters,"cases":[{"case":"approved","node":operation["id"],"phase":"change" if operation["action"]=="transform" else "commit" if operation["action"]=="transaction" else "return"}],"requirements":["R_STORAGE"]})
    entries={source for feature in features for source in feature["sources"]}
    excluded={}
    support={}
    for sid,symbol in index["symbols"].items():
        if symbol["kind"]!="function" or sid in entries:
            continue
        if symbol["symbol"].endswith(".__init__"):
            excluded[sid]={"category":"construction","reason":"Object construction; business operations have separate feature mappings."}
        elif symbol["path"].startswith("integrations/") or symbol["path"]=="app/ports.py":
            excluded[sid]={"category":"observer","reason":"Exact optional monitoring transport or neutral monitoring port; never determines business permission or state."}
        elif symbol["symbol"]=="create_app.health":
            excluded[sid]={"category":"observer","reason":"Read-only readiness endpoint; returns build metadata without business effects.","routes":["/api/bo/health"]}
        else:
            support[sid]={"node":"download" if symbol["path"].endswith("policy.py") else "http_action" if symbol["path"].endswith("web.py") else "share","reason":"Implementation helper; searchable source candidate, not an execution claim."}
    implementation={"schema":"bo-implementation/v1","features":features,"support":support,"excluded":excluded}
    save("implementation.json",implementation)
    model["implementation"]=implementation
    model["source_files"]=sorted(set(model["source_files"]+sync["watch_files"]))
    model=enrich(model,index,1)
    project["model"]=model
    save("bo_stategraph/project.json",project)
    save("behavior.json",model)
    for network in discovery["networks"]:
        for node in network["nodes"]:
            node["model_nodes"]=[node["id"]]
    for decision in discovery["decisions"]:
        decision["requirements"]=[req["id"] for req in json.loads((ROOT/"intent.json").read_text(encoding="utf-8"))["requirements"]]
        decision["model_nodes"]=[value for value in decision["affects"] if value in {node["id"] for node in model["nodes"]}]
        decision["checks"]=[check["id"] for check in json.loads((ROOT/"acceptance.json").read_text(encoding="utf-8"))["checks"]]
        decision["links"]={key:decision[key] for key in ["requirements","model_nodes","checks"]}
    save("discovery.json",discovery)
    save("manifest.json",capture(ROOT,model))
    print(json.dumps({"nodes":len(model["nodes"]),"features":len(features),"cases":len(cases)}))


if __name__=="__main__":
    main()
