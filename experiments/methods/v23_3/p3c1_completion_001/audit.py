"""Offline completion audit. Reads archived outputs; never invokes generation or environments."""
import json
import random
import re
from collections import Counter
from pathlib import Path
from experiments.methods.v23_3.p3c1_r05_replay_001 import run as original
from experiments.methods.v23_3.p3c1_r05_replay_restart_004 import run as final
from experiments.methods.v23_3.p3c1_r05_replay_001.select_train import FAMILIES
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.replay import verify_pair
from src.skill_evolution.v23 import editor

ROOT=original.ROOT
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
read=lambda p: json.loads(resolve(Path(p)).read_text())
from experiments.methods.v23_3.archive_io import archive_glob, load_saved, resolve

def save(name,value):
    (resolve(HERE/name)).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    final.verify()
    upstream=original.upstreams()
    editors={a:load_saved(editor.load_editor, original.HERE / 'editors' / a, expected_preconditioner=upstream[a]) for a in ['A','B']}
    inputs={a:read(original.HERE/'editors'/a/'input.json') for a in ['A','B']}
    differing=[k for k in inputs['A'] if inputs['A'][k]!=inputs['B'][k]]
    assert differing==['plan'],differing
    requests={a:read(original.HERE/f'editors/{a}/http/001/request.json') for a in ['A','B']}
    assert {k:v for k,v in requests['A']['body'].items() if k!='messages'} == {k:v for k,v in requests['B']['body'].items() if k!='messages'}
    assert requests['A']['timeout']==requests['B']['timeout']==[60,300]
    assert requests['A']['body']['messages'][0]==requests['B']['body']['messages'][0]
    save('editor_audit.json',{'valid_candidates':{a:editors[a]['editor_status'] for a in editors},'differing_input_fields':differing,'request_top_level_keys':{a:list(v) for a,v in requests.items()},'adjustment_counts':{a:len(upstream[a]['preconditioner']['adjustments']) for a in editors},'update_texts':{a:upstream[a]['effective_plan']['updates'] for a in editors},'original_plan':upstream['B']['effective_plan']})
    latest=read(final.HERE/'analysis.json');selected={};rows=[];trace_md=['# 最终选定轨迹索引与逐步执行证据','', '仅列真实执行动作及环境反馈，不转录模型思维文本。各任务首次正常结束的轨迹用于最终比较；中断前缀只计成本。','']
    for row in latest['rows']:
        key=(row['condition'],row['ref']);r=read(row['source']);a=verify_record(r)
        assert a['trace_valid'] and a['episode_complete'];selected[key]=r
        steps=[s for s in r['steps'] if s['phase']=='executed'];visits=[];revisits=[];seen=set()
        for s in steps:
            if s['action'].startswith('go to '):
                loc=s['action'][6:];visits.append(loc);pair=(loc,s['observation'])
                if pair in seen:revisits.append(s['step'])
                seen.add(pair)
        locations=list(dict.fromkeys(visits));classes=list(dict.fromkeys(re.sub(r' \d+$','',x) for x in locations))
        rows.append({'condition':key[0],'ref':key[1],'source':row['source'],**a,'navigation_count':len(visits),'locations':locations,'location_count':len(locations),'location_classes':classes,'same_location_observation_repeat_steps':revisits,'opened':[{'step':s['step'],'action':s['action']} for s in steps if s['action'].startswith('open ')],'invalid_steps':[s['step'] for s in steps if not s['action_in_admissible_commands']],'nothing_happens_steps':[s['step'] for s in steps if s['observation'].strip()=='Nothing happens.'],'fallback_steps':[s['step'] for s in steps if s.get('fallback')],'key_actions':[{'step':s['step'],'action':s['action']} for s in steps if s['action'].split()[0] in {'take','clean','cool','heat','move','use'}]})
        trace_md += [f'## {key[0]} {key[1]}','',f"[原始 trajectory.json]({row['source']})；{r['status']}，{a['steps_executed']} 步。",'',f"任务：{r['goal']}",'','| 步 | 实际动作 | 环境反馈 |','|---|---|---|']
        trace_md += [f"| {s['step']} | `{s['action'] if s['action_in_admissible_commands'] else '[投影含额外文本的非法动作，详见原轨迹]'}` | {s['observation'].replace(chr(10),' ').replace('|',' / ')} |" for s in steps];trace_md+=['']
    # Specific observations used in prose; neither hidden game state nor model rationale is inferred.
    b7=selected[('B','P7')];u8=b7['steps'][7]['messages'][-1]['content']
    assert 'Observation 6:' in u8 and 'Observation 7:' in u8 and 'Observation 1:' not in u8
    assert 'go to countertop 4' in b7['steps'][7]['admissible_commands']
    b10=selected[('B','P10')]['steps'][1];content=b10['model_response']['content']
    assert content.count('<action>')==2 and content.count('</action>')==1
    assert 'open fridge 1' in b10['admissible_commands'] and not b10['action_in_admissible_commands']
    for arm in ['Parent','A','B']:
        r=selected[(arm,'P7')]
        assert 'countertop 4' in r['initial_observation']
        assert not any(s.get('action')=='go to countertop 4' for s in r['steps'])
        assert not any('butterknife' in s['observation'].lower() for s in r['steps'] if s['phase']=='executed')
    save('specific_observations.json',{'B_P7_step8_history_observations':[6,7],'B_P7_step8_countertop4_admissible':True,'P7_all_arms_countertop4_visible_but_unvisited':True,'P7_exact_target_absent_from_executed_feedback_not_proof_of_environment_absence':True,'B_P10_step2_action_tag_counts':[2,1],'B_P10_step2_open_fridge_admissible':True})
    pairs=[]
    for ref in ['P3','P6','P7','P10']:
        for a,b in [('Parent','A'),('Parent','B'),('A','B')]:
            p,q=selected[(a,ref)],selected[(b,ref)];verify_pair(p,q)
            assert p['request_policy']==q['request_policy']
            assert p['implementation']['files']==q['implementation']['files']
            pairs.append([ref,a,b])
    paths=sorted(p for d in archive_glob(BASE, 'p3c1_r05_replay*') if resolve(d).is_dir() for p in archive_glob(d, 'trajectory.json', recursive=True))
    attempts=[];cost=Counter();completed={}
    for p in paths:
        r=read(p);a=verify_record(r);assert a['trace_valid'];condition=p.parts[-3];ref=p.parts[-2]
        attempts.append({'source':str(p),'condition':condition,'ref':ref,'started_at':r['started_at'],**a,'error_type':r.get('error_type')})
        cost.update(a['reported_usage']);cost['episodes']+=1;cost['actor_decisions']+=a['requests_recorded'];cost['actor_transport_attempts']+=a['transport_attempts_recorded'];cost['executed_actions_all_attempts']+=a['steps_executed'];cost['complete']+=a['episode_complete'];cost['unknown_usage_attempts']+=a['transport_attempts_with_unknown_usage']
        for s in r['steps']:
            response=s.get('model_response') or {};u=response.get('usage') or {}
            cost['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
            cost['http_429']+=sum(t.get('http_status')==429 for t in s.get('transport_attempts',[]))
        if a['episode_complete']:completed.setdefault((condition,ref),[]).append((r['started_at'],str(p)))
    for row in rows:assert min(completed[(row['condition'],row['ref'])])[1]==row['source']
    actor_cost=dict(cost)
    for arm in ['A','B']:
        response=read(original.HERE/f'editors/{arm}/response.json');u=response['usage'];cost.update({k:u[k] for k in ['prompt_tokens','completion_tokens','total_tokens']});cost['reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
    cost['editor_calls']=2;cost['total_client_transport_attempts']=cost['actor_transport_attempts']+2
    for k in ['episodes','prompt_tokens','completion_tokens','total_tokens','reasoning_tokens','http_429','unknown_usage_attempts']:assert cost[k]==latest['cumulative_including_editors'][k],(k,cost[k])
    assert cost['actor_decisions']==480 and cost['actor_decisions']<=600 and cost['complete']==12
    save('costs.json',{'actor_only':actor_cost,'including_editors':dict(cost),'currency_cost':None,'reasoning_is_subset_of_completion':True,'unknown_usage_is_not_zero':True,'selected_executed_actions':sum(r['steps_executed'] for r in rows),'attempts':attempts})
    train=read(original.HERE/'new_train_cases.json');ex=read(original.HERE/'new_train_exclusions.json');excluded={x['identity'] for x in ex};data=Path(train['source_root']);pool=sorted(archive_glob(data, '*/*/game.tw-pddl'));eligible={f:[] for f in FAMILIES}
    for p in pool:
        family=p.parent.parent.name.split('-')[0]
        if p.parent.name not in excluded and family in eligible:eligible[family].append(p)
    rng=random.Random(train['seed']);chosen=[]
    for f in FAMILIES:
        for batch,p in enumerate(rng.sample(eligible[f],2),1):chosen.append((batch,f,str(p.relative_to(data.parent.parent))))
    actual=[(x['batch'],x['task_type'],x['gamefile']) for x in train['tasks']]
    assert sorted(chosen)==sorted(actual);assert len({x['instance'] for x in train['tasks']})==12
    assert all(train['frozen_at']<read(original.HERE/f'editors/{a}/run.json')['started_at'] for a in ['A','B'])
    save('train_preregistration_check.json',{'original_frozen_at':train['frozen_at'],'same_selection_reproduced':True,'raw_train_count':len(pool),'excluded_count':len(excluded),'task_count':12,'unique_instances':12,'before_both_editors':True,'used_frozen_exclusions_not_posthoc_rescreening':True,'read_game_contents':False,'new_case_execution':False,'exposure_screening_limit':'Original scan read 131072-byte prefixes; aliases, unscanned tails and external exposure cannot be excluded.'})
    mem=read(BASE/'memory_v3_integration_001/config/model_input.json')['memory'];refs={'M3':['S1_R02/diff','S1_R02/P5','S1_R02/Q5','S1_R02/Q4','S1_R02/Q6'],'M6':['S1_R03/diff','S1_R03/P2','S1_R03/Q2','S1_R03/P4','S1_R03/Q4','S1_R03/P6','S1_R03/Q6'],'M8':['S1_R03/diff','S1_R04/diff','S1_R03/P5','S1_R03/Q5','S1_R03/P10','S1_R03/Q10','S1_R04/P1','S1_R04/Q1']}
    save('historical_evidence.json',{'source':'../memory_v3_integration_001/config/model_input.json','entries':[e for e in mem['entries'] if e['id'] in refs],'sources':{r:mem['sources'][r] for r in sorted(set(r for v in refs.values() for r in v))}})
    save('evidence.json',{'rows':rows,'paired_checks':pairs,'cost_scope':'Selected complete trajectories for behavior; all 25 attempts for cost.'})
    (resolve(HERE/'TRAJECTORY_EVIDENCE.md')).write_text('\n'.join(trace_md))
    save('validation.json',{'freeze_chain_verified':True,'editor_strict_reapplication_valid':True,'selected_complete':len(rows),'all_archived_attempts_trace_valid':len(attempts),'pair_checks':len(pairs),'first_complete_selection_verified':True,'train_selection_reproduced':True,'new_model_calls':0,'new_environment_runs':0})
    print(json.dumps({'rows':[{k:r[k] for k in ['condition','ref','steps_executed','location_count','location_classes','same_location_observation_repeat_steps','invalid_steps']} for r in rows],'cost':dict(cost)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
