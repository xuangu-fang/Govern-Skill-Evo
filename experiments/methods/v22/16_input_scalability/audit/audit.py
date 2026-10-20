#!/usr/bin/env python3
"""Read-only archived-message audit. Writes only sibling results/notes. No API/environment.

Character counts are Unicode codepoints in compact ensure_ascii=False JSON, not tokens.
Only provider-reported prompt_tokens are labelled actual tokens. Reused call files are
identified by original call start time; they are never counted as new model calls.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
ART = ROOT / 'artifacts/methods/v22'
REV = ROOT / 'experiments/methods/v22/12_contract_alignment/revision'

def compact(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def size(x): return len(compact(x))
def read(p): return json.loads(p.read_text())
def stamp(p): return {'path': str(p.relative_to(ROOT)), 'sha256': sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
def artifact(p): return ART / p

def leaves(x, path='$'):
    if isinstance(x, dict):
        for k,v in x.items(): yield from leaves(v, path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from leaves(v,path+f'[{i}]')
    elif isinstance(x,str): yield path,x

def repeated_strings(payload):
    occurrences = defaultdict(list)
    for path,text in leaves(payload):
        if len(text)>=80: occurrences[text].append(path)
    rows=[]
    for text,paths in occurrences.items():
        if len(paths)>1:
            rows.append({'sha256':sha256(text.encode()).hexdigest(),'string_chars':len(text),'occurrences':len(paths),
                         'duplicate_literal_chars':len(text)*(len(paths)-1),'example_paths':paths[:5]})
    rows.sort(key=lambda x:x['duplicate_literal_chars'], reverse=True)
    return {'minimum_string_chars':80,'duplicate_literal_chars':sum(x['duplicate_literal_chars'] for x in rows),
            'unique_repeated_strings':len(rows),'largest':rows[:12],
            'warning':'Potential exact string interning only; not realized savings, reference overhead excluded. Same string does not collapse distinct events.'}

def run_stats(payload):
    runs=list(payload.get('runs',{}).values()) or payload.get('experiences',[])
    events=[event for run in runs for event in run.get('steps',[])]
    observations=[run.get('initial_observation','') for run in runs]+[event.get('observation','') for event in events]
    metadata=[{k:v for k,v in run.items() if k not in ['steps','initial_observation']} for run in runs]
    commands=payload.get('command_sets',{})
    flat=[c for cs in commands.values() for c in cs]
    sources=payload.get('sources',{})
    kinds=defaultdict(dict)
    for ref,source in sources.items(): kinds[source.get('kind','unknown')][ref]=source
    return {'run_count':len(runs),'step_count':len(events),'step_objects_chars':size(events),
            'observations_literal_chars':sum(map(len,observations)), 'observation_unique_count':len(set(observations)),
            'observation_count':len(observations),'duplicate_observation_literal_chars':sum(map(len,observations))-sum(map(len,set(observations))),
            'run_metadata_chars':size(metadata),'command_set_count':len(commands),
            'command_entry_count':len(flat),'unique_command_strings':len(set(flat)),
            'command_literal_chars':sum(map(len,flat)),'unique_command_literal_chars':sum(map(len,set(flat))),
            'source_count':len(sources),'source_kind_chars':{k:size(v) for k,v in kinds.items()},
            'source_kind_count':{k:len(v) for k,v in kinds.items()}}

def history_stats(payload):
    effects=payload.get('memory',[])
    basis=[b for e in effects for b in e.get('basis',[])]
    acts=[b['actual_update'] for b in basis if 'actual_update' in b]
    encoded=[compact(a) for a in acts]
    return {'effect_count':len(effects),'basis_count':len(basis),'limits_count':sum(len(e.get('limits',[])) for e in effects),
            'historical_source_count':len(payload.get('historical_sources',{})),
            'context_count':len(payload.get('historical_contexts',{})),
            'history_field_chars':sum(size(payload.get(k,{} if k!='memory' else [])) for k in ['memory','historical_sources','historical_contexts','historical_updates'] if k in payload),
            'memory_basis_chars':sum(size(e.get('basis',[])) for e in effects),
            'memory_claim_limit_chars':sum(size({k:e.get(k) for k in ['claim','limits']}) for e in effects),
            'basis_actual_update_chars':sum(map(len,encoded)),
            'exact_duplicate_actual_update_chars':sum(map(len,encoded))-sum(map(len,set(encoded)))}

def get_messages(call_path):
    round_dir=call_path.parent.parent
    message_path=round_dir/'messages'/call_path.name
    if not message_path.exists(): message_path=round_dir/'messages.json'
    return message_path

def analyse(label,call_path,*,role='effective',note=''):
    call=read(call_path);message_path=get_messages(call_path);messages=read(message_path)
    payload=json.loads(messages[-1]['content'])
    attempts=[a for s in call['steps'] for a in s.get('transport_attempts',[])]
    response=call['steps'][-1].get('model_response',{})
    usage=response.get('usage',{})
    grouping=payload.get('grouping'); update=payload.get('update_context',{})
    grouping_copies=[path for path,value in walk_objects(payload) if grouping is not None and value==grouping]
    row={'label':label,'role':role,'note':note,'message_artifact':stamp(message_path),'call_artifact':stamp(call_path),
         'recorded_model':call.get('model'),'call_started_at':call.get('started_at'),'call_status':call.get('status'),
         'finish_reason':response.get('finish_reason'),'request_parameters':attempts[-1].get('request_parameters') if attempts else None,
         'actual_provider_usage':usage,'actual_usage_semantics':'Provider reported; no char-to-token conversion.',
         'system_prompt_chars':sum(len(m['content']) for m in messages if m['role']=='system'),
         'user_content_chars':sum(len(m['content']) for m in messages if m['role']=='user'),
         'all_content_chars':sum(len(m['content']) for m in messages),
         'compact_json_messages_chars':size(messages),
         'within_400000_char_limit':size(messages)<=400000,
         'field_chars':{k:size(v) for k,v in payload.items()},
         'field_chars_note':'Each value separately compact-serialized. Keys/separators and outer-message escaping are excluded, so columns are not an additive decomposition of envelope.',
         'run_stats':run_stats(payload),'history_stats':history_stats(payload),
         'duplication':{'exact_grouping_copies':grouping_copies,'exact_grouping_duplicate_chars':max(0,len(grouping_copies)-1)*size(grouping) if grouping else 0,
                        'current_run_facts_chars':size(payload.get('current_run_facts',{})) if 'current_run_facts' in payload else 0,
                        'repeated_strings':repeated_strings(payload)},
         'call_embeds_equal_messages':all(s.get('messages')==messages for s in call['steps']),
         'recorded_messages_sha256':call.get('messages_sha256'),
         'compact_messages_sha256':sha256(compact(messages).encode()).hexdigest(),
         'canonical_messages_sha256':sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    row['subfield_chars']={k:{kk:size(vv) for kk,vv in payload[k].items()} for k in ['parent','candidate','plan','grouping','update_context','base_protocol'] if isinstance(payload.get(k),dict)}
    row['sample_profile']=payload.get('update_profile','v22.grouped_update.v1' if label.startswith('08') else 'classifier-independent')
    return row

def walk_objects(x,path='$'):
    if isinstance(x,(dict,list)):
        yield path,x
        values=x.items() if isinstance(x,dict) else enumerate(x)
        for k,v in values: yield from walk_objects(v,path+'.'+str(k))

def main():
    calls=[]
    r1=artifact('08_grouped_continual_live_20261015/rounds/r1')
    r2=artifact('08_grouped_continual_fusion_resumed_20261015/rounds/r2')
    for stage in ['classification','diagnosis','main_editor','post_gate_learning']:
        calls.append(analyse('08_r1_'+stage,r1/'calls'/f'{stage}.json'))
    for stage in ['classification','diagnosis','fusion','main_editor']:
        calls.append(analyse('08_r2_'+stage,r2/'calls'/f'{stage}.json',note='Original successful call copied into resumed archive; counted once.'))
    calls.append(analyse('08_r2_post_gate_learning',artifact('08_grouped_continual_memory_recovered_20261015/calls/post_gate_learning.json'),note='Authorized recovery uses byte-identical messages to failed learning request; higher output budget.'))
    for label,path,note in [
        ('08_r2_classification_failed','08_grouped_continual_live_20261015/rounds/r2/calls/classification.json','Output length stop; not input overrun.'),
        ('08_r2_fusion_failed','08_grouped_continual_recovered_20261015/rounds/r2/calls/fusion.json','Returned response rejected downstream; not input overrun.'),
        ('08_r2_learning_failed','08_grouped_continual_fusion_resumed_20261015/rounds/r2/calls/post_gate_learning.json','Output max_tokens=16384 exhausted; reasoning consumes14913; not input overrun.')]:
        calls.append(analyse(label,artifact(path),role='failed',note=note))
    for stage in ['classification','diagnosis','main_editor']:
        calls.append(analyse('15_r1_'+stage,artifact('15_unified_dsc_v3_editor_recovery_live_20261016/rounds/r1/calls/'+stage+'.json'),
                             role='supplement', note='Classification and Diagnosis are reused accepted upstream records; Editor is third actual failed attempt. No new Candidate/Replay exists.'))
    files=['grouped_update.py','grouped_representation.py','compact_learning.py','compact_learning_view.py','effective_memory.py','compact_cycle.py','continual_runner.py']
    sources=[stamp(REV/'src/skill_evolution/v22'/f) for f in files]
    checks={r['label']:{'matches_call_messages':r['call_embeds_equal_messages'],'message_hash_matches':r['recorded_messages_sha256']==r['canonical_messages_sha256']} for r in calls}
    by={r['label']:r for r in calls}
    assert by['08_r1_post_gate_learning']['compact_json_messages_chars']==298551
    assert by['08_r2_post_gate_learning']['compact_json_messages_chars']==398816
    assert by['08_r2_post_gate_learning']['compact_messages_sha256']==by['08_r2_learning_failed']['compact_messages_sha256']
    result={'schema':'v22.input_audit.v1','boundary':'Read-only actual archives, no API or ALFWorld. 08 observations are old grouped_update.v1, not v3 measurements. 15 contains true v3 Diagnosis/Editor inputs, but inherited classifier.','character_definition':'Unicode codepoints; json.dumps(ensure_ascii=False,separators=(comma,colon)); not UTF8 bytes and not tokens.',
            'stages':calls,'sources':sources,'checks':checks,'program_identity':{'08_r1_fusion':'Empty Memory => program identity; no model message or service tokens.'},
            'historical_representation_warning':'08 actual_update is repeated in basis; current v3 shares historical_updates by context. Do not generalize 08 historical redundancy directly to v3.'}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# Archived input cost audit','',result['boundary'],'','All numbers are read from frozen messages and provider usage; no API/environment executed.','',
           '| Archive/stage | System chars | User chars | Compact messages chars | Actual input tokens | Runs / steps | History fields chars |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in calls:
        lines.append('| '+r['label']+' | '+ ' | '.join(str(v) for v in [r['system_prompt_chars'],r['user_content_chars'],r['compact_json_messages_chars'],r['actual_provider_usage'].get('prompt_tokens'),str(r['run_stats']['run_count'])+' / '+str(r['run_stats']['step_count']),r['history_stats']['history_field_chars']])+' |')
    lines+=['','R1 Fusion is program identity, not a semantic call. R2 learning recovery is byte-identical in messages to failed request; failure was output truncation (16,384 limit), not input overflow.',
            '','## Key repeated/oversized inputs',
            '- The same ordered full Parent runs and complete command sets go to Diagnosis, Fusion, and Editor; current v3 still routes the same effective_consumption_payload to Fusion and Editor. This is role redundancy, not necessarily same-message duplicate content.',
            '- Learning repeats grouping at root and update_context.grouping, and source group snapshots expand member execution identities again. Event source directory repeats run/step already encoded in aliases.',
            '- current_run_facts repeats run identities/status plus useful deterministic counts; a compact view can share identity fields without removing counts.',
            '- command_sets deduplicates identical complete lists, but repeated command strings appear across distinct lists. Literal string interning can preserve every action opportunity.',
            '- Full ordered observation/action evidence is retained; repeated observation strings can be interned without merging events or dropping timestamps/step order.',
            '- In 08 Memory, actual_update is repeated per basis. v3 already shares it under historical_updates, but all retained basis sources and all history updates are still consumed each time.',
            '','## Existing experiment scope restriction',
            'The current v3 learning builder requires split=train and purpose=learning (compact_learning.py:56-57), and classification requires train: task IDs (grouped_representation.py:72). Input capacity alone does not authorize Train+Selection mixing; do not relabel Selection as Train to bypass this protocol.',
            '','## Source references',
            '- grouped_update.py:90-101 update_payload shares current evidence; :164-195 _unified_messages uses full effective view for Fusion/Editor/Learning.',
            '- grouped_representation.py:34-96 classifier keeps ordered actions/observations and complete shared command lists; :155-185 grouping is copied and expanded into sources.',
            '- compact_learning.py:22-95 all paired current trajectories; :98-127 source resolver; :130-166 response provenance closure.',
            '- effective_memory.py:53-128 all active Effect/basis consumed; :188-242 inherited basis/limits; no consumption length bound.',
            '- compact_learning_view.py:70-132 shares historical sources and removes command lists/fingerprints. Important: historical action opportunity cannot be inferred from omitted command candidates.',
            '- continual_runner.py:211-214 400k-like plan budget checked only after per-stage input is assembled; no automatic shortening.',
            '','results.json contains SHA256 and exact artifact paths, field/subfield decomposition, run/command/source counts, exact duplicated string estimates and call-message integrity checks.',
            'Repeated-string potential is not measured net savings: reference/schema overhead must be accounted for in a separate prototype. Actual output-token anomalies (e.g. R1 provider completion above requested max) are retained as provider data rather than silently corrected.']
    (OUT/'notes.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'stages':len(calls),'all_embedded_messages_match':all(r['call_embeds_equal_messages'] for r in calls),'all_message_hashes_match':all(v['message_hash_matches'] for v in checks.values()),'results':str(OUT/'results.json')},ensure_ascii=False))

if __name__=='__main__':main()
