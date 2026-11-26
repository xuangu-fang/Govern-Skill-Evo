#!/usr/bin/env python3
"""User-authorized Actor budget change for this functional pilot only."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.runs.v25.run_v25_pilot import run_pilot
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmarks.spreadsheetbench import facts,protocol,evidence


class PilotAdapter(SpreadsheetBenchAdapter):
    def __init__(self,change,**kwargs):
        super().__init__(**kwargs);self.change=change

    def build_facts(self,records):
        ev.require(records,'Missing executions');parent=records[0]['skill'];runs=[];sources=[]
        for i,r in enumerate(records,1):
            ev.require(r['skill']==parent,'Mixed Skills')
            expected=16384 if r['run_id'] in self.change['retained_run_ids'] else 32768
            ev.require(r['protocol']=={**protocol.DEFAULTS,'actor_max_output_tokens':expected},'Unexpected pilot profile')
            single=facts.build_facts([r]);runs.append(evidence.relabel(single['facts']['runs'][0],f'P{i}'))
            sources.append({**single['sources'][0],'ref':f'P{i}'})
        ev.require(len({r['task_id'] for r in runs})==len(runs),'Duplicate tasks')
        background=protocol.background({**protocol.DEFAULTS,'actor_max_output_tokens':32768})
        note=('Functional pilot only: the first '+str(len(self.change['retained_run_ids']))+
              ' completed Parent executions used a 16384-token output limit. Subsequent Actor requests use 32768. '
              'Each run includes its actual initial messages. Paired results are a mixed-budget functional comparison; '
              'do not attribute differences exclusively to the Skill edit. The following template describes the current 32768-token profile.\n\n')
        background['actor_system_prompt']=note+background['actor_system_prompt']
        return {'facts':{'parent':parent,'runs':runs},'background':background,'sources':sources}

    def verify_pair(self,parent,candidate,*,implementation_review=None):
        self.build_facts([parent]);self.build_facts([candidate])
        normalized=deepcopy(candidate);normalized['protocol']['actor_max_output_tokens']=parent['protocol']['actor_max_output_tokens']
        evidence.verify_pair(parent,normalized,implementation_review=implementation_review)

    def evidence(self,operation,*args,**kwargs):
        if operation=='contracts.replay.build_replay_from_editor':
            return evidence.build_replay_from_editor(*args,**kwargs,facts_builder=self.build_facts,pair_verifier=self.verify_pair)
        if operation=='contracts.replay.verify_pair':return self.verify_pair(*args,**kwargs)
        return super().evidence(operation,*args,**kwargs)

    def check_record(self,record,task,expected_skill,config):
        self.build_facts([record]);cfg=deepcopy(config);cfg['actor_profile']=record['protocol']
        return super().check_record(record,task,expected_skill,cfg)

    def build_gate(self,parent_records,candidate_records,tasks,*,parent_skill,candidate_skill,implementation_review=None):
        self.build_facts(parent_records);self.build_facts(candidate_records)
        p={r['task']['id']:r for r in parent_records};q={r['task']['id']:r for r in candidate_records}
        ev.require(len(parent_records)==len(candidate_records)==len(tasks) and set(p)==set(q)==set(tasks),'Incomplete pilot pairs')
        pairs=[]
        for tid in tasks:
            ev.require(p[tid]['skill']==parent_skill and q[tid]['skill']==candidate_skill,'Paired Skill differs')
            self.verify_pair(p[tid],q[tid],implementation_review=implementation_review)
            pairs.append({'task_id':tid,**{side:{'run_id':r['run_id'],'success':bool(r['score']['hard'])} for side,r in [('parent',p[tid]),('candidate',q[tid])]}})
        return {'input':{'pairs':pairs}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);args=p.parse_args()
    root=args.campaign.resolve();change=ev.read(root/'pilot_budget_change/change.json')
    with using_benchmark(PilotAdapter(change)):
        ev.check_live_environment(ev.read(root/'config.json'))
        result=run_pilot(root,resume=True)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
