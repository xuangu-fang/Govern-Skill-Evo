"""Offline copy migration before an entirely unsent Issue Fusion stage."""
import argparse,sys,shutil,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'external/tau2-bench/src')]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','output'):ap.add_argument('--'+k,type=Path,required=True)
    args=ap.parse_args();source=args.source.resolve();output=args.output.resolve()
    from src.skill_evolution.memory_restart_v19 import files,compatible_manifest,_ManifestView,ENTRYPOINT
    from src.skill_evolution.campaign_v19 import source_manifest,_binding
    from src.skill_evolution.semantics_migration_v19 import SemanticsMigration
    from src.skill_evolution.evolution_replay_v19 import _load,_save,_file_digest,_lock
    from src.skill_evolution.memory_store_v19 import load_memory,require
    from src.skill_evolution.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.current_diagnosis_v19 import validate_current_batch
    from src.skill_evolution.review_contract_v19 import CurrentDiagnosisInput,CurrentFindings,MemoryReviewInput
    from src.skill_evolution.edit_tracking_v19 import encode
    from src.skill_evolution.edit_memory_review_v19 import packet_profile
    require(source!=output and source not in output.parents and output not in source.parents,'disjoint paths required')
    with _lock(source),_lock(output):
        require(not output.exists(),'output exists');before=files(source)
        old=_load(source/'binding.json');previous=_load(source/'migration.json')
        require(old['memory_restart_sha256']==_file_digest(source/'migration.json'),'receipt changed')
        require(files(Path(previous['archive']))==previous['archive_files'],'archive changed')
        snapshot=load_memory(source/'memory');rd=f"round-{snapshot.head['revision']+1:02d}";g=source/rd/'generation'
        require((g/'historical-reviews.json').exists() and not (g/'local-reviews/fusion/request.json').exists(),'expected completed Memory Review and unsent Fusion')
        from src.skill_evolution.local_generation_v19 import restore_upstream
        from src.skill_evolution.issue_fusion_v19 import build_issue_fusion_input
        from src.skill_evolution.issue_fusion_prompt_v19 import build_issue_fusion_request
        local=g/'local-reviews';upstream=_load(local/'upstream.json')
        review,historical=restore_upstream(upstream)
        fusion=build_issue_fusion_input(review_request=review,historical_reviews=historical)
        require(fusion.payload==_load(local/'fusion-input.json'),'fusion input changed')
        fusion_request=build_issue_fusion_request(fusion)
        bound=_load(g/'input.json')
        requests=[CurrentDiagnosisInput(encode(r['payload']),encode(r['provenance'])) for r in bound['current_inputs']]
        findings=[CurrentFindings(encode(_load(g/f'current-{i:03d}-findings.json'))) for i in range(len(requests))]
        validate_current_batch(requests,findings)
        profile=packet_profile(MemoryReviewInput(encode(_load(g/'memory-review-input.json'))))
        require(all(x['within_budget'] for x in profile['edits']),'new budget still exceeded')
        evo,mon=BenchmarkEvolutionV19(),BenchmarkMonitorV19();actual={'evolution_manifest':evo.manifest(),'monitor_manifest':mon.manifest()}
        for k,v in actual.items():compatible_manifest(old[k],v)
        code=source_manifest();stage=output.with_name('.'+output.name+'.pending-'+uuid.uuid4().hex)
        shutil.copytree(source,stage);require(files(stage)==before,'copy mismatch')
        bound['source_files']={p.name:_file_digest(p) for p in (ROOT/'src/skill_evolution').glob('*v19.py')};_save(stage/rd/'generation/input.json',bound)
        local_binding=_load(stage/rd/'generation/local-reviews/binding.json')
        local_binding['source_files']={p.name:_file_digest(p) for p in (ROOT/'src/skill_evolution').glob('*.py')}
        _save(stage/rd/'generation/local-reviews/binding.json',local_binding)
        reused={k:v for k,v in before.items() if k.startswith(('round-','memory/rounds/')) and k not in (f'{rd}/generation/input.json',f'{rd}/generation/validation.json',f'{rd}/generation/local-reviews/binding.json',f'{rd}/generation/local-reviews/status.json') and not k.endswith('.lock')}
        receipt={**previous,'source':str(source),'archive':str(source),'archive_files':before,'original_binding':old,'replacement_sources':code,'current_manifests':actual,'reused_files':reused,
            'budget_migration':{'round_id':rd,'memory_revision':snapshot.head['revision'],'current_diagnoses':len(findings),'review_profile':profile,'fusion_input_tokens':fusion_request['input_budget']['proxy_input_tokens'],'next_stage':'ISSUE_FUSION','model_calls':0}}
        _save(stage/'migration.json',receipt)
        binding=_binding(old['config'],old['run_id'],old['initial_skill'],_ManifestView(evo,old['evolution_manifest']),_ManifestView(mon,old['monitor_manifest']))
        _save(stage/'binding.json',{**binding,'entrypoint':ENTRYPOINT,'memory_restart_sha256':_file_digest(stage/'migration.json')})
        require(files(source)==before and source_manifest()==code,'source drift')
        stage.rename(output);SemanticsMigration(output/'migration.json').verify_reused_artifacts(output)
        print(encode({'status':'READY','output':str(output),'round':rd,'memory_revision':snapshot.head['revision'],'current_diagnoses':len(findings),'edits':profile['edit_count'],'model_calls':0}))
if __name__=='__main__':main()
