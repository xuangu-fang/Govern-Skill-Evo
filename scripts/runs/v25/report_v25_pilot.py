#!/usr/bin/env python3
"""Summarize saved pilot records without executing tasks or requesting models."""
import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmarks.spreadsheetbench.facts import build_facts
from scripts.runs.v25.continue_v25_pilot import PilotAdapter


def summarize(pilot):
    pilot=Path(pilot).resolve();root=pilot/'campaign';cfg=ev.read(root/'config.json');tasks=cfg['batches'][0]
    change_path=root/'pilot_budget_change/change.json'
    change=ev.read(change_path) if change_path.exists() else None
    facts_builder=PilotAdapter(change).build_facts if change else build_facts
    rd=root/'rounds/R01';sides={};checks={};rows=[];response_models=set();budget_usage={}
    for side in ('parent','candidate'):
        records=[];pending=[]
        paths=list((rd/f'{side}_runs').rglob('actor_state.json'))
        for path in paths:
            r=ev.read(path);completed=r['status']=='completed'
            rows.append({'side':side,'task_id':r['task']['id'],'run_id':r['run_id'],'status':r['status'],
                'termination':r.get('termination'),'hard':r.get('score',{}).get('hard'),
                'per_cell_pass_rate':r.get('score',{}).get('per_cell_pass_rate'),
                'code_attempts':len(r['attempts']),'program_executions':sum(a['executed'] for a in r['attempts']),
                'api_requests':len(r['requests']),'actor_seconds':r['elapsed_seconds'],
                'actor_max_output_tokens':r['protocol']['actor_max_output_tokens'],
                'state_file':str(path),'error_type':r.get('error_type')})
            for request in r['requests']:
                response=request.get('response') or {}
                model=response.get('response_model')
                if model:response_models.add(model)
                request_path=path.parent/request['path']/'request.json'
                limit=ev.read(request_path)['call_config']['max_tokens'] if request_path.exists() else r['protocol']['actor_max_output_tokens']
                counts=budget_usage.setdefault(str(limit),{'requests':0,'saved_responses':0,'length_responses':0,'empty_length_responses':0})
                counts['requests']+=1;counts['saved_responses']+=bool(response)
                counts['length_responses']+=response.get('finish_reason')=='length'
                counts['empty_length_responses']+=response.get('finish_reason')=='length' and not response.get('content','').strip()
            (records if completed else pending).append(r)
        records.sort(key=lambda r:tasks.index(r['task']['id']))
        if records:facts_builder(records)
        sides[side]={'started':len(paths),'completed':len(records),'technical_or_scoring_interruptions':sum(r['status'] in ('technical_interruption','scoring_interrupted') for r in pending),
            'in_progress':sum(r['status'] in ('running','scoring') for r in pending),
            'hard_successes':sum(r['score']['hard'] for r in records),
            'hard':sum(r['score']['hard'] for r in records)/len(records) if records else None,
            'per_cell_pass_rate':sum(r['score']['per_cell_pass_rate'] for r in records)/len(records) if records else None,
            'actor_seconds':sum(r['elapsed_seconds'] for r in records),
            'termination_counts':dict(Counter(r['termination'] for r in records))}
    costs=ev.cost_summary(root);stages={}
    for name in ev.enabled_modules(cfg):
        stage=rd/name;requests=list(stage.rglob('request_started.json'))
        stages[name]={'requests':len(requests),'selected':(stage/'result.json').exists(),
                     'validation_errors':sum(ev.read(p).get('kind')=='output_validation' for p in stage.rglob('error.json'))}
        for p in stage.rglob('response.json'):
            model=ev.read(p).get('response_model')
            if model:response_models.add(model)
    gate=ev.read(rd/'gate/result.json')['result'] if (rd/'gate/result.json').exists() else None
    state=ev.read(root/'state.json');progress=ev.read(root/'pilot_progress.json')
    result=ev.read(rd/'result.json') if (rd/'result.json').exists() else None
    expected_cfg=ev.read(pilot/'candidate_config.json')
    if change:expected_cfg['actor_profile']['actor_max_output_tokens']=change['new_actor_max_output_tokens']
    checks={'only_first_batch':all(r['task_id'] in tasks for r in rows),
            'no_second_round':not (root/'rounds/R02').exists(),
            'no_test_tasks':all(cfg['task_items'][r['task_id']]['split']!='test' for r in rows),
            'no_duplicate_side_task_executions':len(rows)==len({(r['side'],r['task_id']) for r in rows}),
            'completed_actor_transcripts_validated':True,
            'configuration_matches_authorized_settings':cfg==expected_cfg,
            'retained_parent_runs_preserved':not change or set(change['retained_run_ids']).issubset({r['run_id'] for r in rows if r['side']=='parent' and r['status']=='completed'})}
    summary={'status':progress['status'],'stage':ev.read(rd/'progress.json')['stage'],'scope':'First 15 optimization tasks only; not final benchmark evaluation',
        'requested_model':cfg['actor_model'],'response_models':sorted(response_models),'tasks':tasks,
        'sides':sides,'gate':gate,'round_outcome':result['outcome'] if result else None,'checks':checks,
        'method_stages':stages,'cost':costs,'monetary_cost':None,
        'monetary_cost_note':'Provider responses do not establish a billing tariff; token usage is recorded without a monetary estimate.',
        'actor_records':rows,'retained_skill':str(root/state['parent']) if state['parent'] else None,
        'actor_budget_change':change,
        'actor_requests_by_output_limit':budget_usage,
        'active_memory':str(root/state['active_memory']),
        'stop':ev.read(root/'stop.json') if progress['status']=='stopped' and (root/'stop.json').exists() else None,
        'historical_stop':ev.read(root/'stop.json') if (root/'stop.json').exists() else None}
    if progress['status']=='pilot_complete':
        summary['elapsed_wall_seconds']=round(datetime.fromisoformat(progress['at']).timestamp()-(pilot/'run.log').stat().st_birthtime,2)
    ev.save(pilot/'summary.json',summary)
    return summary


def main():
    import json
    p=argparse.ArgumentParser();p.add_argument('pilot',type=Path);p.add_argument('--compact',action='store_true');args=p.parse_args()
    s=summarize(args.pilot)
    value=({'status':s['status'],'stage':s['stage'],'completed':{k:v['completed'] for k,v in s['sides'].items()},
            'successes':{k:v['hard_successes'] for k,v in s['sides'].items()},
            'current':[{k:r[k] for k in ('task_id','status','code_attempts','api_requests')} for r in s['actor_records'] if r['status']!='completed'],
            'stop':s['stop']} if args.compact else {k:s[k] for k in ('status','sides','gate','method_stages','cost')})
    print(json.dumps(value,ensure_ascii=False,indent=None if args.compact else 2))


if __name__=='__main__':main()
