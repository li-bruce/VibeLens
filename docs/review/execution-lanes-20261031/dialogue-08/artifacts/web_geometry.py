"""Actual pointer, rendering, layer and independent preference checks."""
import json
import math
from pathlib import Path
import sys
import traceback
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8983"
CHECKS = []

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
def stable(page):
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
def pick(page, ident):
    page.locator('#semantic [data-node-id="' + ident + '"]').dispatch_event("click")
def menu(page, ident):
    page.locator("#selection-menu").click()
    page.locator(ident).click()
def drag(page, x, y, dx=65, dy=37, button="left"):
    page.mouse.move(x, y)
    page.mouse.down(button=button)
    page.mouse.move(x + dx, y + dy, steps=15)
    page.mouse.up(button=button)
    stable(page)
def pos(page, ident):
    return page.evaluate("id=>{const b=graphDebug.graph.byId.get(id);return {x:b.x,y:b.y}}", ident)
def snapshot(page):
    return page.evaluate("""async()=>{const {nodePoint}=await import('/renderer.js'); const g=graphDebug.displayGraph,p=graphDebug.presentation;
      return {camera:graphDebug.camera, boxes:g.boxes.map(b=>({id:b.id,x:b.x,y:b.y,w:b.w,h:b.h,type:b.type||b.node.kind,parent:b.node.parent,point:nodePoint(g,p,b)})),
        regions:g.regions,edges:p.edges.map(e=>({id:e.id,from:e.from,to:e.to,type:e.type,members:e.members?.map(m=>m.id)})),
        glyphs:[...p.glyphs],regionIds:[...p.regions],ports:graphDebug.planarPorts,spatial:graphDebug.spatial,positions:graphDebug.spatialPositions,layers:graphDebug.layers,metrics:graphDebug.metrics};}""")
def screen(page, point):
    box = page.locator("#canvas-host canvas").first.bounding_box()
    camera = page.evaluate("graphDebug.camera")
    return box["x"] + camera["pan"]["x"] + point["x"] * camera["scale"], box["y"] + camera["pan"]["y"] + point["y"] * camera["scale"]
def saved(page):
    page.wait_for_function("/saved|已保存/i.test(document.querySelector('#layout-status').textContent)")
def mode(page, value):
    if page.locator("#legend-mode").inner_text() != value:
        page.locator("#layered-toggle").click()
    stable(page)

def planar(page):
    mode(page,"2D")
    page.locator("#analysis-view").select_option("overview")
    stable(page)
    if page.evaluate("graphDebug.presentation.regions.has('upload_file')"):
        pick(page,"upload_file"); menu(page,"#node-expand"); stable(page)
    pick(page,"upload_file")
    menu(page,"#focus-selection")
    stable(page)
    before = pos(page,"upload_file")
    state = snapshot(page)
    node = next(b for b in state["boxes"] if b["id"] == "upload_file")
    x,y = screen(page,node["point"])
    drag(page,x,y)
    after = pos(page,"upload_file")
    assert math.dist(list(before.values()),list(after.values())) > 5
    CHECKS.append({"case":"2D node pointer drag","before":before,"after":after})
    pick(page,"upload_file")
    menu(page,"#node-expand")
    stable(page)
    pick(page,"upload_file")
    menu(page,"#focus-selection")
    stable(page)
    state = snapshot(page)
    save("expanded-planar-geometry.json",state)
    region = next(r for r in state["regions"] if r["id"] == "upload_file")
    children = [b for b in state["boxes"] if b["parent"] == "upload_file"]
    assert children
    # Use the region's actual caption hit area after moving it clear of the toolbar.
    radius = region.get("r",region.get("radius"))
    assert radius
    viewport = page.locator("#canvas-host canvas").first.bounding_box()
    drag(page,viewport["x"]+230,viewport["y"]+45,0,-95)
    camera = page.evaluate("graphDebug.camera")
    font = max(13,11/camera["scale"])
    point = {"x":region["cx"],"y":region["cy"]+radius+(font+8/camera["scale"])/2+5/camera["scale"]}
    x,y = screen(page,point)
    before = {b["id"]:pos(page,b["id"]) for b in children}
    drag(page,x,y,55,29)
    after = {ident:pos(page,ident) for ident in before}
    deltas = [[after[ident][axis]-before[ident][axis] for axis in ("x","y")] for ident in before]
    assert all(math.dist(delta,deltas[0]) < .1 for delta in deltas) and math.hypot(*deltas[0]) > 5
    CHECKS.append({"case":"2D region caption pointer drag moves actual children together","children":len(children),"delta":deltas[0],"screen":[x,y]})
    camera = page.evaluate("graphDebug.camera")
    # Far canvas corner lies outside the fitted group and starts a pan.
    drag(page,viewport["x"]+230,viewport["y"]+45,-62,31)
    moved = page.evaluate("graphDebug.camera")
    assert moved["pan"] != camera["pan"]
    CHECKS.append({"case":"2D empty canvas pointer pan","before":camera,"after":moved})
    saved(page)
    expected = pos(page,"upload_file")
    page.reload(); stable(page)
    assert pos(page,"upload_file") == expected
    CHECKS.append({"case":"2D pointer coordinates and expansion survive reload","position":expected})

