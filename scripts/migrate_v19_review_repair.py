"""Copy a stopped campaign, preserve completed reviews, prepare one unsent repair."""
import argparse
import sys
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();source=args.source.resolve();output=args.output.resolve()
    from src.skill_evolution.memory_restart_v19 import files,compatible_manifest,_ManifestView,ENTRYPOINT
    from src.skill_evolution.semantics_migration_v19 import SemanticsMigration
    from src.skill_evolution.campaign_v19 import source_manifest,_binding
    from src.skill_evolution.evolution_replay_v19 import _lock,_load,_save,_file_digest
    from src.skill_evolution.memory_store_v19 import require,load_memory
    from src.skill_evolution.edit_tracking_v19 import encode,digest
    from src.skill_evolution.edit_memory_review_v19 import validate_packet,build_packet_request,MAX_INPUT_TOKENS
    from src.skill_evolution.review_contract_v19 import MemoryReviewInput
    from src.skill_evolution.memory_review_repair_v19 import build_repair
    from src.skill_evolution.memory_generation_v19 import _prepared,_read_call
    from src.skill_evolution.evidence_review_prompt_v19 import check_review_budget
    from src.skill_evolution.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.monitor_campaign_v19 import BenchmarkMonitorV19
    import uuid
    require(source!=output and source not in output.parents and output not in source.parents,'disjoint paths required')
    with _lock(source),_lock(output):
        require(not output.exists(),'output already exists')
        before=files(source);old=_load(source/'binding.json');previous=_load(source/'migration.json')
        require(old['memory_restart_sha256']==_file_digest(source/'migration.json'),'prior migration changed')
        require(files(Path(previous['archive']))==previous['archive_files'],'prior archive changed')
        snapshot=load_memory(source/'memory');require(snapshot.head['revision']==1,'expected one committed round')
        require(not (source/'round-02/generation/local-reviews').exists(),'downstream already exists')
        evo,mon=BenchmarkEvolutionV19(),BenchmarkMonitorV19()
        actual={'evolution_manifest':evo.manifest(),'monitor_manifest':mon.manifest()}
        for key,value in actual.items():compatible_manifest(old[key],value)
        stage=output.with_name('.'+output.name+'.pending-'+uuid.uuid4().hex)
        shutil.copytree(source,stage);require(files(stage)==before,'copy mismatch')
        g=stage/'round-02/generation';root=g/'edit-memory-reviews'
        dirs=sorted(p for p in root.iterdir() if p.is_dir() and (p/'input.json').exists())
        failed=[];complete=[]
        for d in dirs:
            packet=MemoryReviewInput(encode(_load(d/'input.json')))
            if (d/'result.json').exists():
                saved=_load(d/'result.json');require(validate_packet(saved['raw_response'],packet).payload==saved,'saved review invalid');complete.append(d)
            else:failed.append(d)
        require(len(failed)==1,'exactly one failed edit required')
        d=failed[0];packet=MemoryReviewInput(encode(_load(d/'input.json')))
        raw=_read_call(d/'review',_load(d/'review/request.json'))
        try:validate_packet(raw,packet)
        except ValueError as exc:error={'type':type(exc).__name__,'message':str(exc),'raw_response_sha256':digest(raw)}
        else:raise ValueError('original response passed; no repair needed')
        repair=d/'review-repair-001'
        require(not (repair/'response.json').exists() and not (repair/'response_complete.json').exists(),'repair may have been sent')
        require(_load(repair/'failure.json')=={'error_type':'MemoryRejected'},'expected local budget rejection')
        old_req=_load(repair/'request.json');require(old_req['input_budget']['proxy_input_tokens']>MAX_INPUT_TOKENS,'not an over-budget unsent repair')
        (d/'archived-unsent-repair').mkdir();repair.rename(d/'archived-unsent-repair/review-repair-001')
        prepared=_prepared(build_repair(build_packet_request(packet),raw,error));check_review_budget(prepared,MAX_INPUT_TOKENS)
        _save(d/'pending-repair-request.json',prepared)
        protected={str(p.relative_to(root)):_file_digest(p) for p in root.rglob('*') if p.is_file()
                   and (any(p.is_relative_to(x) for x in complete) or p.is_relative_to(d/'review') or p.is_relative_to(d/'archived-unsent-repair') or p.name in ('input.json','pending-repair-request.json'))}
        _save(root/'repair-migration.json',{'schema_version':'edit_review_repair_migration_v19.1','source_input_ref':_load(root/'binding.json')['source_input_ref'],
              'directories':[p.name for p in dirs],'failed_directory':d.name,'preserved_files':protected})
        code=source_manifest();bound=_load(g/'input.json');bound['source_files']={p.name:_file_digest(p) for p in (ROOT/'src/skill_evolution').glob('*v19.py')};_save(g/'input.json',bound)
        immutable={str(p.relative_to(stage)):_file_digest(p) for sub in ('round-01','round-02/parent_evolution','round-02/grouping') for p in (stage/sub).rglob('*') if p.is_file()}
        for p in g.glob('current-*'):
            if p.is_file():immutable[str(p.relative_to(stage))]=_file_digest(p)
            else:immutable.update({str(f.relative_to(stage)):_file_digest(f) for f in p.rglob('*') if f.is_file()})
        immutable.update({str((root/n).relative_to(stage)):h for n,h in protected.items()})
        immutable[str((root/'repair-migration.json').relative_to(stage))]=_file_digest(root/'repair-migration.json')
        receipt={**previous,'source':str(source),'archive':str(source),'archive_files':before,'original_binding':old,
            'replacement_sources':code,'current_manifests':actual,'reused_files':immutable,
            'repair_migration':{'preserved_completed':len(complete),'repair_tokens':prepared['input_budget']['proxy_input_tokens'],'model_calls':0}}
        _save(stage/'migration.json',receipt)
        binding=_binding(old['config'],old['run_id'],old['initial_skill'],_ManifestView(evo,old['evolution_manifest']),_ManifestView(mon,old['monitor_manifest']))
        _save(stage/'binding.json',{**binding,'entrypoint':ENTRYPOINT,'memory_restart_sha256':_file_digest(stage/'migration.json')})
        require(files(source)==before and source_manifest()==code,'source drift during migration')
        stage.rename(output);SemanticsMigration(output/'migration.json').verify_reused_artifacts(output)
        print(encode({'status':'READY','output':str(output),**receipt['repair_migration']}))

if __name__=='__main__':main()
