"""Adopt the explicit graph confirmation and preserve its simulated dialogue provenance."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def write(name,value):(ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
answer='对，就按这个理解做。拒绝原因保留原文，上传的人能在文件详情里看到，通过时不用填写。'
doc=read('review/rejection-reason-20261101-01/discovery-draft.json')
doc['sources'].append({'id':'U007','kind':'user','text':answer,
    'locator':'codex://threads/01a19395-491d-7800-a15c-711f4b1bcbda; explicit graph confirmation; coordinating-AI simulated business user'})
decision=next(d for d in doc['decisions'] if d['id']=='D_REJECTION_REASON')
decision.update(status='resolved',resolution={'kind':'user_answer','text':answer,'source_refs':['U007']})
decision['source_refs'].append('U007')
for node in doc['networks'][0]['nodes']:
    if node['id']=='rejection_reason':node['label']='拒绝原因原文'
doc['networks'][0]['outcome']+=' Rejected reviews retain their exact original reason for authorized file details; approvals need no reason.'
write('discovery.json',doc)
intent=read('intent.json')
intent['revision']='3'
review=next(r for r in intent['requirements'] if r['id']=='R_REVIEW')
review['text']+=' A rejected review requires a nonblank reason preserved verbatim; approval needs no reason.'
review['source']='U007'
intent['requirements'].append({'id':'R_REASON','text':'Require a nonblank rejection reason, preserve its original text without trimming or rewriting, and show it to the uploader in file details under the existing access rules. Approval needs no reason. Prior rejected records without a reason remain truthful historical records.','status':'confirmed','source':'U007'})
write('intent.json',intent)
write('review/rejection-reason-20261101-01/dialogue.json',{'kind':'coordinating-AI-simulated-business-dialogue',
    'request':'审核拒绝时填写原因，上传的人在详情里看得到；通过不用填。','question':decision['question'],
    'answer':answer,'conversation':'01a19395-491d-7800-a15c-711f4b1bcbda','independent_human_acceptance':False})
print(json.dumps({'valid':True,'allowed_requirement_changes':['R_REVIEW','R_REASON'],'verbatim':True}))
