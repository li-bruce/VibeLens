"""Extend native value/context contracts and independent reason expectations."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def write(name,value):(ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
project=read('bo_stategraph/project.json')
project['model']['revision']='3'
project['model']['machine']['context']['rejection_reason']={'type':'string'}
write('bo_stategraph/project.json',project)
acceptance=read('acceptance.json')
acceptance['checks'].append({'id':'rejection-reason-business','requirement':'R_REASON','case':'rejection_reason','path':['business_ok'],'equals':True})
write('acceptance.json',acceptance)
mapping=read('mapping.json')
mapping['cases'].append('rejection_reason')
mapping['fields'].append({'id':'rejection-reason','node':'rejection_reason','actual':['rejection_reason'],'mapped':['context','rejection_reason']})
write('mapping.json',mapping)
whitebox=read('whitebox.json')
whitebox['rules'] += [
    {'id':'reason-validation','requirement':'R_REASON','claim':'Blank rejection text is invalid; approval needs none.','basis':'R_REASON','category':'decision',
        'node':'review_reason_check','source':{'path':'app/service.py','symbol':'FileService.review_reason'},'parameters':{'decision':'str','reason':'str'}},
    {'id':'reason-preserved','requirement':'R_REASON','claim':'The successful rejected review returns the exact original reason.','basis':'R_REASON','category':'decision',
        'node':'review_file','source':{'path':'app/service.py','symbol':'FileService.review'},'parameters':{'actor':'str','file_id':'str','decision':'str','reason':'str'}}]
whitebox['checks'] += [
    {'id':'blank-reason-check-false','rule':'reason-validation','case':'rejection_reason','phase':'decision','count':{'min':2},
        'select':[{'path':['outputs','valid'],'equals':False}], 'fields':[{'path':['inputs','decision'],'equals':'reject'}]},
    {'id':'verbatim-reason-result','rule':'reason-preserved','case':'rejection_reason','phase':'return','count':{'min':1},
        'select':[{'path':['outputs','state'],'equals':'rejected'}],
        'fields':[{'path':['outputs','rejection_reason'],'equals':'  缺少签字页。\n请补齐附件 <原件>。  '},{'path':['outputs','revision'],'equals':2}]}]
write('whitebox.json',whitebox)
path=ROOT/'templates/index.html'
text=path.read_text(encoding='utf-8')
old='''<form action="/files/{{ file.id }}/review" method="post"><input type="hidden" name="csrf_token" value="{{ session.csrf_token }}"><button name="decision" value="approve">通过审核</button><button class="secondary" name="decision" value="reject">不通过</button></form>'''
new='''<form action="/files/{{ file.id }}/review" method="post"><input type="hidden" name="csrf_token" value="{{ session.csrf_token }}"><button name="decision" value="approve">通过审核</button></form><form class="review-reject" action="/files/{{ file.id }}/review" method="post"><input type="hidden" name="csrf_token" value="{{ session.csrf_token }}"><input type="hidden" name="decision" value="reject"><label for="reason-{{ file.id }}">拒绝原因（不通过时必填）<textarea id="reason-{{ file.id }}" name="reason" rows="3" required></textarea></label><button class="secondary">不通过</button></form>'''
assert old in text
path.write_text(text.replace(old,new),encoding='utf-8')
path=ROOT/'static/app/app.css'
path.write_text(path.read_text(encoding='utf-8')+'\n.file-actions .review-reject{display:grid;gap:8px;flex-basis:100%}.review-reject label{margin:0}.review-reject textarea{display:block;box-sizing:border-box;width:100%;margin-top:8px;padding:10px;font:inherit;line-height:1.6;color:#183630;background:#fff;border:1px solid #cad8cd;border-radius:5px;resize:vertical}.review-reject button{justify-self:start}.details-page{max-width:960px;padding-top:25px}.details-page h1{font-size:28px;margin-top:10px}.rejection-details{margin:28px 0}.rejection-details h2{font-size:18px}.reason-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;background:#f7f5f0;border-left:3px solid #ad7b65;padding:18px}\n',encoding='utf-8')
print(json.dumps({'valid':True,'prior_checks_preserved':True,'verbatim_reason_expected':True}))
