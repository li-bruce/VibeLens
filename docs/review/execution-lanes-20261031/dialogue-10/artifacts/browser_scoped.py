"""Verify a scoped native view or replay with exact nodes and original edges."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / '.tmp/browserdeps'))
from playwright.sync_api import sync_playwright

def read(name): return json.loads((OUT / name).read_text(encoding='utf-8'))
def get(path): return json.load(urllib.request.urlopen('http://127.0.0.1:8983' + path, timeout=60))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

stage = sys.argv[1]
activation = read('control-activate-host.result.json')['result']
plan = read(stage + '-plan-host.result.json')['result']
rid = read('recording-evidence.json')['recording_id']
raw_path = ROOT / 'bo_stategraph/data/recordings' / (rid + '.json')
raw_before = sha(raw_path)
before = get('/api/view')
errors, responses = [], []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1800,'height':1150})
    page.on('pageerror', lambda e:errors.append(str(e)))
    page.goto(activation['graph_url'], wait_until='domcontentloaded')
    page.wait_for_function('window.graphDebug?.graph?.boxes.length>0 && !graphDebug.layoutBusy', timeout=90000)
    for _ in range(40):
        status = get('/api/vibelens/control?vl_session=' + activation['session'])
        if status.get('result'):
            break
        page.wait_for_timeout(500)
    ack = status.get('result')
    geometry = page.evaluate('''()=>({boxes:graphDebug.graph.boxes.map(b=>({id:b.id,node:b.node})),edges:graphDebug.graph.edges,ports:graphDebug.planarPorts,algorithm:graphDebug.layoutAlgorithm,bodyPlan:document.body.dataset.controlPlan,metrics:graphDebug.metrics,timeline:graphDebug.timeline,replay:graphDebug.view.replay})''')
    visible = {b['id'] for b in geometry['boxes']}
    edge_ids = {e['id'] for e in geometry['edges']}
    missing_nodes = sorted(set(plan['node_ids'])-visible)
    missing_edges = sorted(set(plan['edge_ids'])-edge_ids)
    page.screenshot(path=str(OUT / (stage + '-scoped.png')), full_page=True)
    replay_checks = {}
    if ack and ack['status']=='applied' and stage=='replay':
        page.wait_for_function('graphDebug.timeline?.source==="saved"')
        page.locator('#replay-grain').select_option('events')
        page.locator('#replay-next').click()
        first = page.evaluate('graphDebug.view.replay.index')
        page.locator('#replay-next').click()
        page.wait_for_function('i=>graphDebug.view.replay.index!==i', arg=first)
        second = page.evaluate('graphDebug.view.replay.index')
        page.locator('#replay-play').click()
        page.wait_for_function('i=>graphDebug.view.replay.index!==i', arg=second)
        page.locator('#replay-play').click()
        selected = page.evaluate('graphDebug.view.replay')
        timeline_id = page.locator('#recording-timeline').get_attribute('data-event-id')
        replay_checks = {'first_index':first,'second_index':second,'after_play':selected,'timeline_event_id':timeline_id,
                         'selected_event_ids':plan['recording']['event_ids']}
        page.screenshot(path=str(OUT / 'replay-playing-paused.png'), full_page=True)
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('window.graphDebug?.graph?.boxes.length>0 && !graphDebug.layoutBusy', timeout=90000)
    reload_visible = page.evaluate('graphDebug.graph.boxes.map(b=>b.id)')
    page.screenshot(path=str(OUT / (stage+'-reload.png')), full_page=True)
    browser.close()
after = get('/api/view')
unchanged = [e['id'] for e in before['events']]==[e['id'] for e in after['events']]
raw_unchanged = sha(raw_path)==raw_before
result = {'valid':bool(ack and ack['status']=='applied' and not missing_nodes and not missing_edges and raw_unchanged and unchanged),
          'stage':stage,'url':activation['graph_url'],'acknowledgement':ack,'plan':plan,'geometry':geometry,
          'missing_nodes':missing_nodes,'missing_original_edges':missing_edges,'reload_visible':reload_visible,
          'replay_checks':replay_checks,'page_errors':errors,'raw_recording_unchanged':raw_unchanged,
          'raw_recording_sha256':raw_before,'observer_reads_added_zero_events':unchanged,
          'before_health':before['health'],'after_health':after['health']}
(OUT/(stage+'-browser.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('valid','acknowledgement','missing_nodes','missing_original_edges','raw_recording_unchanged','observer_reads_added_zero_events')},ensure_ascii=False))
assert result['valid'], 'Scoped view did not apply every current node and original relation'
