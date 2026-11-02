"""Observe the actual scoped browser acknowledgement and rendered identities."""
import json
from pathlib import Path
import sys
import time
import urllib.request

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / '.tmp/browserdeps'))
from playwright.sync_api import sync_playwright

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def get(path):
    return json.load(urllib.request.urlopen('http://127.0.0.1:8983' + path, timeout=60))

activation = read('control-activate-host.result.json')['result']
plan = read('control-plan-host.result.json')['result']
session = activation['session']
before = get('/api/view')
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',
                                args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1540,'height':1100})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(activation['graph_url'], wait_until='domcontentloaded')
    page.wait_for_function('window.graphDebug?.graph?.boxes.length > 0 && !graphDebug.layoutBusy', timeout=90000)
    acknowledgement = None
    for _ in range(30):
        status = get('/api/vibelens/control?vl_session=' + session)
        if status.get('result'):
            acknowledgement = status['result']
            break
        page.wait_for_timeout(500)
    geometry = page.evaluate('''()=>({
      visible:graphDebug.graph.boxes.map(b=>({id:b.id,node:b.node,rect:{x:b.x,y:b.y,w:b.w,h:b.h}})),
      edges:graphDebug.graph.edges,
      ports:graphDebug.planarPorts,
      algorithm:graphDebug.layoutAlgorithm,
      bodyControlPlan:document.body.dataset.controlPlan,
      analysis:document.querySelector('#analysis-view').value,
      build:graphDebug.view.manifest.build_id,
      metrics:graphDebug.metrics
    })''')
    visible = {n['id'] for n in geometry['visible']}
    missing = sorted(set(plan['node_ids']) - visible)
    geometry['missing_requested_nodes'] = missing
    geometry['missing_requested_edges'] = sorted(set(plan['edge_ids']) - {p['id'] for p in geometry['ports']})
    page.screenshot(path=str(OUT / 'scoped-control.png'), full_page=True)
    (OUT / 'scoped-control.html').write_text(page.content(), encoding='utf-8')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('window.graphDebug?.graph?.boxes.length > 0 && !graphDebug.layoutBusy', timeout=90000)
    reload_visible = page.evaluate('graphDebug.graph.boxes.map(b=>b.id)')
    page.screenshot(path=str(OUT / 'scoped-control-reload.png'), full_page=True)
    browser.close()
after = get('/api/view')
unchanged = [e['id'] for e in before['events']] == [e['id'] for e in after['events']]
result = {'valid': acknowledgement is not None and acknowledgement['status'] == 'applied' and not missing,
          'url': activation['graph_url'], 'plan':plan, 'acknowledgement':acknowledgement,
          'geometry':geometry, 'reload_visible':reload_visible, 'page_errors':errors,
          'observer_reads_added_zero_events':unchanged,
          'before_health':before['health'], 'after_health':after['health']}
(OUT / 'browser-control.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k:result[k] for k in ('valid','acknowledgement','observer_reads_added_zero_events','page_errors')},ensure_ascii=False))
assert unchanged
assert result['valid'], 'Actual scoped viewer did not apply every requested node'
