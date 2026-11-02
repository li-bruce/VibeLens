"""Preserve the actual simulated dialogue and add only the confirmed withdrawal scope."""
from copy import deepcopy
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def write(name,value):(ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

request='我想把还没审核的文件撤回。'
answer='撤回后就结束这次流程，这一版先不做再次提交。文件保留，上传的人仍然可以查看和下载；指定审核人不再看到待审核任务，也不能查看或下载。只允许上传的人撤回，而且必须还是待审核状态。'
questions='撤回后，这份文件的流程是直接结束，还是以后可以再次提交审核？\n现有规则允许上传者和指定审核人在各阶段查看、下载。撤回后，指定审核人的读取权限怎么处理？'
write('review/withdrawal-20261101-01/dialogue.json',{'kind':'coordinating-AI-simulated-business-dialogue',
    'conversation':'01a19395-491d-7800-a15c-711f4b1bcbda','request':request,'questions':questions,'answer':answer,
    'independent_human_acceptance':False,'allowed_requirement_changes':['R_WITHDRAW','R_ACCESS']})
intent=read('intent.json')
intent['revision']='2'
access=next(r for r in intent['requirements'] if r['id']=='R_ACCESS')
access['text']='The uploader can always read metadata/download. The assigned reviewer can read except after withdrawal. A recipient requires approval and an actual share; everyone else is denied.'
access['source']='U004'
intent['requirements'].append({'id':'R_WITHDRAW','text':'Only the logged-in uploader may withdraw a still-pending file. Withdrawal ends this workflow without resubmission. Retain file content and uploader metadata/download; remove reviewer tasks and deny reviewer metadata/download, including stale pages.','status':'confirmed','source':'U004'})
intent['exclusions'].append('Resubmission after withdrawal.')
write('intent.json',intent)
doc=read('discovery.json')
for sid,kind,text in [('U003','user',request),('A_WITHDRAW_QUESTIONS','assistant',questions),('U004','user',answer)]:
    doc['sources'].append({'id':sid,'kind':kind,'text':text,'locator':'codex://threads/01a19395-491d-7800-a15c-711f4b1bcbda; current delegated dialogue; business user simulated by coordinating AI'})
net=doc['networks'][0]
net['outcome']+=' The uploader may withdraw a pending file, ending that workflow and reviewer access while retaining uploader access.'
net['nodes'] += [{'id':'withdraw_file','label':'上传者撤回待审核文件','kind':'action','source_refs':['U003','U004'],'model_nodes':['withdraw_file']},
    {'id':'withdrawn','label':'已撤回：本次流程结束','kind':'state','source_refs':['U004'],'model_nodes':['withdrawn']}]
for node in net['nodes']:
    if node['id']=='uploader_access':
        node['label']='上传者始终可读；审核人撤回后不可读'
        node['source_refs']=['U001','U004']
for edge in net['edges']:
    if edge['id']=='guard_uploader_reviewer_access':
        edge['label']='上传者始终可读；审核人仅未撤回时可读'
        edge['source_refs']=['U001','U004']
net['edges'] += [
    {'id':'flow_pending_withdraw','from':'pending_review','to':'withdraw_file','relation':'cancel','label':'仅上传者且仍为待审核','source_refs':['U004']},
    {'id':'flow_withdrawn','from':'withdraw_file','to':'withdrawn','relation':'flow','label':'撤回后结束；本版不再提交','source_refs':['U004']},
    {'id':'guard_withdrawn_access','from':'withdrawn','to':'access_file','relation':'guard','label':'保留文件；仅上传者可读取','source_refs':['U004']}]
old=next(d for d in doc['decisions'] if d['id']=='D_ACCESS')
doc['changes'].append({'id':'C_ACCESS_WITHDRAW','decision':'D_ACCESS','previous':deepcopy(old),'source_refs':['U004'],
    'reason':'The new confirmed withdrawal exception replaces reviewer all-stage access only for withdrawn files.'})
old['source_refs']=list(dict.fromkeys(old['source_refs']+['U004']))
old['resolution']={'kind':'user_answer','text':answer,'source_refs':['U004']}
doc['decisions'].append({'id':'D_WITHDRAW','topic':'cancellation','question':questions,
    'why':'Determine withdrawal authority, terminal state and reviewer access without assuming new business policy.',
    'affects':['withdraw_file','withdrawn','access_file'],'blocking':True,'status':'resolved','priority':1,
    'source_refs':['U003','U004'],'asked_in':['A_WITHDRAW_QUESTIONS'],
    'resolution':{'kind':'user_answer','text':answer,'source_refs':['U004']},
    'requirements':['R_WITHDRAW','R_ACCESS'],'model_nodes':['withdraw_file','withdrawn','access_file'],
    'checks':['withdrawal-business'],'links':{'requirements':['R_WITHDRAW','R_ACCESS'],
        'model_nodes':['withdraw_file','withdrawn','access_file'],'checks':['withdrawal-business']}})
policy=doc['policy']
policy['revision']='withdrawal-01'
policy['inputs'].update(pending='boolean',withdrawn='boolean')
policy['nodes'] += [
    {'id':'pending','op':'input','name':'pending','label':'仍为待审核','source_refs':['U004']},
    {'id':'withdrawn','op':'input','name':'withdrawn','label':'文件已撤回','source_refs':['U004']},
    {'id':'not_withdrawn','op':'not','inputs':['withdrawn'],'label':'尚未撤回','source_refs':['U004']},
    {'id':'reviewer_access','op':'all','inputs':['actor_is_reviewer','not_withdrawn'],'label':'指定审核人且尚未撤回','source_refs':['U004']},
    {'id':'withdraw_allowed','op':'all','inputs':['logged_in','actor_is_uploader','pending'],'label':'已登录上传者且仍为待审核','source_refs':['U004']}]
basis=next(n for n in policy['nodes'] if n['id']=='file_access_basis')
basis['inputs']=['reviewer_access' if name=='actor_is_reviewer' else name for name in basis['inputs']]
basis['source_refs']=list(dict.fromkeys(basis['source_refs']+['U004']))
policy['operations'].append({'id':'withdraw','root':'withdraw_allowed','business_nodes':['withdraw_file'],
    'cases':[],'source_refs':['U004']})
write('discovery.json',doc)
print(json.dumps({'valid':True,'requirements':['R_WITHDRAW','R_ACCESS'],'answers':'simulated and explicit','business_code_changed':False}))
