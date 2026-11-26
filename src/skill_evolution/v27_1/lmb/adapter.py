"""Native LMB Actor pool and immutable execution journals; no method Gate."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
import uuid
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.stages import freeze, read, save
from . import facts, protocol as p, actor


class LMBExecution:
    def execution_profile(self, record):
        return self.transport.metadata()

    def read_completed_case(self, case, skill, directory):
        return actor.read_completed(case, skill, directory, self.transport.metadata())

    def execute_case(self, case, skill, directory):
        return actor.execute(case, skill, directory, self.transport)

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
                    self.read_completed_case(case,skill,folder)
                else:
                    actor.validate_pending(case,skill,folder,self.transport.metadata())
            def run(case):
                folder=root/'actor'/p.digest(case.case_id)
                e=self.execute_case(case,skill,folder)
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
        require(e['skill']==expected_skill and p.equal(e['actor'],self.execution_profile(record)),'Actor or Skill differs')
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
        result=self.read_completed_case(self.dataset.case(task),expected_skill,folder)
        require((folder/'trajectory.json').is_file(), 'Missing completed Actor trajectory')
        require(p.equal(result,record['execution']) and p.equal(read(folder/'trajectory.json'),record),
                'Cached trajectory differs from Actor archive')
        return record