def spatial(page):
    planar_before = pos(page,"upload_file")
    mode(page,"3D")
    pick(page,"upload_file"); menu(page,"#focus-selection"); stable(page)
    label = page.locator('[data-spatial-region="upload_file"]').first
    label.wait_for(state="visible")
    box = label.bounding_box()
    before = page.evaluate("graphDebug.spatialPositions")
    drag(page,box["x"]+box["width"]/2,box["y"]+box["height"]/2,52,23)
    after = page.evaluate("graphDebug.spatialPositions")
    assert before["upload_file"] != after["upload_file"]
    actual_children = page.evaluate("[...graphDebug.graph.all.values()].filter(n=>n.parent==='upload_file').map(n=>n.id)")
    children = [ident for ident in actual_children if ident in before and ident in after]
    assert children
    deltas = [[after[ident][axis]-before[ident][axis] for axis in ("x","y","z")] for ident in children]
    assert all(math.dist(delta,deltas[0]) < .1 for delta in deltas)
    CHECKS.append({"case":"3D region label ray drag moves branch","children":len(children),"delta":deltas[0]})
    node_label = page.locator('[data-spatial-label="review_file"]')
    pick(page,"review_file"); menu(page,"#focus-selection"); stable(page)
    node_label.wait_for(state="visible")
    box = node_label.bounding_box()
    before_node = page.evaluate("graphDebug.spatialPositions.review_file")
    drag(page,box["x"]+box["width"]/2,box["y"]+box["height"]/2,48,24)
    after_node = page.evaluate("graphDebug.spatialPositions.review_file")
    assert before_node != after_node
    canvas = page.locator("#canvas-host canvas").last.bounding_box()
    camera = page.evaluate("graphDebug.spatial.camera")
    drag(page,canvas["x"]+230,canvas["y"]+45,-55,30,button="right")
    changed = page.evaluate("graphDebug.spatial.camera")
    assert camera != changed
    CHECKS.append({"case":"3D node pointer drag and empty-canvas camera pan","before":before_node,"after":after_node,"camera_changed":True})
    saved(page)
    expected = page.evaluate("graphDebug.spatialPositions")
    page.reload(); stable(page)
    assert page.evaluate("graphDebug.spatialPositions.upload_file") == expected["upload_file"]
    assert page.evaluate("graphDebug.spatialPositions.review_file") == expected["review_file"]
    mode(page,"2D")
    assert pos(page,"upload_file") == planar_before
    mode(page,"3D")
    assert page.evaluate("graphDebug.spatialPositions.review_file") == expected["review_file"]
    CHECKS.append({"case":"Independent 2D and 3D positions survive switching/reload","valid":True})

