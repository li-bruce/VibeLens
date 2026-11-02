"""Project the requested rejection-reason branch without editing accepted behavior."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
doc=json.loads((ROOT/'discovery.json').read_text(encoding='utf-8-sig'))
doc['sources'] += [
    {'id':'U006','kind':'user','text':'审核拒绝时填写原因，上传的人在详情里看得到；通过不用填。',
     'locator':'codex://threads/01a19395-491d-7800-a15c-711f4b1bcbda; current delegated request; coordinating-AI simulated business user'},
    {'id':'A_REASON_CONFIRM','kind':'assistant','text':'拒绝时原因必填并保存，上传者在详情看到原文；通过时无需填写，现有审核与读取权限保持。业务图将按这条分支更新，这样理解是否正确？',
     'locator':'codex://threads/01a19395-491d-7800-a15c-711f4b1bcbda; current asynchronous graph-scope question'}]
net=doc['networks'][0]
net['nodes'] += [
    {'id':'review_reason_check','label':'不通过需填写原因；通过可空','kind':'condition','source_refs':['U006'],'model_nodes':['review_reason_check']},
    {'id':'rejection_reason','label':'已保存的拒绝原因','kind':'data','source_refs':['U006'],'model_nodes':['rejection_reason']}]
net['edges'] += [
    {'id':'guard_review_reason','from':'review_reason_check','to':'review_file','relation':'guard','label':'拒绝必填；通过无需填写','source_refs':['U006']},
    {'id':'data_review_reason','from':'review_file','to':'rejection_reason','relation':'data','label':'拒绝时保存原因','source_refs':['U006']},
    {'id':'data_reason_details','from':'rejection_reason','to':'access_file','relation':'data','label':'上传者在详情查看原因','source_refs':['U006']}]
doc['decisions'].append({'id':'D_REJECTION_REASON','topic':'completion','question':doc['sources'][-1]['text'],
    'why':'Confirm the requested validation/storage/display branch without changing established role or state rules.',
    'affects':['review_reason_check','review_file','rejection_reason','access_file'],'blocking':True,'status':'open','priority':1,
    'source_refs':['U006'],'asked_in':['A_REASON_CONFIRM'],'requirements':['R_REVIEW','R_REASON'],
    'model_nodes':['review_file','review_reason_check','rejection_reason','access_file'],'checks':['rejection-reason-business'],
    'links':{'requirements':['R_REVIEW','R_REASON'],'model_nodes':['review_file','review_reason_check','rejection_reason','access_file'],'checks':['rejection-reason-business']}})
(OUT/'discovery-draft.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'request.txt').write_text(doc['sources'][-2]['text']+'\n',encoding='utf-8')
print(json.dumps({'valid':True,'accepted_business_source_changed':False,'pending_question':'D_REJECTION_REASON'}))
