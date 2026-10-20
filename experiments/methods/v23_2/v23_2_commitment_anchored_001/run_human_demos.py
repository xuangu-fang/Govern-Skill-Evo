"""Persist human test demonstrations, with network disabled; not live model runs."""
from pathlib import Path
import sys,json,socket
from copy import deepcopy
import anchored
E=Path(__file__).resolve().parent
attempts=[]
def deny(*a,**k):attempts.append(1);raise AssertionError('offline only')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
bad=anchored.load_json(E/'fixtures/single_replace.json');bad['edits'][0]['anchor_text']='intentionally missing anchor'
(E/'fixtures/rejected_missing.json').write_text(json.dumps(bad,indent=2)+'\n')
results=[]
for name in ('single_replace','target_supporting','large_replace','semantic_risk','keep','need_evidence','rejected_missing'):
 out=E/'results/human_runs'/name
 sys.argv=['anchored.py','--payload',str(E/'fixtures/payload.json'),'--proposal',str(E/f'fixtures/{name}.json'),'--out',str(out)]
 code=0
 try:anchored.main()
 except SystemExit as exc:code=exc.code
 receipt=anchored.load_json(out/'receipt.json')
 if name=='rejected_missing':assert code==2 and not (out/'effective_plan.json').exists()
 else:assert code==0
 results.append({'fixture':name,'kind':'HUMAN_TEST_NOT_MODEL_OUTPUT','exit_code':code,'receipt':receipt})
assert not attempts
(E/'results/human_demos.json').write_text(json.dumps({'demos':results,'network_attempts':0,'new_model_calls':0,'not_a_real_candidate':True},indent=2)+'\n')
print(json.dumps({'human_demos':len(results),'expected_rejections':1,'model_calls':0}))
