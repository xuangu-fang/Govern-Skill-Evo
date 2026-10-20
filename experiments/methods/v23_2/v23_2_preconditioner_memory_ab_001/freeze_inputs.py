"""P3-A offline preparation only: no stage runner or API generator invocation."""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch

from dotenv import dotenv_values
from src.skill_evolution.v23 import preconditioner as pc, memory, evolution as ev, grouping, prompts
from src.skill_evolution.v23.model_routing import route_call_config
from src.skill_evolution.v23_2 import local_validation as local

ROOT=Path(__file__).resolve().parents[4]
EXP=Path(__file__).resolve().parent
S=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
D=ROOT/'artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001'
DP=ROOT/'experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/diagnosis_prompt.md'

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,x):
    with p.open('x') as f: json.dump(x,f,ensure_ascii=False,indent=2); f.write('\n')

def freeze():
    assert not (EXP/'config/input_manifest.json').exists(), 'Frozen inputs cannot be overwritten'
    saved=local.load_attempt(D,prompt_path=DP)
    raw_diag=read(D/'diagnosis.json')
    assert saved['diagnosis']==raw_diag and raw_diag['decision']=='revise'
    ri=read(S/'rounds/R05/round_input.json')
    olddir=S/'rounds/R05/preconditioner/attempts/001'
    original=read(olddir/'input.json')
    active=S/ri['state']['active_memory']
    hist=memory.load_memory(active)
    assert hist==ri['memory']==original['memory']==json.loads(read(olddir/'request.json')['body']['messages'][1]['content'])['memory']
    assert [e['id'] for e in hist['entries']]==['M1','M2','M3','M6','M7','M8','M9']
    assert read(olddir/'http_status.json')['status_code']==200 and read(olddir/'run.json')['status']=='valid'
    assert saved['facts']==original['facts'] and saved['background']==original['background']
    assert saved['grouping']==original['grouping']
    contract=read(S/'contract.json')
    for p in sorted((S/'recoveries').glob('*.json')): contract.update(read(p).get('contract_changes',{}))
    for p in [pc.PROMPT_PATH,prompts.CONTEXT_PATH]:
        assert p.read_text()==contract[str(p.relative_to(ROOT))]
        (EXP/'config'/p.name).write_bytes(p.read_bytes())
    (EXP/'config/original_diagnosis.json').write_bytes((D/'diagnosis.json').read_bytes())
    save(EXP/'config/original_plan.json',raw_diag['plan'])
    save(EXP/'config/background.json',saved['background'])
    save(EXP/'config/memory_A.json',memory.empty_memory())
    save(EXP/'config/memory_B.json',hist)
    save(EXP/'config/active_index.json',read(active/'active.json'))
    inherited=read(D/'run.json')['call_config']
    env=dotenv_values(ROOT/'.env')
    base=os.environ.get('OPENAI_BASE_URL') or env.get('OPENAI_BASE_URL')
    assert base, 'No configured endpoint'
    cfg=route_call_config(inherited,base)
    assert cfg==grouping.call_configuration(base_url=base,model=inherited['model'],max_tokens=inherited['max_tokens'],timeout=inherited['timeout_seconds'])
    limits=read(ROOT/'experiments/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/config/freeze.json')['config']
    config={'call_config':cfg,'historical_call_config':inherited,'route_source':'environment' if os.environ.get('OPENAI_BASE_URL') else '.env',
            'credential_present':bool(os.environ.get('OPENAI_API_KEY') or env.get('OPENAI_API_KEY')),
            'max_input_chars':limits['max_input_chars'],'max_message_utf8_bytes':limits['max_message_utf8_bytes'],
            'future_logical_calls_per_arm':1,'future_automatic_retries':0,'execution_authorized':False,
            'http_connect_timeout_seconds':10,'http_read_timeout_seconds':cfg['timeout_seconds'],'allow_redirects':False,
            'trust_env_for_proxy':False,'model_context_limit_verified':None,'provider_tokenizer_available':False,
            'tiktoken_proxy_available':False,'context_readiness':'unverified_for_current_proxy_model',
            'future_entry':'grouping.live_generator single HTTP request + existing parse/compile; not local.run_stage auto retry'}
    save(EXP/'config/call_config.json',config)
    evidence=[]
    for rnd in ['R04','R05','R06']:
        stage=S/f'rounds/{rnd}/preconditioner';p=stage/read(stage/'result.json')['path']
        meta=read(p/'run.json');usage=read(p/'response.json')['usage'];n=usage['prompt_tokens']
        evidence.append({'round':rnd,'path':str(p),'chars':meta['input_chars'],'prompt_tokens_reported':n,
                         'ratio':n/meta['input_chars'],'model':meta['call_config']['model'],'endpoint':meta['call_config']['endpoint']})
    payloads={};requests={};sizes={};tests=[]
    for arm,mem in [('A',memory.empty_memory()),('B',hist)]:
        view={**saved,'memory':mem}
        msgs=pc.messages_for(view)
        assert local.messages_for('preconditioner',view)==msgs
        payload=pc.preconditioner_input(view)
        assert json.loads(msgs[1]['content'])==payload
        assert payload['plan']==raw_diag['plan']
        assert [r['ref'] for r in payload['runs']]==['P1','P3','P6','P7','P8','P10']
        memory.validate_memory(mem)
        # Keep/stop/identity are structural fixtures only, never experimental results.
        keep={'decision':'ready','reason':'Offline contract fixture.','adjustments':[],'checks':None}
        result=pc.compile_effective_plan(keep,payload)
        assert result['goal']==raw_diag['plan']['goal']
        assert [(u['id'],u['text']) for u in result['updates']]==[(u['id'],u['text']) for u in raw_diag['plan']['updates']]
        assert result['checks']==raw_diag['plan']['checks']
        assert pc.compile_effective_plan({'decision':'need_evidence','reason':'Offline fixture.','adjustments':[],'checks':None},payload) is None
        withdraw={'decision':'no_change','reason':'Offline fixture.','adjustments':[{'from':['u1','u2'],'to':[],'basis':['P3:8'],'reason':'Offline fixture.'}],'checks':[]}
        assert pc.compile_effective_plan(withdraw,payload) is None
        identity={'decision':'ready','reason':'Offline fixture.','adjustments':[{'from':['u1'],'to':[{'id':'u1','text':raw_diag['plan']['updates'][0]['text']}],'basis':['P3:8'],'reason':'Offline fixture.'}],'checks':None}
        assert pc.compile_effective_plan(identity,payload)['goal']==raw_diag['plan']['goal']
        identity['adjustments'][0]['basis']=['M6']
        if arm=='B': pc.compile_effective_plan(identity,payload)
        else:
            try: pc.compile_effective_plan(identity,payload)
            except ValueError: pass
            else: raise AssertionError('Empty arm accepted absent M6')
        tests.append({'arm':arm,'keep_stop_withdraw_identity_contracts':True,'memory_reference_validation':True})
        # Reuse saved real HTTP envelope and exact real message assembler.
        req=deepcopy(read(olddir/'request.json'))
        req['endpoint']=cfg['endpoint'];req['timeout_seconds']=cfg['timeout_seconds'];req['attempts']=1
        for k in req['body']:
            req['body'][k]=msgs if k=='messages' else cfg[k]
        assert set(req['body'])=={'model','messages','max_tokens','temperature','reasoning_effort','thinking','stream'}
        save(EXP/f'requests/{arm}_UNSENT.json',req)
        payloads[arm]=payload;requests[arm]=req
        enc=json.dumps(msgs,ensure_ascii=False);n=len(enc)
        sizes[arm]={'message_chars':n,'message_utf8_bytes':len(enc.encode()),'request_file_bytes':(EXP/f'requests/{arm}_UNSENT.json').stat().st_size,
                    'estimate_method':'historical reported prompt tokens / serialized message chars, same data format, different current route; not model tokenizer or bound',
                    'estimated_input_tokens_range':[round(n*min(e['ratio'] for e in evidence)),round(n*max(e['ratio'] for e in evidence))]}
        sizes[arm]['estimated_with_max_output_range']=[t+cfg['max_tokens'] for t in sizes[arm]['estimated_input_tokens_range']]
        assert n<=config['max_input_chars'] and sizes[arm]['message_utf8_bytes']<=config['max_message_utf8_bytes']
    a,b=deepcopy(payloads['A']),deepcopy(payloads['B'])
    a.pop('memory');b.pop('memory');assert a==b
    ar,br=deepcopy(requests['A']),deepcopy(requests['B'])
    ar['body']['messages'][1]['content']=a;br['body']['messages'][1]['content']=b
    assert ar==br
    save(EXP/'config/common_payload_without_memory.json',a)
    save(EXP/'config/system_message.json',requests['A']['body']['messages'][0])
    save(EXP/'results/input_checks.json',{'only_semantic_difference':'body.messages[1].content (JSON)/memory',
         'same_non_memory_payload':True,'same_system':True,'same_call_config':True,'same_original_plan':True,
         'empty_memory_valid':True,'historical_memory_exact':True,'selected_runs':[r['ref'] for r in a['runs']],
         'selected_groups':[g['group_id'] for g in a['grouping']['groups']], 'command_sets':len(a['command_sets']),
         'no_hidden_selection_change':True,'prompt_equals_formal_frozen':True,'context_equals_formal_frozen':True,
         'offline_compiler_fixtures':tests,'no_real_responses':True,'network_blocked':True,'model_calls':0,'tokens_consumed':0,'environment_calls':0})
    save(EXP/'results/capacity.json',{'arms':sizes,'historical_usage_basis':evidence,'character_byte_limits_pass':True,
                                   'exact_tokens':None,'current_model_context_fit':None,'price_verified':False,'actual_api_cost':0})
    source_paths=[D/n for n in ['diagnosis.json','input.json','messages.json','request.json','response.json','run.json','validation.json']]
    source_paths += [olddir/n for n in ['input.json','request.json','response.json','run.json']]
    source_paths += [active/'active.json',S/'rounds/R05/round_input.json',DP]
    source_paths += [active/'archive'/f'{cid}.json' for cid in read(active/'active.json')['commits']]
    source_paths += list((ROOT/'src/skill_evolution/v23').glob('*.py'))+[pc.PROMPT_PATH,prompts.CONTEXT_PATH,Path(local.__file__)]
    save(EXP/'config/source_hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in source_paths})
    # Actual current record references, not historical facts relabelled as current.
    fact_sources=saved.get('sources')
    save(EXP/'config/evidence_index.json',{'selected_runs':[{'ref':r['ref'],'task':r['task'],'steps':len(r['steps']),
          'outcome':r['outcome'],'canonical_sha256':canonical(r)} for r in a['runs']],
          'grouping_ids':[g['group_id'] for g in a['grouping']['groups']], 'plan_basis':{u['id']:u['basis'] for u in raw_diag['plan']['updates']},
          'source_index_from_saved':fact_sources,'raw_records_index':str(ROOT/'experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/run_evidence_index.json'),
          'omitted_full_runs':['P2','P4','P5','P9'],'future_optional_condition_only':'six runs + P2 + P4; NOT constructed here'})
    save(EXP/'config/memory_source_index.json',[{'id':e['id'],'knowledge':e['knowledge'],'evidence':e['evidence'],
         'source_keys':list(dict.fromkeys(ref if ref.endswith('/diff') else ref.split(':')[0] for ref in e['evidence']))} for e in hist['entries']])
    files=[p for sub in ['requests','config','results'] for p in (EXP/sub).glob('*') if p.name not in ['protected_before.json','git_diff_before.patch','git_status_before.txt']]
    save(EXP/'config/input_manifest.json',{'frozen_at':ev.now(),'sent':False,'responses':None,
         'original_diagnosis_path':str(D/'diagnosis.json'),'original_diagnosis_file_sha256':sha(D/'diagnosis.json'),
         'original_plan_canonical_sha256':canonical(raw_diag['plan']),'memory_B_canonical_sha256':canonical(hist),
         'common_payload_canonical_sha256':canonical(a),'files_sha256':{str(p.relative_to(EXP)):sha(p) for p in files},
         'offline_control_status':'passed','execution_readiness':'pending_current_model_context_verification',
         'model_calls':0,'environment_calls':0})
    print(json.dumps({'sizes':sizes,'config':config,'controls':'passed'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('P3-A: network prohibited')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('P3-A: network prohibited')):
        freeze()
