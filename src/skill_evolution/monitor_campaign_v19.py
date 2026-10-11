"""Private v19 paired Monitor with unchanged exact-count Four-Delta Gate.

No Monitor learner projection is ever created. The only return is the version-
bound COMPLETE decision receipt required by Memory. Internal checkpoints reuse
v19 execution machinery, not the public Evolution export API.
"""
from pathlib import Path

from .edit_tracking_v19 import digest, encode, validate_edit_ledger
from .evolution_benchmark_v19 import BenchmarkEvolutionV19
from .evolution_replay_v19 import (_input, _run_set, _load_set, _load, _save,
                                    _file_digest, _lock, _pair_binding)
from .memory_store_v19 import require
from .monitor_v18 import MonitorInput, MonitorTask, summarize_monitor


class BenchmarkMonitorV19(BenchmarkEvolutionV19):
    """Separate fixed Monitor split; never pass to an Evolution learner runner."""
    _split = 'monitor'


def _inputs(ledger, backend, history):
    data = validate_edit_ledger(ledger, history=history)
    manifest = backend.manifest()
    require(type(manifest) is dict and set(manifest) == {'schema_version','task_ids','seed','runtime'}
            and manifest['schema_version'] == 'monitor_manifest_v19.1', 'private Monitor manifest required')
    tasks=manifest['task_ids']
    require(type(tasks) is list and bool(tasks) and all(type(t) is str and bool(t) for t in tasks)
            and len(set(tasks))==len(tasks) and type(manifest['seed']) is int and manifest['seed']>=0,
            'invalid Monitor tasks/seed')
    value=MonitorInput(data['round_id'],tuple(MonitorTask(t,manifest['seed']) for t in tasks),
        ledger.source['editor']['parent_skill'],ledger.source['candidate_skill'],digest(encode(manifest)))
    bound={'schema_version':'private_monitor_input_v19.1','run_id':data['run_id'],'round_id':data['round_id'],
           'manifest':manifest,'ledger_sha256':digest(ledger.output_json),
           'parent_skill_sha256':digest(value.parent_skill),'candidate_skill_sha256':digest(value.candidate_skill)}
    parent_input=_input(data['run_id'],data['round_id'],'PARENT',value.parent_skill,manifest,ledger=ledger)
    return value,bound,parent_input


def _candidate_input(ledger,bound,root):
    return _input(bound['run_id'],bound['round_id'],'CANDIDATE',ledger.source['candidate_skill'],
                  bound['manifest'],ledger=ledger,parent_set=digest(encode(_load(root/'parent/state.json'))))


def _summarize(value,bound,parents,candidates):
    rows=[]
    for task,p,c in zip(value.tasks,parents,candidates):
        _pair_binding(p,c)
        for role,raw in [('PARENT',p),('CANDIDATE',c)]:
            rows.append({'task_id':task.task_id,'seed':task.seed,'role':role,'rollout_index':1,
                'skill_digest':raw['binding']['skill_ref']['sha256'],
                'benchmark_config_digest':value.benchmark_config_digest,'status':'COMPLETE','error':None,
                'success':raw['evaluation']['success'],'compliant':raw['evaluation']['compliant'],
                'initial_state_digest':digest(encode(raw['initial_db']))})
    summary=summarize_monitor(value,rows)
    require(summary['status']=='COMPLETE','Monitor incomplete; Gate unavailable')
    receipt={'status':'COMPLETE','decision':summary['decision'],'run_id':bound['run_id'],'round_id':bound['round_id'],
             'parent_skill_sha256':bound['parent_skill_sha256'],'candidate_skill_sha256':bound['candidate_skill_sha256']}
    return summary,receipt


FILES=('input.json','parent/state.json','candidate/state.json','summary.json','receipt.json')


def load_private_monitor(ledger,*,backend,artifact_dir,history=()):
    root=Path(artifact_dir)
    value,bound,parent_input=_inputs(ledger,backend,history)
    require(_load(root/'input.json')==bound,'Monitor input mismatch')
    marker=_load(root/'validation.json')
    require(marker=={'status':'COMPLETE','files':{n:_file_digest(root/n) for n in FILES}},'Monitor manifest changed')
    parents=_load_set(root/'parent',parent_input)
    candidates=_load_set(root/'candidate',_candidate_input(ledger,bound,root))
    summary,receipt=_summarize(value,bound,parents,candidates)
    require(_load(root/'summary.json')==summary and _load(root/'receipt.json')==receipt,
            'saved Gate differs from private evidence')
    return receipt


def run_private_monitor(ledger,*,backend,artifact_dir,history=(),max_workers=8,resume=False):
    require(type(resume) is bool,'resume must be boolean')
    root=Path(artifact_dir)
    value,bound,parent_input=_inputs(ledger,backend,history)
    with _lock(root):
        if root.exists():
            require(resume,'existing Monitor requires explicit resume')
            require(_load(root/'input.json')==bound,'Monitor resume input mismatch')
            if (root/'validation.json').exists() and _load(root/'validation.json').get('status')=='COMPLETE':
                return load_private_monitor(ledger,backend=backend,artifact_dir=root,history=history)
        else:
            require(not resume,'Monitor resume needs existing output')
            root.mkdir(parents=True)
            _save(root/'input.json',bound)
        _save(root/'validation.json',{'status':'RUNNING'})
        try:
            parents=_run_set(backend,parent_input,root/'parent',resume=(root/'parent').exists(),max_workers=max_workers)
            candidates=_run_set(backend,_candidate_input(ledger,bound,root),root/'candidate',
                resume=(root/'candidate').exists(),max_workers=max_workers,parents=parents)
            summary,receipt=_summarize(value,bound,parents,candidates)
            for name,payload in [('summary.json',summary),('receipt.json',receipt)]:
                if (root/name).exists():
                    require(_load(root/name)==payload,'existing private Monitor result changed')
                else:
                    _save(root/name,payload)
            _save(root/'validation.json',{'status':'COMPLETE','files':{n:_file_digest(root/n) for n in FILES}})
            return receipt
        except BaseException as exc:
            _save(root/'validation.json',{'status':'INCOMPLETE','error_type':type(exc).__name__})
            raise
