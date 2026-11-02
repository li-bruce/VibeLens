"""Verify loaded nine-layer inventory and exact lexical parameter source ranges."""
from collections import Counter
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/".tmp/browserdeps"))
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:8983"
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",args=["--enable-unsafe-swiftshader"])
    page=browser.new_page(viewport={"width":1540,"height":1100})
    page.goto(BASE+"/graph");page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    if page.locator("#replay-live").is_visible():page.locator("#replay-live").click()
    before=page.request.get(BASE+"/api/view").json()
    page.locator("#analysis-view").select_option("code")
    page.wait_for_function("[...graphDebug.graph.all.values()].some(n=>n.code_role==='function') && !graphDebug.layoutBusy")
    if page.locator("#code-more").is_visible():page.locator("#code-more").click()
    inventory=page.request.get(BASE+"/api/code/graph?projection=all&limit=1500&depth=2").json()
    parameters=[]
    for symbol,name in (("FileService.upload","reviewer_id"),("FileService.upload","filename"),("FileService.review","decision"),("FileService.share","recipient_id")):
        node=next(n for n in inventory["nodes"] if n.get("code_role")=="parameter" and n.get("source",{}).get("symbol")==symbol and n["label"]==name)
        page.wait_for_function("id=>graphDebug.graph.all.has(id)",arg=node["id"])
        page.locator("#node-search").fill(node["id"]);page.locator("#node-search").press("Enter")
        page.wait_for_function("id=>graphDebug.graph.byId.has(id)",arg=node["id"])
        page.locator("#node-search").fill("")
        page.locator('#semantic [data-node-id="'+node["id"]+'"]').dispatch_event("click")
        page.locator("#selection-menu").click();page.locator("#source").click()
        page.locator("#source-code mark").first.wait_for()
        marks=page.locator("#source-code mark").all_text_contents()
        assert marks==[name],marks
        text=page.locator("#source-code").inner_text()
        assert "class FileService" in text and "def visible_files" in text
        parameters.append({"node":node["id"],"source":node["source"],"marks":marks,"complete_source_file":True})
        page.locator("#close-detail").click()
    network=page.evaluate("""async()=>{const {layerOf}=await import('/graph-layers.js');return {nodes:[...graphDebug.graph.all.values()].map(n=>({id:n.id,layer:layerOf(n),source:n.source,role:n.code_role})),edges:graphDebug.view.model.edges.map(e=>({id:e.id,from:e.from,to:e.to,type:e.type,code_relation:e.code_relation,data_relation:e.data_relation,mapping_role:e.mapping_role}))}}""")
    nodes={n["id"]:n for n in network["nodes"]}
    counts=Counter(n["layer"] for n in nodes.values())
    assert {"business","state","rules","api","execution","operations","project","code","data"}<=set(counts),counts
    crossing=[e for e in network["edges"] if e["from"] in nodes and e["to"] in nodes and nodes[e["from"]]["layer"]!=nodes[e["to"]]["layer"]]
    pairs=Counter(nodes[e["from"]]["layer"]+" -> "+nodes[e["to"]]["layer"] for e in crossing)
    assert crossing and all(any(layer in (nodes[e["from"]]["layer"],nodes[e["to"]]["layer"]) for e in crossing) for layer in counts)
    page.locator("#analysis-view").select_option("overview");page.wait_for_function("!graphDebug.layoutBusy")
    page.locator("#edge-routing").select_option("curve")
    after=page.request.get(BASE+"/api/view").json()
    assert [e["id"] for e in before["events"]]==[e["id"] for e in after["events"]]
    save("source-layer-audit.json",{"valid":True,"build_id":after["manifest"]["build_id"],"layer_counts":dict(counts),"cross_layer_pairs":dict(pairs),"cross_layer_edges":crossing,"parameters":parameters,"observer_events_unchanged":len(after["events"]),"boundary":"Static source/declaration links remain distinct from actual runtime events. UI source ranges were opened after the source projection loaded."})
    page.screenshot(path=str(OUT/"final-current-graph.png"))
    browser.close()
