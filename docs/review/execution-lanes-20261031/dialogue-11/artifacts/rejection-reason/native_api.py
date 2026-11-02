"""Compare actual Flask routes to the current static API graph independently."""
import inspect
import json
from pathlib import Path
import sys
import tempfile
import urllib.request

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT))
from app.web import create_app

with urllib.request.urlopen('http://127.0.0.1:8983/api/code/graph?projection=all&limit=1500&depth=2',timeout=60) as response:
    graph=json.load(response)
(OUT/'code-graph-web.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
with tempfile.TemporaryDirectory(dir=OUT/'.tmp',prefix='native-routes-') as directory:
    app=create_app(ROOT,database=Path(directory)/'routes.sqlite3')
    native=[{'path':rule.rule,'methods':sorted(rule.methods),
             'handler':app.view_functions[rule.endpoint].__qualname__,
             'source':inspect.getsourcefile(app.view_functions[rule.endpoint]),
             'line':inspect.getsourcelines(app.view_functions[rule.endpoint])[1]}
            for rule in app.url_map.iter_rules() if rule.endpoint!='static']
    app.extensions['trial_store'].engine.dispose()
nodes={n['id']:n for n in graph['nodes']}
endpoints=[n for n in nodes.values() if n.get('code_role')=='endpoint']
assert len(endpoints)==len(native)==9
comparisons=[]
for row in native:
    endpoint=next(n for n in endpoints if n['api']['path']==row['path'])
    handlers=[nodes[e['to']] for e in graph['edges'] if e['from']==endpoint['id'] and e.get('code_relation')=='handles']
    assert len(handlers)==1 and handlers[0]['source']['symbol']==row['handler']
    assert endpoint['api']['handler']==row['handler'] and endpoint['api']['handler_resolved']
    methods=endpoint['api']['methods']
    assert set(methods)==set(row['methods'])-{'OPTIONS','HEAD'} if methods else row['methods']==['GET','HEAD','OPTIONS']
    comparisons.append({'native':row,'endpoint':endpoint['id'],'handler':handlers[0]['id']})
result={'valid':True,'comparisons':comparisons,'static_links_are_not_execution':True}
(OUT/'native-api-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'valid':True,'routes':len(comparisons)}))
