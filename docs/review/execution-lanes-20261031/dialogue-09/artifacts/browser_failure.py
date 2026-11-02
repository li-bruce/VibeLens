"""Read the actual loaded runtime page and failed HTTP endpoint without changing views."""
import json
import os
from pathlib import Path
import sys
import traceback

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / '.tmp/browserdeps'))
from playwright.sync_api import sync_playwright

os.environ['TEMP'] = os.environ['TMP'] = str(OUT / '.tmp')

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',
            args=['--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1540, 'height': 1100})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8983/graph')
        page.wait_for_load_state('domcontentloaded')
        page.wait_for_function('window.graphDebug?.graph?.boxes?.length > 0 && !graphDebug.layoutBusy', timeout=60000)
        before = page.request.get('http://127.0.0.1:8983/api/view', timeout=60000).json()
        page.screenshot(path=str(OUT / 'runtime-page-at-blocker.png'))
        graph = page.evaluate('({build_id: graphDebug.view.manifest.build_id, nodes: graphDebug.graph.boxes.map(b=>b.id), edges: graphDebug.planarPorts.map(e=>e.id), layout: graphDebug.layoutAlgorithm})')
        response = page.request.get('http://127.0.0.1:8983/api/vibelens/control/context')
        assert response.status == 404
        failure = {'status': response.status, 'body': response.text()}
        page.goto('http://127.0.0.1:8983/api/vibelens/control/context')
        page.screenshot(path=str(OUT / 'control-context-404.png'))
        after = page.request.get('http://127.0.0.1:8983/api/view', timeout=60000).json()
        assert graph['build_id'] == before['manifest']['build_id'] == after['manifest']['build_id']
        assert [e['id'] for e in before['events']] == [e['id'] for e in after['events']]
        result = {'valid': True, 'runtime_page_loaded': True, 'graph': graph, 'context': failure,
                  'errors': errors, 'observer_reads_added_zero_events': True,
                  'scope': 'Read-only browser evidence. No vl_session graph URL could be obtained because normal activation failed. Applied control and filtered replay are not_run.'}
        assert not errors
        (OUT / 'browser-blocker.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'valid': True, 'build_id': graph['build_id'], 'nodes': len(graph['nodes']),
                          'edges': len(graph['edges']), 'context_status': failure['status']}))
        browser.close()

if __name__ == '__main__':
    try:
        main()
    except BaseException:
        (OUT / 'browser-blocker-failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
