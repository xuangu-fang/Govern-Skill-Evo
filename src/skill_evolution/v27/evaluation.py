"""Independent frozen Test evaluation; no optimizer or Memory feedback path."""
from copy import deepcopy
from pathlib import Path
from .facts import require
from .stages import read, freeze, freeze_text, save
from .storage import load_skill
from .training import POOL_IDS
from .benchmarks.lmb import protocol as p
from .benchmarks.lmb.actor import locked

TEST_IDS=tuple(POOL_IDS['test'])
VERSION='v27_lmb_test_v1'
ROLE={'split':'test','role':'evaluation'}

class ArchiveTransport:
    def __init__(self,metadata=None):self.config=deepcopy(p.ACTOR if metadata is None else metadata)
    def metadata(self):return deepcopy(self.config)
    def __call__(self,*args,**kwargs):raise RuntimeError('Archive-only transport cannot issue requests')

def _tasks(adapter):
    adapter._bound()
    require(len(TEST_IDS)==len(set(TEST_IDS))==124,'Invalid Test IDs')
    require(tuple(adapter.dataset.splits['test'])==TEST_IDS,'Test IDs/order differ')
    require(adapter.gate_metric is None,'Test must not configure Gate')
    return list(TEST_IDS)

def _contract(adapter):return {k:p.digest(v) for k,v in adapter.frozen_files().items()}

def _verify(root,adapter):
    plan=read(root/'plan.json')
    require(plan['version']==VERSION and plan['tasks']==_tasks(adapter) and plan['role']==ROLE,'Test plan differs')
    require(plan['contract']==_contract(adapter) and plan['runtime']==adapter.runtime_snapshot({'batches':[plan['tasks']]}),'Frozen Test sources changed')
    if plan['skill']['mode']=='fixed':freeze_text(root/'skill.md',plan['skill']['text'],read_only=True)
    else:require(plan['skill']=={'mode':'none','text':None},'Invalid no-Skill identity')
    return plan

def report_evaluation(directory,*,adapter):
    root=Path(directory);plan=_verify(root,adapter);records=[]
    for task in plan['tasks']:
        file=root/'batch/actor'/p.digest(task)/'trajectory.json'
        if file.exists():
            record=read(file)
            adapter.check_record_archive(record,task,plan['skill']['text'],ROLE,root/'batch')
            records.append(record)
    done={r['task_id'] for r in records}
    full=len(done)==124
    result={'version':VERSION,'status':'complete' if full else 'incomplete','total':124,'completed':len(done),
            'pending_ids':[t for t in plan['tasks'] if t not in done],'optimization_updates':False,
            'skill_sha256':p.digest(plan['skill']['text']),'em':sum(r['execution']['metrics']['em'] for r in records)/124 if full else None,
            'exact_matches':sum(r['execution']['metrics']['em'] for r in records) if full else None,
            'actor_requests':sum(r['execution']['api_requests'] for r in records),
            'cases':[{'task_id':r['task_id'],**r['execution']['metrics'],'termination':r['execution']['termination'],
                      'answer':r['execution']['answer']} for r in records]}
    save(root/'report.json',result);return result

def run_evaluation(directory,*,adapter,skill_file,resume=False):
    tasks=_tasks(adapter);root=Path(directory).resolve();skill=load_skill(skill_file)
    protected=[adapter.dataset.root.resolve()]
    if skill_file is not None:protected.append(Path(skill_file).resolve())
    require(all(not root.is_relative_to(q) and not q.is_relative_to(root) for q in protected),'Separate Test directory required')
    require(not any((q/'state.json').exists() and (q/'config.json').exists() for q in (root,*root.parents)),'Test output cannot be inside Campaign')
    with locked(root):
        exists=(root/'plan.json').exists()
        require(not exists or resume,'Existing Test requires explicit resume')
        plan={'version':VERSION,'tasks':tasks,'role':ROLE,'skill':skill,'contract':_contract(adapter),
              'runtime':adapter.runtime_snapshot({'batches':[tasks]})}
        freeze(root/'plan.json',plan)
        if skill['mode']=='fixed':freeze_text(root/'skill.md',skill['text'])
        _verify(root,adapter)
        adapter.actor_batch(tasks,root/'skill.md' if skill['mode']=='fixed' else None,root/'batch',ROLE,final=True)
        return report_evaluation(root,adapter=adapter)

def final_skill(campaign):
    from .evolution import final_parent
    return final_parent(campaign)