def routes_layers(page):
    for dimension in ("2D","3D"):
        mode(page,dimension)
        page.locator("#fit").click(); stable(page)
        for routing in ("straight","curve","orthogonal","bus"):
            frame = page.evaluate("graphDebug.spatial.frames" if dimension=="3D" else "graphDebug.metrics.drawCount")
            page.locator("#edge-routing").select_option(routing)
            page.wait_for_function("([mode,frame])=>(mode==='3D'?graphDebug.spatial.frames:graphDebug.metrics.drawCount)>frame",arg=[dimension,frame])
            page.wait_for_function("mode=>{const m=mode==='3D'?graphDebug.spatial:graphDebug.metrics;return !graphDebug.layoutBusy && !m.routeSolver.busy && m.routeSolver.total>0 && m.routeSolver.routed+m.routeSolver.unresolved===m.routeSolver.total}",arg=dimension)
            page.wait_for_function("mode=>{const m=mode==='3D'?graphDebug.spatial:graphDebug.metrics;const ports=mode==='3D'?m.edgePorts:graphDebug.planarPorts;return ports.length+m.routeSolver.unresolved>=m.routeSolver.total}",arg=dimension)
            value = snapshot(page)
            save("routes-"+dimension.lower()+"-"+routing+".json",value)
            ports = value["ports"] if dimension=="2D" else value["spatial"]["edgePorts"]
            assert ports
            ids = {edge["id"] for edge in value["edges"]}
            guides = {"projection:"+volume["id"]+":"+volume["layer"] for volume in (value["spatial"] or {}).get("volumes",[]) if volume.get("projection")}
            assert all(port["id"] in ids or (dimension=="3D" and port["id"] in guides) for port in ports)
            assert all(math.isfinite(port[side][axis]) for port in ports for side in ("start","end") for axis in (("x","y") if dimension=="2D" else ("x","y","z")))
            if dimension == "3D":
                if routing == "straight":
                    for port in ports:
                        if port["id"] in guides: continue
                        edge = next(edge for edge in value["edges"] if edge["id"]==port["id"])
                        if edge["from"] == edge["to"]: continue
                        for axis in ("x","y","z"):
                            assert abs(port["midpoint"][axis]-(port["start"][axis]+port["end"][axis])/2) < .01
                planes = sorted({plane["y"] for plane in value["spatial"]["layerPlanes"]})
                gap = value["layers"]["gap"]
                assert all(abs(b-a-gap)<.01 for a,b in zip(planes,planes[1:]))
            solver = value["spatial"]["routeSolver"] if dimension=="3D" else page.evaluate("graphDebug.metrics.routeSolver")
            CHECKS.append({"case":"Rendered route identities/finite ports and declared shape","dimension":dimension,"routing":routing,"ports":len(ports),"projection_guides":sorted(guides) if dimension=="3D" else [],"solver":solver})
        page.screenshot(path=str(OUT/("geometry-"+dimension.lower()+".png")))
    # Ruler toggles actual populated layers; consecutive planes retain a uniform gap.
    before = page.evaluate("graphDebug.layers")
    def toggle_rules():
        rect = page.locator("#layer-controls canvas").bounding_box()
        index = page.evaluate("graphDebug.layers.order.indexOf('rules')")
        page.mouse.click(rect["x"]+20,rect["y"]+40+index*34+15)
        stable(page)
    toggle_rules()
    hidden = page.evaluate("graphDebug.layers")
    assert "rules" not in hidden["visible"]
    assert not any(plane["id"]=="rules" for plane in page.evaluate("graphDebug.spatial.layerPlanes"))
    saved(page); page.reload(); stable(page)
    assert "rules" not in page.evaluate("graphDebug.layers.visible")
    toggle_rules()
    assert "rules" in page.evaluate("graphDebug.layers.visible")
    CHECKS.append({"case":"Layer visibility persists and actual planes compact","before":before,"hidden":hidden})
    mode(page,"2D")
    page.locator("#filter-toggle").click()
    check = page.locator('#filter-nodes input[value="decision"]')
    assert check.count()
    check.uncheck(); page.locator("#close-filters").click(); stable(page); saved(page)
    page.reload(); stable(page)
    page.locator("#filter-toggle").click()
    assert not page.locator('#filter-nodes input[value="decision"]').is_checked()
    page.locator("#close-filters").click()
    page.locator("#show-all").click(); stable(page)
    CHECKS.append({"case":"Type-filter retention and All elements restoration","valid":True})

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width":1540,"height":1100})
        page.set_default_timeout(15000)
        page.goto(BASE+"/graph"); stable(page)
        if page.locator("#replay-live").is_visible(): page.locator("#replay-live").click()
        before = page.request.get(BASE+"/api/view").json()
        operations = (("routes-layers",routes_layers),) if "--routes-only" in sys.argv else (("planar",planar),("spatial",spatial),("routes-layers",routes_layers))
        for name,operation in operations:
            try:
                operation(page)
            except BaseException:
                errors.append({"stage":name,"traceback":traceback.format_exc()})
                save("geometry-failure-"+name+".json",snapshot(page))
                page.screenshot(path=str(OUT/("geometry-failure-"+name+".png")))
                break
        after = page.request.get(BASE+"/api/view").json()
        assert [e["id"] for e in before["events"]] == [e["id"] for e in after["events"]]
        save("geometry-routes-checks.json" if "--routes-only" in sys.argv else "geometry-checks.json",{"valid":not errors,"checks":CHECKS,"errors":errors,"observer_events_unchanged":len(before["events"]),"build_id":after["manifest"]["build_id"]})
        browser.close()
    assert not errors, "See retained actual geometry failure"

if __name__=="__main__": main()
