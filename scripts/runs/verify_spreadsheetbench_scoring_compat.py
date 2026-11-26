#!/usr/bin/env python3
"""Read-only workbook scoring audit: no model calls or generated programs."""
import argparse
from collections import Counter
from pathlib import Path
import sys
from types import ModuleType

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmarks.spreadsheetbench import scoring


def verify(config_file, reference_campaign, report):
    config=ev.read(config_file);reference_campaign=Path(reference_campaign)
    old=ev.read(reference_campaign/'config.json')
    source_key='src/skill_evolution/v25/benchmarks/spreadsheetbench/scoring.py'
    legacy=ModuleType('frozen_scoring_reference')
    exec(compile(ev.read(reference_campaign/'contract.json')[source_key],source_key,'exec'),legacy.__dict__)
    for key in set(config)|set(old):
        if key not in ('dataset','task_items'):ev.require(config.get(key)==old.get(key),f'Non-scoring configuration changed: {key}')
    ev.require({k:v for k,v in config['dataset'].items() if k not in ('metadata_issues','scoring_compatibility')}
               =={k:v for k,v in old['dataset'].items() if k!='metadata_issues'},'Dataset protocol changed')
    changed=[]
    for key,task in config['task_items'].items():
        previous=old['task_items'][key]
        ev.require({k:v for k,v in task.items() if k!='answer_region'}=={k:v for k,v in previous.items() if k!='answer_region'},f'Task input changed: {key}')
        if task['answer_region']!=previous['answer_region']:changed.append(key)
    ev.require(changed==['test:60-7'],'Unexpected task region changes')
    ev.require(not config['dataset']['metadata_issues'],'Unresolved metadata issues')
    excluded={x['task_id'] for x in old['dataset']['metadata_issues']}
    counts=Counter();rows=[]
    for index,(key,task) in enumerate(config['task_items'].items(),1):
        profile=config['actor_profile'];gold=task['answer_path'];inp=task['input_path'];region=task['answer_region']
        oracle=scoring.score(gold,gold,region,profile)
        ev.require(oracle['hard']==1 and oracle['total_cells']>0,f'Oracle failed: {key}')
        counts[task['split']+'_oracle_pass']+=1
        untouched=scoring.score(inp,gold,region,profile)
        row={'task_id':key,'oracle_cells':oracle['total_cells'],'oracle_hard':oracle['hard'],
             'unmodified_input_hard':untouched['hard'],'unmodified_input_per_cell_pass_rate':untouched['per_cell_pass_rate']}
        if key not in excluded:
            ev.require(scoring.regions(region)==legacy.regions(old['task_items'][key]['answer_region']),f'Existing cell selection changed: {key}')
            before=legacy.score(inp,gold,old['task_items'][key]['answer_region'],profile)
            for field in ('hard','correct_cells','total_cells','mismatched_cells','missing_sheets'):
                ev.require(before[field]==untouched[field],f'Existing score changed: {key}/{field}')
            ev.require(round(before['per_cell_pass_rate'],4)==untouched['per_cell_pass_rate'],f'Rate rounding differs: {key}')
            counts[task['split']+'_legacy_equivalent']+=1
            row['legacy_equivalent_except_rate_rounding']=True
        rows.append(row)
        if index%25==0:print(f'Checked {index}/400 workbooks',flush=True)
    result={'status':'passed','checked_at':ev.now(),'config_file':str(Path(config_file).resolve()),
            'reference_campaign':str(reference_campaign.resolve()),'counts':dict(counts),
            'changed_task_regions':changed,'rows':rows,'model_requests':0,'generated_program_executions':0,
            'scope':'gold-vs-gold all 400; unmodified-input comparison against frozen scorer on 397 valid legacy tasks; no Actor execution'}
    ev.save(Path(report),result)
    return {k:v for k,v in result.items() if k!='rows'}


def main():
    import json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True,type=Path)
    p.add_argument('--reference-campaign',required=True,type=Path)
    p.add_argument('--report',required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(verify(a.config,a.reference_campaign,a.report),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
