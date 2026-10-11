"""Offline migration of one committed round to facts-only Attribution/Memory."""
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timezone

from .memory_restart_v19 import (files, compatible_manifest, _ManifestView, ENTRYPOINT,
                                 PRESERVED_SOURCES, MemoryRestart)
from .memory_store_v19 import require, load_memory, initialize_memory, commit_round_memory, _durable_save
from .evolution_replay_v19 import _load, _file_digest, _lock, load_parent_experiences
from .campaign_v19 import source_manifest, _binding, _round_result, campaign_report
from . import attribution_pairs_v19 as pairs


class SemanticsMigration(MemoryRestart):
    def __init__(self, path):
        self.path=Path(path).resolve();self.receipt=_load(self.path);self.sha256=_file_digest(self.path)
        require(self.receipt['schema_version']=='semantics_migration_v19.1','unknown migration protocol')
        self.validate_sources()

    def verify_reused_artifacts(self, output):
        super().verify_reused_artifacts(output)
        snapshot=load_memory(Path(output)/'memory')
        require(bool(snapshot.rounds) and snapshot.rounds[0]['record']==self.receipt['new_round_record'],
                'migrated first-round Memory changed')


def prepare_semantics_migration(*,source,archive,output,evolution,monitor):
    from .monitor_campaign_v19 import load_private_monitor
    from .experience_cards_v17 import build_experience_cards
    from .grouping_campaign_v19 import _request, run_campaign_grouping
    source,archive,output=(Path(p).resolve() for p in (source,archive,output))
    paths=(source,archive,output)
    require(all(a!=b and a not in b.parents and b not in a.parents
                for i,a in enumerate(paths) for b in paths[i+1:]),'migration paths must be disjoint')
    require(source.is_dir(),'source missing')
    with _lock(source),_lock(archive),_lock(output):
        require(not archive.exists() and not output.exists(),'destination already exists')
        old=_load(source/'binding.json');code=source_manifest()
        require(old.get('entrypoint')==ENTRYPOINT,'unified local/pair run required')
        for name in PRESERVED_SOURCES:
            path='src/skill_evolution/'+name+'_v19.py'
            require(old['source_files'].get(path)==code[path],'upstream implementation changed: '+name)
        actual={'evolution_manifest':evolution.manifest(),'monitor_manifest':monitor.manifest()}
        for key,value in actual.items():compatible_manifest(old[key],value)
        snapshot=load_memory(source/'memory')
        require(snapshot.head['revision']==1,'exactly one committed round required')
        require(not (source/'round-02/generation').exists(),
                'round-02 generation exists; requires a separate downstream migration')
        evo=_ManifestView(evolution,old['evolution_manifest']);mon=_ManifestView(monitor,old['monitor_manifest'])
        ledger=snapshot.history[0].ledger
        require(ledger.source['editor']['parent_skill']==old['initial_skill'],'initial Skill mismatch')
        gate=load_private_monitor(ledger,backend=mon,artifact_dir=source/'round-01/monitor_private')
        hashes=files(source)
        archive_stage=archive.with_name('.'+archive.name+'.pending-'+uuid.uuid4().hex)
        stage=output.with_name('.'+output.name+'.pending-'+uuid.uuid4().hex)
        shutil.copytree(source,archive_stage)
        require(files(archive_stage)==hashes==files(source),'archive checksum mismatch')
        stage.mkdir();shutil.copytree(archive_stage/'round-01',stage/'round-01')
        attr=stage/'round-01/attribution';data=_load(attr/'input.json')
        previous=pairs.load_complete(attr,data)
        batch=pairs.aggregate(data,previous.payload['pair_results'])
        _durable_save(attr/'attributions.json',batch.payload)
        marker=_load(attr/'validation.json');marker['files']={n:_file_digest(attr/n) for n in pairs.FILES}
        _durable_save(attr/'validation.json',marker)
        require(pairs.load_complete(attr,data)==batch,'facts aggregate validation failed')
        initialize_memory(store_dir=stage/'memory',run_id=old['run_id'],initial_skill=old['initial_skill'])
        commit_round_memory(ledger,store_dir=stage/'memory',expected_head_ref=None,backend=evo,
            parent_dir=stage/'round-01/parent_evolution',replay_dir=stage/'round-01/candidate_evolution',
            attribution_dir=attr,gate_result=gate)
        migrated=load_memory(stage/'memory')
        require(migrated.head['retained_skill']==snapshot.head['retained_skill'],'retained Skill changed')
        _durable_save(stage/'round-01/round_result.json',_round_result(migrated.rounds[0]))
        grouping_status='ABSENT'
        if (source/'round-02').exists():
            (stage/'round-02').mkdir()
            shutil.copytree(archive_stage/'round-02/parent_evolution',stage/'round-02/parent_evolution')
            experiences,scope=load_parent_experiences(run_id=old['run_id'],round_id='round-02',
                parent_skill=migrated.head['retained_skill'],backend=evo,artifact_dir=stage/'round-02/parent_evolution')
            grouping=archive_stage/'round-02/grouping'
            if grouping.exists():
                cards=build_experience_cards(experiences,scope=scope,max_input_chars=old['config']['max_grouping_chars'])
                bound={'request':_request(cards,scope),'scope':{'round_id':scope.round_id,
                    'parent_skill_digest':scope.parent_skill_digest,'experiences':[vars(r) for r in scope.experiences]}}
                require(_load(grouping/'input.json')==bound,'round-02 grouping input changed')
                shutil.copytree(grouping,stage/'round-02/grouping')
                grouping_status=_load(grouping/'validation.json')['status']
                if grouping_status=='COMPLETE':
                    def no_model(_):raise ValueError('offline migration cannot call models')
                    run_campaign_grouping(cards,scope=scope,artifact_dir=stage/'round-02/grouping',resume=True,transport=no_model)
                else:
                    # Retain completed calls; move unanswered attempts to an audit
                    # directory in the NEW run. Never erase or alter old attempts.
                    from .memory_generation_v19 import _read_call
                    for call in sorted((stage/'round-02/grouping').glob('attempt-*')):
                        request=_load(call/'request.json')
                        if (call/'response_complete.json').exists():_read_call(call,request)
                        else:
                            require(not (call/'response.json').exists(),'partial response needs manual inspection')
                            from .run_control_v19 import RETRYABLE
                            failure=_load(call/'failure.json') if (call/'failure.json').exists() else None
                            require(failure is None or failure.get('error_type') in RETRYABLE | {'KeyboardInterrupt'},
                                    'non-transport grouping failure requires inspection')
                            target=stage/'recovery'/('migration-'+call.name);target.mkdir(parents=True)
                            _durable_save(target/'receipt.json',{'reason':'INTERRUPTED_WITHOUT_COMPLETE_RESPONSE',
                                'original_path':str(call.relative_to(stage)),'files':files(call)})
                            call.rename(target/'call')
        # Only immutable reused files are protected across subsequent resume.
        reused={str(p.relative_to(stage)):_file_digest(p) for p in (stage/'round-01').rglob('*') if p.is_file()}
        if (stage/'round-02/parent_evolution').exists():
            reused.update({str(p.relative_to(stage)):_file_digest(p) for p in (stage/'round-02/parent_evolution').rglob('*') if p.is_file()})
        receipt={'schema_version':'semantics_migration_v19.1','created_at':datetime.now(timezone.utc).isoformat(),
            'source':str(source),'archive':str(archive),'original_binding':old,'replacement_sources':code,
            'current_manifests':actual,'archive_files':hashes,'reused_files':reused,
            'old_memory_head':snapshot.head,'new_memory_head':migrated.head,
            'new_round_record':migrated.rounds[0]['record'],'grouping_status':grouping_status,
            'memory_protocol':'issue_memory_v19.2','aggregate_protocol':'attribution_batch_v19.3',
            'identity_policy':'SOURCE_RUN_ID_AND_EXECUTION_MANIFEST_RETAINED; NEW_CODE_BOUND_SEPARATELY'}
        _durable_save(stage/'migration.json',receipt)
        bound=_binding(old['config'],old['run_id'],old['initial_skill'],evo,mon)
        _durable_save(stage/'binding.json',{**bound,'entrypoint':ENTRYPOINT,'memory_restart_sha256':_file_digest(stage/'migration.json')})
        report=campaign_report(migrated,status='INCOMPLETE');report.update(active_round='round-02',failed_stage='GROUPING',error_type='MIGRATION_READY')
        _durable_save(stage/'campaign.json',report)
        require(files(source)==hashes and source_manifest()==code,'source changed during migration')
        archive_stage.rename(archive);stage.rename(output)
        SemanticsMigration(output/'migration.json').verify_reused_artifacts(output)
        return {'status':'READY','output':str(output),'archive':str(archive),'memory_revision':1,
                'grouping_status':grouping_status,'model_calls':0}
