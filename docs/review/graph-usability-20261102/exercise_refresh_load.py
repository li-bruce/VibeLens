"""Measure a real three-user refresh workload without changing project source."""

import json
import os
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parent / ("native-refresh-profile-"+os.environ.get("BO_MINI_ROUND","09"))
OUT.mkdir(exist_ok=False)
BASE = "http://127.0.0.1:50958"
with sync_playwright() as driver:
    browser = driver.chromium.launch(headless=True, executable_path=sys.argv[1])
    try:
        graph = browser.new_page(viewport={"width": 1520, "height": 1060})
        preferences = graph.request.get(BASE+'/api/preferences').json()
        graph.route('**/api/preferences',lambda route:route.fulfill(json=preferences))
        graph.goto(BASE+'/graph?lang=zh-CN')
        graph.wait_for_function("typeof graphDebug!=='undefined' && graphDebug.graph")
        if graph.locator('#replay-timeline').get_attribute('aria-pressed')!='true':
            graph.locator('#replay-timeline').click()
        with graph.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/recordings/start')) as beginning:
            graph.locator('#record-start').click()
        identity=beginning.value.json()['id']
        graph.wait_for_function("graphDebug.timeline?.source === 'recording'")
        pages=[]
        for name in ('member1','member2','admin1'):
            page=browser.new_page()
            page.goto('http://127.0.0.1:50957',wait_until='domcontentloaded')
            page.get_by_label('账号',exact=True).fill(name)
            page.get_by_label('密码',exact=True).fill('Trial2026!')
            page.get_by_role('button',name='登录',exact=True).click()
            expect(page.locator('#workspace')).to_be_visible()
            pages.append(page)
        graph.wait_for_timeout(25000)
        started=time.monotonic()
        graph.locator('#record-stop').click()
        graph.wait_for_function("graphDebug.timeline?.source === 'saved'",timeout=60000)
        graph.wait_for_function("id=>document.querySelector('#record-list').value===id",arg=identity)
        result=graph.request.get(BASE+'/api/recordings/'+identity).json()
        (OUT/'recording.json').write_text(json.dumps(result),encoding='utf-8')
        report={'elapsed_stop_s':time.monotonic()-started,'events':len(result['events']),
                'settlement':result['producer_settlement'],'gaps':result['gaps'],
                'health':result['final']['health']}
        (OUT/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:
        browser.close()
