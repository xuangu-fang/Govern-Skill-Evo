"""Read-only comparison of saved episodes; no model or environment entry point."""
from collections import Counter
from itertools import groupby
import json
from pathlib import Path
from experiments.methods.v23_2.v23_2_response_behavior_001 import run as r
from src.skill_evolution.v23 import evolution as ev, editor
from src.adapters.alfworld.response_archive import verify_response_archive


def search_metrics(record):
    steps=record['steps']; first=next((s['step'] for s in steps if s.get('action','').startswith('take ')),None)
    before=[s for s in steps if first is None or s['step']<first]
    visits=[(s['step'],s['action'][6:]) for s in before if s.get('action','').startswith('go to ')]
    kinds=[place.rsplit(' ',1)[0] for _,place in visits]
    return {'before_first_take_step':first,'go_to_count':len(visits),'distinct_locations':len({p for _,p in visits}),
            'repeat_go_to_count':len(visits)-len({p for _,p in visits}),
            'distinct_location_types':len(set(kinds)),
            'longest_same_type_go_to_streak':max((len(list(g)) for _,g in groupby(kinds)),default=0),
            'visits':visits,'inventory_actions_total':sum(s.get('action')=='inventory' for s in steps)}


def main():
    plan=ev.read(r.EXP/'config/plan.json');new=ev.read(r.OUTPUT/'candidate_results.json')
    paths={'Parent':plan['historical_records']['parent_runs'],'V23':plan['historical_records']['candidate_runs'],'V23.2':new['paths']}
    sources=['# 三组逐步证据\n','P=Parent；Q=原 V23 Candidate；N=新 V23.2 Candidate。步骤为实际执行动作，观察为动作后环境反馈。\n']
    rows=[]; checks=[]
    ep=r.history.selected(r.OUTPUT,'editor'); saved=r.load_handoff(r.UPSTREAM)
    edit=editor.load_editor(ep,expected_preconditioner=saved,expected_call_config=plan['editor_call_config'])
    for i,task in enumerate(plan['tasks']):
        row={'task_id':task,'groups':{}};ref=None
        sources.append(f'\n## {task}\n')
        for label,items in paths.items():
            path=Path(items[i]);record=ev.read(path)
            if ref is None:ref=record
            assert record['task']==ref['task'] and record['gamefile']==ref['gamefile']
            assert record['initial_observation']==ref['initial_observation'] and record['initial_admissible_commands']==ref['initial_admissible_commands']
            assert record['protocol']==ref['protocol'] and record['environment']==ref['environment'] and record['model']==ref['model']
            assert record['request_policy']==ref['request_policy'] and record['status'] in ev.COMPLETE
            if label=='V23.2':assert record['skill']['text']==edit['candidate_text']
            for step in record['steps']:
                for attempt in step.get('transport_attempts',[]):verify_response_archive(path,attempt)
            executed=[s for s in record['steps'] if s.get('phase')=='executed']
            row['groups'][label]={'status':record['status'],'success':record['won'],'steps':len(executed),
                                  'trajectory':str(path),'search':search_metrics(record)}
            sources += [f'\n### {label}\n',f'[{record["goal"]}]({path}) — {record["status"]}, {len(executed)} 步\n']
            for s in executed:
                sources.append(f'- {s["step"]}. `{s["action"]}` → {s["observation"].replace(chr(10)," ")}\n')
        checks.append({'task_id':task,'identity_gamefile_initial_state_protocol_environment_model_retry_equal':True,'new_skill_exact':True,'raw_response_archives_verified':True})
        rows.append(row)
    totals={label:{'successes':sum(row['groups'][label]['success'] for row in rows),'total_steps':sum(row['groups'][label]['steps'] for row in rows)} for label in paths}
    changes={label:{'repairs':[row['task_id'] for row in rows if row['groups']['V23.2']['success'] and not row['groups'][label]['success']],
                    'regressions':[row['task_id'] for row in rows if not row['groups']['V23.2']['success'] and row['groups'][label]['success']]} for label in ('Parent','V23')}
    ev.save(r.EXP/'results/comparison.json',{'rows':rows,'totals':totals,'changes':changes})
    ev.save(r.EXP/'results/verification.json',{'episodes':checks,'strict_patch_reapplication':True,'original_parent_exact':True,'frozen_effective_plan_exact':True})
    (r.EXP/'reports/TRAJECTORIES.md').write_text('\n'.join(sources))
    (r.EXP/'reports/actual.diff').write_text(edit['actual_diff'])
    ev.save(r.EXP/'results/cost.json',ev.cost_summary(r.OUTPUT))
    r.verify_protection()
    print(json.dumps({'totals':totals,'changes':changes},ensure_ascii=False))


if __name__=='__main__':main()
