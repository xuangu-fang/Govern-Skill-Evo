"""One isolated offline revision: same ancestor, independent sibling-edit feedback."""
from copy import deepcopy
from pathlib import Path
import json
import sys
from .run import core, HERE as FIRST, ROOT, NEW, PROMPT
from src.skill_evolution.v23 import memory

HERE=FIRST/'round2'
core.HERE=HERE

def inputs(label,stage):
    assert label=='ROUND2' and stage=='replay'
    return core.read(HERE/'config/replay_bundle.json'),core.read(HERE/'config/messages.json')

core.inputs=inputs

def prepare():
    first_freeze=core.read(FIRST/'config/freeze.json')
    assert all(core.sha(ROOT/p)==d for p,d in first_freeze['sha256'].items())
    lineage=core.read(FIRST/'LINEAGE.json')
    chosen=lineage['selected_second_feedback']
    assert not chosen['run_id_overlap_with_all_first_input_contexts']
    assert chosen['raw_record_rebuild_equals_archive'] and chosen['shared_exact_parent']
    assert all(core.sha(ROOT/p)==h for p,h in lineage['frozen_files'].items())
    source=ROOT/chosen['source'];assert core.sha(source)==chosen['sha256']
    bundle=core.read(source)
    preview=core.resolve(FIRST/'cases/R05/memory_preview')
    loaded=memory.load_memory(preview,memory_contract=NEW)
    assert loaded==core.read(FIRST/'cases/R05/results/memory_candidate.json')
    assert memory.normalize_memory(bundle['payload']['memory'],source_contract=memory.LEGACY_CONTRACT)==core.read(
        FIRST.with_name('multi_knowledge_p4_001')/'cases/R05/replay_bundle.json')['payload']['memory']
    bundle['payload']['memory']=loaded
    sources=core.replay.history_pair_sources(preview,loaded,memory_contract=NEW)
    messages=core.replay.messages_for(bundle,history_sources=sources,memory_contract=NEW,
        prompt_version=core.replay.LEARNING_PROMPT_VERSION)
    prefix=core.replay.LEARNING_PROMPT_PATH.read_text().rstrip()
    assert messages[0]['content'].startswith(prefix+'\n\n')
    messages[0]['content']=PROMPT.read_text().rstrip()+messages[0]['content'][len(prefix):]
    core.save(HERE/'config/replay_bundle.json',bundle)
    core.save(HERE/'config/history_pair_sources.json',sources)
    core.save(HERE/'config/messages.json',messages)
    core.save(HERE/'config/model_input.json',json.loads(messages[1]['content']))
    core.save(HERE/'config/CONTROL.json',{'classification':lineage['classification'],
        'raw_first_round_memory_used_unchanged':True,'not_semantically_approved':True,
        'second_feedback_source':chosen,'single_logical_call':True,
        'historical_execution_order_reversed_for_offline_ingestion':True})
    files=[Path(__file__),FIRST/'check_round2.py',FIRST/'lineage.py',FIRST/'LINEAGE.json',source,PROMPT,
           *preview.rglob('*.json'),*core.archive_glob(HERE/'config', '*.json')]
    frozen={**first_freeze['sha256'],**lineage['frozen_files']}
    frozen.update({str(p.relative_to(ROOT)):core.sha(p) for p in files})
    core.save(HERE/'config/freeze.json',{'at':core.now(),'call_config':first_freeze['call_config'],
        'max_restarts':3,'max_logical_calls':1,'max_http_attempts':4,'memory_contract':NEW,
        'prompt_version':first_freeze['prompt_version'],'sha256':frozen})
    core.verify()
    print(json.dumps({'prepared':True,'user_chars':len(messages[1]['content']),
        'raw_memory_entries':len(loaded['entries']),'classification':lineage['classification']}))

def audit():
    core.verify();core.load('ROUND2','replay')
    attempts=[];cfg=core.read(HERE/'config/freeze.json')['call_config']
    for p in core.archive_glob(HERE/'runs/ROUND2_replay', 'attempt_*'):
        a=core.read(p/'attempt.json');r=core.read(p/'http/request.json')
        expected={k:v for k,v in cfg.items() if k not in ('endpoint','timeout_seconds')}
        expected.update(messages=inputs('ROUND2','replay')[1],max_tokens=a['max_tokens'])
        assert r['body']==expected and r['transport_retries']==0
        response=core.read(p/'response.json') if core.resolve(p/'response.json').exists() else {}
        attempts.append({**a,'usage':response.get('usage'),'finish_reason':response.get('finish_reason')})
    assert len(attempts)<=4
    out={'attempts':attempts,'first_legal_output_only':True,'semantic_resampling':False}
    (HERE/'AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':core.run('ROUND2','replay')
    elif sys.argv[1]=='audit':audit()
