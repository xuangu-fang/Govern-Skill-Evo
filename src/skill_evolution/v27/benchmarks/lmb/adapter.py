"""LMB-specific Actor pool, immutable identities, evidence dispatch and EM Gate."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from copy import deepcopy
import json
from pathlib import Path
import uuid
from ...facts import require
from ...contracts import gate
from ...stages import freeze, read, save
from . import evidence, facts, protocol as p, actor


class LMBAdapter:
    identity=p.IDENTITY
    build_facts=staticmethod(facts.build_facts)
    parent_text=staticmethod(facts.parent_text)
    execution_context=staticmethod(p.execution_context)
    def __init__(self,dataset=None,transport=None,*,workers=20,test_workers=16,gate_metric=None):
        require(type(workers) is int and workers==20 and type(test_workers) is int and test_workers==16,'Frozen LMB worker limits are 20/16')
        require((dataset is None)==(transport is None),'Supply dataset and transport together')
        require(gate_metric in (None,p.EM_GATE),'Unknown LMB Gate')
        self.dataset=dataset;self.transport=transport;self.workers=workers;self.test_workers=test_workers;self.gate_metric=gate_metric
        if transport is not None:p.background(transport.metadata())
    def _bound(self):require(self.dataset is not None and self.transport is not None,'Explicit Actor dependencies required')
    def evidence(self,operation,*args,**kwargs):
        require(operation in evidence.OPERATIONS,'Unknown evidence operation');return evidence.OPERATIONS[operation](*args,**kwargs)
    def plan_fields(self):return ('parent','plan','runs','grouping','memory')
    def auxiliary_references(self,payload):return set()
    def validate_execution_source(self,source):
        p.fields(source,('run',),'Execution source');return facts.validate_run(source['run'])
    def validation_sources(self):return {Path(m.__file__).resolve() for m in (p,facts,evidence)}
    def resource(self,key):
        from .prompting import resource_path
        return resource_path(key)
    def frozen_files(self):
        import skilladam
        local=Path(__file__).resolve().parents[2]; root=local.parents[2]
        paths=[q for q in local.rglob('*') if q.suffix in ('.py','.md','.json')]
        native=Path(skilladam.__file__).parent
        paths += [native/'benchmarks/lmb'/name for name in ('choices.py','rollout.py','evaluation.py')]
        return {str(q.relative_to(root)):q.read_text() for q in sorted(paths)}
    def runtime_snapshot(self,config):
        import sys
        self._bound()
        return {'python':sys.version,'data':self.dataset.snapshot(),'actor':self.transport.metadata(),
                'workers':self.workers,'test_workers':self.test_workers,'gate_metric':self.gate_metric}
    def validate_config(self,config):
        p.fields(config,('split','role'),'Execution configuration')
        require(config['split'] in ('train','validation','test') and config['role'] in ('parent','candidate','evaluation'),'Invalid execution role')
        require((config['role']=='evaluation')==(config['split']=='test'),'Test is isolated from optimization')
    def _source_identity(self,case):
        return {'case_sha256':p.digest(self.dataset.rows[case.case_id]),'task_context_sha256':p.digest(p.messages(case.payload,None)),'scorer':p.EM_GATE}
    def actor_batch(self,tasks,skill_file,directory,config,*,final=False):
        self._bound();self.validate_config(config)
        require(type(final) is bool and final==(config['role']=='evaluation'),'Execution final flag differs')
        tasks=list(tasks);require(tasks and len(tasks)==len(set(tasks)),'Missing/duplicate Actor tasks')
        cases=[self.dataset.case(t) for t in tasks]
        require(all(c.metadata['split']==config['split'] for c in cases),'Wrong task split')
        skill=None if skill_file is None else Path(skill_file).read_bytes().decode('utf-8')
        root=Path(directory)
        with actor.locked(root):
            signature={'tasks':tasks,'sources':{c.case_id:self._source_identity(c) for c in cases},'actor':self.transport.metadata(),
                       'skill':skill,'config':config,'workers':self.test_workers if final else self.workers}
            meta=root/'batch.json'
            if meta.exists():
                value=read(meta);require(p.equal(value['signature'],signature),'Frozen batch differs')
            else:value={'batch_id':str(uuid.uuid4()),'signature':signature};save(meta,value)
            # Check every known completion before submitting any workers. An
            # incomplete batch may contain both completed and pending tasks.
            if (root/'records.json').exists():
                records=read(root/'records.json')
                require(isinstance(records,list) and [r['task_id'] for r in records]==tasks,
                        'Completed Actor batch coverage/order differs')
                for record in records:
                    self.check_record_archive(record,record['task_id'],skill,config,root)
                return records
            for case in cases:
                folder=root/'actor'/p.digest(case.case_id)
                if (folder/'trajectory.json').exists():
                    self.check_record_archive(read(folder/'trajectory.json'),case.case_id,skill,config,root)
                elif (folder/'result.json').exists():
                    actor.read_completed(case,skill,folder,self.transport.metadata())
                else:
                    actor.validate_pending(case,skill,folder,self.transport.metadata())
            def run(case):
                folder=root/'actor'/p.digest(case.case_id)
                e=actor.execute(case,skill,folder,self.transport)
                record={'schema':p.RECORD_VERSION,'run_id':value['batch_id']+':'+p.digest(case.case_id),
                        'task_id':case.case_id,'task':p.public_task(case),'execution':e,
                        'provenance':{'batch_id':value['batch_id'],'role':config['role'],**self._source_identity(case),'record_sha256':p.digest(e)}}
                self.check_record(record,case.case_id,skill,config);freeze(folder/'trajectory.json',record)
                return record
            with ThreadPoolExecutor(max_workers=self.test_workers if final else self.workers) as pool:
                futures=[pool.submit(copy_context().run,run,c) for c in cases]
                records=[f.result() for f in futures] # Frozen task order, never completion order.
            freeze(root/'records.json',records)
            return records
    def actor_task(self,task,skill_file,directory,config,*,final=False):
        self.actor_batch([task],skill_file,directory,config,final=final)
        return Path(directory)/'actor'/p.digest(task)/'trajectory.json'
    def check_record(self,record,task,expected_skill,config):
        self._bound();self.validate_config(config);facts.validate_envelope(record)
        case=self.dataset.case(task);e=record['execution']
        require(record['task_id']==task and p.equal(record['task'],p.public_task(case)),'Canonical task differs')
        require(case.metadata['split']==config['split'] and record['provenance']['role']==config['role'],'Role/split differs')
        require(e['skill']==expected_skill and p.equal(e['actor'],self.transport.metadata()),'Actor or Skill differs')
        require(all(p.equal(record['provenance'][k],v) for k,v in self._source_identity(case).items()),'Source identity differs')
        require(e['answer']['correct_label']==case.reference['label'],'Reference mapping differs')
        return record
    def is_complete(self,record):
        try:facts.validate_envelope(record);return True
        except (ValueError,KeyError,TypeError):return False
    def check_record_archive(self,record,task,expected_skill,config,directory):
        """Validate cached evidence against its original journal without executing recovery."""
        self.check_record(record,task,expected_skill,config)
        root=Path(directory);batch=read(root/'batch.json');tasks=batch['signature']['tasks']
        require(task in tasks and len(tasks)==len(set(tasks)), 'Archived batch tasks differ')
        expected={'tasks':tasks,'sources':{t:self._source_identity(self.dataset.case(t)) for t in tasks},
                  'actor':self.transport.metadata(),'skill':expected_skill,'config':config,
                  'workers':self.test_workers if config['role']=='evaluation' else self.workers}
        require(p.equal(batch['signature'],expected), 'Archived batch signature differs')
        require(record['provenance']['batch_id']==batch['batch_id'] and
                record['run_id']==batch['batch_id']+':'+p.digest(task), 'Archived run identity differs')
        folder=root/'actor'/p.digest(task)
        result=actor.read_completed(self.dataset.case(task),expected_skill,folder,self.transport.metadata())
        require((folder/'trajectory.json').is_file(), 'Missing completed Actor trajectory')
        require(p.equal(result,record['execution']) and p.equal(read(folder/'trajectory.json'),record),
                'Cached trajectory differs from Actor archive')
        return record
    def build_gate(self,parent_records,candidate_records,tasks,*,parent_skill,candidate_skill,implementation_review=None):
        require(self.gate_metric==p.EM_GATE,'Select EM Gate explicitly')
        tasks=list(tasks);require(tasks and len(tasks)==len(set(tasks)),'Invalid Gate tasks')
        parents={r['task_id']:r for r in parent_records}; candidates={r['task_id']:r for r in candidate_records}
        require(len(parents)==len(parent_records) and len(candidates)==len(candidate_records) and set(parents)==set(candidates)==set(tasks),'Incomplete Gate pairs')
        pairs=[]
        for task in tasks:
            a,b=parents[task],candidates[task]
            for role,r,skill in (('parent',a,parent_skill),('candidate',b,candidate_skill)):
                require(facts.parent_text(r)==skill,'Gate Skill differs')
                if self.dataset is not None:self.check_record(r,task,skill,{'split':r['task']['split'],'role':role})
            evidence.verify_pair(a,b,implementation_review=implementation_review)
            pairs.append({'task_id':task,'parent':{'run_id':a['run_id'],'success':a['execution']['metrics']['em']==1},
                          'candidate':{'run_id':b['run_id'],'success':b['execution']['metrics']['em']==1}})
        payload={'pairs':pairs};gate.validate_input(payload,tasks)
        return {'metric':p.EM_GATE,'input':payload,'result':gate.decide_gate(payload,tasks)}
