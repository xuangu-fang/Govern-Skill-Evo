"""Offline import of completed local reviews; compile and stop before Editor."""
import argparse,sys,shutil,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source','reviews','output'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();source,reviews,output=(p.resolve() for p in (a.source,a.reviews,a.output))
    from src.skill_evolution.shared.experiment_paths import resolve_artifact_path
    from src.skill_evolution.v19.evolution_replay_v19 import _load, _save, _file_digest, _lock
    from src.skill_evolution.v19.memory_store_v19 import require, load_memory
    from src.skill_evolution.v19.memory_restart_v19 import files, compatible_manifest, _ManifestView, ENTRYPOINT
    from src.skill_evolution.v19.campaign_v19 import source_manifest, _binding
    from src.skill_evolution.v19.semantics_migration_v19 import SemanticsMigration
    from src.skill_evolution.v19.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.v19.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.v19.evidence_review_run_v19 import _artifacts
    from src.skill_evolution.v19.local_generation_v19 import restore_local_audit
    from src.skill_evolution.v19.verified_compiler_v19 import PROTOCOL
    from src.skill_evolution.v18.compiler_validation_v18 import plan_payload
    from src.skill_evolution.v19.edit_tracking_v19 import encode, digest
    require(source!=output and source not in output.parents and output not in source.parents,'disjoint run directories required')
    with _lock(source),_lock(output):
        require(not output.exists(),'output exists')
        before=files(source);review_files=files(reviews);old=_load(source/'binding.json');previous=_load(source/'migration.json')
        require(old['memory_restart_sha256']==_file_digest(source/'migration.json'),'old receipt changed')
        require(files(resolve_artifact_path(previous['archive']))==previous['archive_files'],'previous archive changed')
        require(load_memory(source/'memory').head['revision']==1,'expected one committed round')
        require(not (source/'round-02/generation/editor').exists(),'Editor already started')
        require(_load(reviews/'status.json')['status']=='COMPLETE','reviews incomplete')
        g=source/'round-02/generation';upstream=_load(g/'local-reviews/upstream.json');fusion=_load(g/'local-reviews/fusion-result.json')
        rows=[]
        for issue in fusion['issues']:
            if issue['decision']!='PROPOSE':continue
            d=reviews/'proposals'/digest(issue['issue_id'])
            require(_load(d/'complete.json')=={'files':_artifacts(d)},'review checksum mismatch')
            rows.append({'input_version':'v19.3','result':_load(d/'result.json')})
        audit={**upstream,'schema_version':PROTOCOL,'issue_fusion':fusion,'evidence_reviews':rows}
        value,pairs=restore_local_audit(encode(audit))
        for request,result in pairs:
            d=reviews/'proposals'/digest(result.payload['proposal_id'])
            require(request.payload==_load(d/'input-0.json'),'review input changed')
        plan=plan_payload(value.plan)
        evo,mon=BenchmarkEvolutionV19(),BenchmarkMonitorV19()
        actual={'evolution_manifest':evo.manifest(),'monitor_manifest':mon.manifest()}
        for k,v in actual.items():compatible_manifest(old[k],v)
        stage=output.with_name('.'+output.name+'.pending-'+uuid.uuid4().hex)
        shutil.copytree(source,stage);require(files(stage)==before,'run copy mismatch')
        target=stage/'round-02/generation'
        shutil.copytree(reviews,target/'imported-review-artifacts')
        _save(target/'imported-local-audit.json',audit);_save(target/'imported-edit-plan.json',plan)
        code=source_manifest();bound=_load(target/'input.json');bound['source_files']={p.name:_file_digest(p) for p in (ROOT/'src/skill_evolution/v19').glob('*v19.py')};_save(target/'input.json',bound)
        immutable={}
        for sub in ('round-01','round-02/parent_evolution','round-02/grouping','round-02/generation/imported-review-artifacts'):
            immutable.update({str(p.relative_to(stage)):_file_digest(p) for p in (stage/sub).rglob('*') if p.is_file()})
        for name in ('imported-local-audit.json','imported-edit-plan.json'):
            immutable[str((target/name).relative_to(stage))]=_file_digest(target/name)
        receipt={**previous,'source':str(source),'archive':str(source),'archive_files':before,'original_binding':old,'replacement_sources':code,'current_manifests':actual,'reused_files':immutable,
            'completed_review_import':{'source':str(reviews),'files':review_files,'reviews':len(rows),'edit_units':len(value.plan.edit_units),'model_calls':0,'next_stage':'EDITOR'}}
        _save(stage/'migration.json',receipt)
        binding=_binding(old['config'],old['run_id'],old['initial_skill'],_ManifestView(evo,old['evolution_manifest']),_ManifestView(mon,old['monitor_manifest']))
        _save(stage/'binding.json',{**binding,'entrypoint':ENTRYPOINT,'memory_restart_sha256':_file_digest(stage/'migration.json')})
        _save(target/'validation.json',{'status':'INCOMPLETE','next_stage':'EDITOR','reason':'COMPLETED_REVIEWS_IMPORTED_AND_COMPILED'})
        require(files(source)==before and files(reviews)==review_files and source_manifest()==code,'source drift')
        stage.rename(output);SemanticsMigration(output/'migration.json').verify_reused_artifacts(output)
        print(encode({'status':'READY_FOR_EDITOR','output':str(output),'operations':[u.operation for u in value.plan.edit_units],'model_calls':0}))

if __name__=='__main__':main()
