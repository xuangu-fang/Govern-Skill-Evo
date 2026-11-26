"""Explicit SpreadsheetBench composition boundary."""
from copy import deepcopy
from pathlib import Path
from ...facts import require
from ...contracts.diagnosis import fields
from . import protocol, actor, executor, facts, evidence, scoring

IDENTITY = {'name':'SpreadsheetBench','dataset':'Verified-400','adapter':'v25_spreadsheetbench_v1','execution_profile':'code_generation_no_score_feedback_v1'}
ROOT = Path(__file__).resolve().parents[7]


class SpreadsheetBenchAdapter:
    identity = IDENTITY

    def __init__(self, *, generate=None, execute=None, score=None):
        self.generate, self.execute, self.score = generate, execute, score

    def validate_config(self, config):
        require(config.get('benchmark') == IDENTITY, 'Explicit SpreadsheetBench identity required')
        p=config['actor_profile']
        optional=set(p)&{'attempt_budget_policy','actor_history_policy'}
        require(set(p)==set(protocol.DEFAULTS)|optional, 'Actor profile fields differ')
        require(p.get('attempt_budget_policy','responses_v1') in ('responses_v1','program_executions_v1'), 'Unknown attempt budget policy')
        require(p.get('actor_history_policy','cumulative_responses_v1') in ('cumulative_responses_v1',protocol.EXECUTION_HISTORY), 'Unknown Actor history policy')
        require(not protocol.execution_history(p) or (protocol.separate_budgets(p) and p['actor_task_timeout_seconds']==0),
                'Execution-only history requires execution budgets and no cumulative task deadline')
        fixture=config.get('dataset',{}).get('kind')=='synthetic_offline'
        expected_profile={**protocol.DEFAULTS,'actor_max_output_tokens':p['actor_max_output_tokens'],
                          'actor_task_timeout_seconds':p['actor_task_timeout_seconds'],
                          **{k:p[k] for k in optional}}
        require((p==expected_profile and p['actor_max_output_tokens'] in (16384,32768,49152)
                 and p['actor_task_timeout_seconds'] in (0,600)) or fixture,
                'Candidate Actor profile differs')
        for k,v in protocol.DEFAULTS.items():
            if isinstance(v,int):require(type(p[k]) is int and (p[k]>=0 if k=='actor_task_timeout_seconds' else p[k]>0), f'Invalid {k}')
        require(p['request_attempts_total']==config['actor_request_attempts'], 'API budget differs')
        require(config['executor']['backend']=='docker', 'Docker execution is required')
        require(config['actor_model']==config['call_config']['model'], 'Actor/method model differs')
        require(config['actor_base_url'].rstrip('/')==config['call_config']['endpoint'].removesuffix('/chat/completions'), 'Actor/method route differs')
        items=config['task_items'];require(isinstance(items,dict) and items,'Missing tasks')
        optimize=[t for b in config['batches'] for t in b];test=config['test_tasks']
        require(not set(optimize)&set(test) and set(optimize)|set(test)==set(items),'Split coverage or separation differs')
        require(len(test)==len(set(test)), 'Duplicate Test tasks')
        for key,t in items.items():
            fields(t,('id','dataset_id','split','instruction','instruction_type','answer_region','input_path','answer_path'),'Task')
            require(t['id']==key and t['split'] in ('train','val','test'), 'Invalid task identity')
            require((t['split']=='test')==(key in test), 'Test task in optimization pool')
            require(Path(t['input_path']).resolve()!=Path(t['answer_path']).resolve(), 'Answer is not an Actor input')
            try:scoring.regions(t['answer_region'])
            except ValueError:
                require(any(x['task_id']==key and x['answer_region']==t['answer_region'] for x in config['dataset'].get('metadata_issues',[])), 'Unrecorded invalid answer region')
        if not fixture:
            require(len(items)==400 and len(optimize)==120 and len(test)==280, 'Verified-400 split differs')
            require([sum(t['split']==s for t in items.values()) for s in ('train','val','test')]==[80,40,280], 'Original split differs')
            require(len(config['batches'])==8 and all(len(b)==15 for b in config['batches']), 'Expected eight batches of fifteen')
            require(config['dataset']['val_participates_in_optimization'] is True, 'Val participation must be explicit')
        require(config['initial_skill']['text'].strip(), 'Missing initial Skill')

    def resource(self,key):
        require(key==Path(key).name and (protocol.PROMPTS/key).is_file(), 'Unknown benchmark resource')
        return protocol.PROMPTS/key

    def frozen_files(self):
        return {str(p.relative_to(ROOT)):p.read_text() for p in sorted(Path(__file__).parent.rglob('*'))
                if p.is_file() and (p.suffix in ('.py','.md') or p.name=='Dockerfile')}

    build_facts=staticmethod(facts.build_facts)
    parent_text=staticmethod(facts.parent_text)
    execution_context=staticmethod(protocol.execution_context)
    actor_fields=staticmethod(protocol.render)
    runtime_snapshot=staticmethod(executor.runtime_snapshot)

    def evidence(self,operation,*args,**kwargs):
        require(operation in evidence.OPERATIONS, f'Unsupported evidence operation: {operation}')
        return evidence.OPERATIONS[operation](*args,**kwargs)

    def plan_fields(self):return ('parent','plan','runs','grouping','memory')
    def auxiliary_references(self,payload):return set()
    def validate_execution_source(self,source):
        fields(source,('run',),'Execution source');return evidence.validate_run(source['run'])
    def validation_sources(self):return {Path(evidence.__file__).resolve(),Path(facts.__file__).resolve()}
    def is_complete(self,record):return record.get('status')=='completed' and record.get('actor_complete') is True

    def actor_task(self,task,skill_file,directory,config,*,final=False):
        require(task in (config['test_tasks'] if final else [t for b in config['batches'] for t in b]), 'Task is outside this execution split')
        require(not any(x['task_id']==task for x in config['dataset'].get('metadata_issues',[])), 'Task has unresolved dataset metadata')
        scoring.regions(config['task_items'][task]['answer_region'])
        return actor.run(config['task_items'][task],Path(skill_file).read_text() if skill_file else None,directory,config,
                         generate=self.generate,execute=self.execute,score=self.score)

    def actor_command(self,*args,**kwargs):
        raise ValueError('Spreadsheet Actor uses the bounded request subprocess and Docker executor directly')

    def check_record(self,record,task,expected_skill,config):
        require(self.is_complete(record), 'Incomplete execution')
        require(record['task']==config['task_items'][task] and record['skill']==expected_skill, 'Task or Skill differs')
        require(record['model']==config['actor_model'] and record['protocol']==config['actor_profile'] and record['executor']==config['executor'],'Execution conditions differ')
        facts.build_facts([record]);return record

    def build_gate(self,parent_records,candidate_records,tasks,*,parent_skill,candidate_skill,implementation_review=None):
        facts.build_facts(parent_records);facts.build_facts(candidate_records)
        require(len(parent_records)==len(candidate_records)==len(tasks), 'Incomplete paired batch')
        p={r['task']['id']:r for r in parent_records};q={r['task']['id']:r for r in candidate_records}
        require(set(p)==set(q)==set(tasks),'Paired task set differs')
        rows=[]
        for tid in tasks:
            require(p[tid]['skill']==parent_skill and q[tid]['skill']==candidate_skill,'Gate Skill differs')
            evidence.verify_pair(p[tid],q[tid],implementation_review=implementation_review)
            rows.append({'task_id':tid,**{side:{'run_id':r['run_id'],'success':bool(r['score']['hard'])} for side,r in [('parent',p[tid]),('candidate',q[tid])]}})
        return {'input':{'pairs':rows}}

    def prepare_evaluation(self,experiment,campaign):
        from ... import evolution as ev
        config=ev.read(Path(campaign)/'config.json');self.validate_config(config)
        require(ev.read(Path(experiment)/'config/campaign.json')==config,'Evaluation experiment config differs')
        require(not config['dataset'].get('metadata_issues'), 'Resolve recorded dataset metadata issues before final Test evaluation')
        skill=ev.final_parent(campaign);require(skill is not None,'Final Skill missing')
        return {'campaign':str(Path(campaign).resolve()),'skill_text':skill.read_text(),
                'actor_config':deepcopy(config),'tasks':[config['task_items'][t] for t in config['test_tasks']],
                'initial_reference':None,'evaluation_policy':'Test only; reporting without optimization'}

    def check_evaluation_record(self,path,task,bundle):
        from ...evolution import read
        require(task in bundle['actor_config']['test_tasks'],'Not a Test task')
        return self.check_record(read(path),task,bundle['skill_text'],bundle['actor_config'])
