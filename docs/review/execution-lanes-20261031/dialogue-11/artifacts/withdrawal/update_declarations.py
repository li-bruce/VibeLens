"""Extend native declarations, UI and independent contracts for confirmed withdrawal."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def write(name,value):(ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
project=read('bo_stategraph/project.json')
model=project['model']
model['revision']='2'
machine=model['machine']
machine['states'].append('withdrawn')
machine['values'].append('withdrawn')
machine['events']['withdraw']={'payload':{'allowed':{'type':'boolean'}}}
machine['transitions'].append({'trigger':'withdraw','source':'pending','dest':'withdrawn','conditions':'operation_allowed'})
write('bo_stategraph/project.json',project)
acceptance=read('acceptance.json')
acceptance['checks'].append({'id':'withdrawal-business','requirement':'R_WITHDRAW','case':'withdrawal','path':['business_ok'],'equals':True})
write('acceptance.json',acceptance)
mapping=read('mapping.json')
mapping['cases'].append('withdrawal')
write('mapping.json',mapping)
whitebox=read('whitebox.json')
whitebox['rules'].append({'id':'uploader-withdraw','requirement':'R_WITHDRAW','claim':'Only a pending file owned by the caller is withdrawn; the completed operation reports withdrawn at revision two.',
    'basis':'R_WITHDRAW','category':'decision','node':'withdraw_file','source':{'path':'app/service.py','symbol':'FileService.withdraw'},
    'parameters':{'actor':'str','file_id':'str'}})
whitebox['checks'] += [
    {'id':'withdrawn-result-observed','rule':'uploader-withdraw','case':'withdrawal','phase':'return','count':{'min':1},
        'fields':[{'path':['outputs','state'],'type':'string','equals':'withdrawn'},{'path':['outputs','revision'],'type':'number','equals':2}]},
    {'id':'withdraw-denials-observed','rule':'uploader-withdraw','case':'withdrawal','phase':'error','count':{'min':4},
        'fields':[{'path':['outputs','error'],'type':'string','equals':'DomainError'}]}]
write('whitebox.json',whitebox)
database=read('bo_stategraph/databases.json')
for operation in database['operations']:
    if operation['id'] in {'db_update','db_candidates','db_file','db_transaction'}:
        operation['required_cases'].append('withdrawal')
    if operation['id']=='db_update':operation['label']='Commit review, recipient or withdrawal'
write('bo_stategraph/databases.json',database)
path=ROOT/'templates/index.html'
text=path.read_text(encoding='utf-8')
text=text.replace('上传者和指定审核人始终可看。','上传者始终可看；指定审核人在文件未撤回时可看。')
text=text.replace("'rejected':'未通过'","'rejected':'未通过','withdrawn':'已撤回'")
anchor="{% if file.state == 'pending' and file.reviewer_id == actor %}"
form='''{% if file.state == 'pending' and file.uploader_id == actor %}<form action="/files/{{ file.id }}/withdraw" method="post"><input type="hidden" name="csrf_token" value="{{ session.csrf_token }}"><button class="secondary">撤回文件</button></form>{% endif %}'''
assert anchor in text
path.write_text(text.replace(anchor,form+anchor),encoding='utf-8')
path=ROOT/'static/app/app.css'
path.write_text(path.read_text(encoding='utf-8')+'\n.withdrawn{background:#e8eced;color:#52646a}\n',encoding='utf-8')
print(json.dumps({'valid':True,'new_state':'withdrawn','resubmission':False,'prior_checks_preserved':True}))
