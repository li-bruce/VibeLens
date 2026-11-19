"""Match an actual SQLite reproduction to a TLC trace in the shared desktop viewer.

This focused UI/native fixture is not whole-application binding acceptance. The
full binding, mapping and independent business gates remain separate regressions.
No runtime events or HTTP responses are fabricated by the browser test.
"""
from pathlib import Path
import json
import os
import runpy
import sqlite3
import sys
import threading
import traceback

ROOT=Path.cwd()
sys.path[:0]=[str(ROOT/'skills/vibelens/scripts'),str(ROOT/'tests')]
from playwright.sync_api import sync_playwright
from test_native_behavior_integration import NativeIntegrationTests
from test_tlc_runtime import finite_fixture
from test_behavior_contract import literal,variable,operation
from bo_observer.project_artifacts import byte_hash
from bo_observer.analysis.runner import run_profile
from bo_observer.service import GraphSession,make_server
from bo_observer.adapters.python.bo_probe import BOProbe

out=ROOT/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
fixture=NativeIntegrationTests();fixture.setUp()
snapshot=finite_fixture()
snapshot['behavior']['actions'][0]['enabled']={'op':'param','id':'allowed'}
snapshot['behavior']['properties'][0].update(kind='state_invariant',action_refs=[],
    expression=operation('eq',variable(),literal('inactive','status')))
fixture.project['model'].pop('behavior_bindings')
for role,name,data in [('behavior','bo_stategraph/behavior.json',snapshot['behavior']),
                       ('discovery','discovery.json',snapshot['behavior_discovery'])]:
    raw=(json.dumps(data)+'\n').encode()
    (fixture.root/name).write_bytes(raw)
    fixture.project['contracts'][role]={'path':name,'schema':data['schema'],'sha256':byte_hash(raw)}
fixture.write()
analysis=run_profile(fixture.root,snapshot,'small')
assert analysis['status']=='fail',analysis['results']
trace_path=fixture.root/analysis['directory']/'property-0/logical-trace.json'
trace=json.loads(trace_path.read_text())
raw_trace=analysis['results'][0]['trace']
assert raw_trace['steps']==[{'action':'grant-share','parameters':{'allowed':True}}],raw_trace['steps']
(out/'logical-trace.json').write_text(json.dumps(trace,indent=2)+'\n')
native=runpy.run_path(str(fixture.root/'application.py'))
session=GraphSession(fixture.root)
probe=BOProbe(fixture.project,session.manifest['build_id'],sink=session.bo_sink)
session.bo_bind_capture(scope_setter=probe.bo_set_scope,flush_capture=lambda:probe.flush(3),health=probe.bo_health)
server=make_server(session,0)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
result={'valid':False,'origin':'Actual TLC and SQLite executions','checks':[],'errors':[]}
try:
    with sync_playwright() as driver:
        browser=driver.chromium.launch(headless=True,executable_path=os.environ['BO_BROWSER_EXECUTABLE'],args=['--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1000})
        page.on('pageerror',lambda e:result['errors'].append(str(e)))
        page.goto(f'http://127.0.0.1:{server.server_port}/graph?lang=zh-CN')
        page.wait_for_function('window.graphDebug?.graph && !graphDebug.layoutBusy')
        page.select_option('#analysis-view','functions');page.click('#expand');page.click('#fit')
        page.click('#record-start')
        page.wait_for_function("!document.querySelector('#record-stop').disabled")
        connection=sqlite3.connect(':memory:')
        connection.execute('CREATE TABLE states (model TEXT PRIMARY KEY,value TEXT)')
        connection.executemany('INSERT INTO states VALUES (?,?)',[('grant','inactive'),('archive','inactive')]);connection.commit()
        statements=[];connection.set_trace_callback(statements.append)
        with probe.span('share',lambda:{'inputs':{'owner':'state-model:grant','allowed':True}},entity='1',attempt='reproduction'):
            native['share'](connection,True)
            native['commit'](connection)
            probe.record('commit','commit',lambda:{'outputs':{'transaction_id':native['read_commit'](statements)}})
            values=native['read_native'](connection)
            for owner,state in values.items():
                probe.record(owner,'read',lambda state=state:{'outputs':{'state':state}})
        assert probe.flush(3)
        observed={key+'-status':value for key,value in native['read_native'](connection).items()}
        assert observed==raw_trace['states'][-1],(observed,raw_trace['states'][-1])
        connection.close()
        page.click('#record-stop')
        page.wait_for_function('graphDebug.timeline?.lifecycles?.some(item=>item.end>item.start)')
        before=page.evaluate('graphDebug.view.events.length')
        timeline=page.evaluate('graphDebug.timeline')
        saved=session.recordings.list()['recordings'][0]
        recorded=session.recordings.get(saved['id'])
        assert len(recorded['events'])>=5,len(recorded['events'])
        for mode in ['2D','3D']:
            if page.locator('#layered-toggle').inner_text()!=mode:page.click('#layered-toggle')
            page.click('#fit')
            page.screenshot(path=str(out/(mode+'-native.png')))
            page.locator('#analysis-trace-file').set_input_files(trace_path)
            page.wait_for_selector('#analysis-trace-panel:not([hidden]) svg')
            slider=page.locator('#analysis-trace-panel input[type=range]');slider.fill('1');slider.dispatch_event('input')
            assert page.evaluate('graphDebug.view.events.length')==before
            assert 'active' in page.locator('#analysis-trace-panel').inner_text()
            page.screenshot(path=str(out/(mode+'-logical.png')))
            page.locator('.analysis-trace-header button').click()
            assert page.evaluate('graphDebug.timeline.lifecycles.length')==len(timeline['lifecycles'])
            assert session.recordings.get(saved['id'])==recorded
            result['checks'].append({'mode':mode,'native_event_count':len(recorded['events']),'logical_steps':len(raw_trace['steps']),'native_values':observed,'runtime_retained':True})
        (out/'native-timeline.json').write_text(json.dumps(timeline,indent=2)+'\n')
        (out/'native-view.json').write_text(json.dumps(session.view(),indent=2)+'\n')
        (out/'native-recording.json').write_text(json.dumps(recorded,indent=2)+'\n')
        assert not result['errors'],result['errors']
        result['valid']=True
        browser.close()
except Exception as error:
    result.update(failure=str(error),traceback=traceback.format_exc())
finally:
    probe.close();server.shutdown();server.server_close();thread.join(5);fixture.doCleanups()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));raise SystemExit(not result['valid'])
