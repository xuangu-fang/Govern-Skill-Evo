from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor import binding
from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM, UPSTREAM_CONFIG
from .support import config, fast_execute, response, CODE

HOME = binding.HOME
REFERENCES = Path(__file__).parent / 'references'
PATCH = '{"reasoning":"Use the observed row-boundary correction.","patch":"--- a/SKILL.md\\n+++ b/SKILL.md\\n@@ -1 +1 @@\\n-Original\\n+Updated\\n"}'


def test_actual_config_prompt_and_native_settings(tmp_path):
    native,bridge,shared,cfg = binding.components()
    assert (HOME/'skilladam.json').read_bytes() == (UPSTREAM_CONFIG/'skilladam.json').read_bytes()
    checkpoint = bridge.read(REFERENCES/'upstream_run_signature.json')
    assert bridge.native_config(cfg).to_dict() == checkpoint['post_decision']['run_config']
    assert asdict(bridge.context_for(shared,cfg)) == checkpoint['post_decision']['backend_context']
    from skilladam.methods.skilladam import _profile_gate, _gate_signature
    gate = _profile_gate(bridge.AlignedAdapter(HOME),'spreadsheetbench',None,cfg['native']['gate_profile'])
    assert _gate_signature(gate,'spreadsheetbench',None,cfg['native']['gate_profile']) == checkpoint['gate']
    task = shared['task_items'][shared['batches'][0][0]]
    actual = bridge.protocol.initial_messages(task,shared['initial_skill']['text'],
        'SYNTHETIC PREVIEW: no dataset workbook read',shared['actor_profile'])
    expected = bridge.read(REFERENCES/'actor_messages.json')
    assert actual == expected
    no_skill = bridge.protocol.initial_messages(task,None,
        'SYNTHETIC PREVIEW: no dataset workbook read',shared['actor_profile'])
    assert no_skill == bridge.read(REFERENCES/'no_skill_messages.json')
    assert native.backend_type(bridge).execute_batch is bridge.SharedBackend.execute_batch
    imported = {k:str(Path(v.__file__).resolve()) for k,v in list(sys.modules.items())
                if (k.startswith('src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime') or k.startswith('skilladam.')) and getattr(v,'__file__',None)}
    assert imported and all(Path(v).is_relative_to(UPSTREAM if k.startswith('skilladam.') else Path(binding.__file__).parent/'actor_runtime') for k,v in imported.items())
    bridge.write(tmp_path/'actor_messages.json',actual)
    bridge.write(tmp_path/'import_paths.json',imported)
    bridge.write(tmp_path/'native_settings.json',{'run_config_matches_completed_run':True,
        'gate_matches_completed_run':True,'backend_context_matches_completed_run':True,
        'actor_messages_equal_v25_1':True,'optimizer_config_byte_identical':True})


@pytest.mark.parametrize('improve',[True,False])
def test_native_pipeline_keeps_compression_gate_momentum_and_history(tmp_path,improve):
    from skilladam.execution.contracts import GenerationResult
    native,bridge,shared,cfg = binding.components()
    fixture = config(tmp_path/'data',n=1)
    for k in ['dataset','task_items','batches','test_tasks']:
        shared[k] = fixture[k]
    task = shared['batches'][0][0]
    shared['actor_max_workers'] = 1
    cfg['native']['optimization_case_ids'] = [task]
    cfg['native'].update(train_size=1,validation_size=1,stage0_size=1)
    cfg['native']['feedback_loop'].update(max_iterations=1,min_iterations=1)
    before = deepcopy(cfg)
    requests=[]; calls=[]; seen=set()
    class Optimizer:
        def generate(self,request):
            requests.append(request)
            return GenerationResult(PATCH if request.stage=='iteration_patch' else 'Observed execution only.')
    backend = native.backend_type(bridge)(shared,cfg,tmp_path/'native',optimizer=Optimizer())
    runner = bridge.AlignedRunner(config=bridge.native_config(cfg),adapter=bridge.AlignedAdapter(HOME),
        backend=backend,context=bridge.context_for(shared,cfg),output_dir=tmp_path/'native')
    real_run = bridge.actor.run
    def generate(messages,directory,*args):
        calls.append(deepcopy(messages));slot=Path(directory).parent
        if slot not in seen:
            seen.add(slot)
            return response('PRIVATE_FORMAT_SENTINEL')
        correct = improve and 'Updated' in messages[0]['content']
        return response('```python\n'+CODE%(' + 1' if correct else '')+'```')
    def run(*args,**kwargs):
        return real_run(*args,**kwargs,generate=generate,execute=fast_execute)
    with patch.object(bridge.actor,'run',side_effect=run):
        result=runner.run(cases=bridge.cases_for(shared,cfg),initial_skill='Original\n')
    assert [r.stage for r in requests]==['trajectory_compression','iteration_patch','momentum_update']
    assert result.feedback_loop.iterations[0].accepted is improve
    assert result.final_skill == ('Updated\n' if improve else 'Original\n')
    assert len(calls)==6 and len(seen)==3
    assert cfg == before
    for request in requests:
        assert 'PRIVATE_FORMAT_SENTINEL' not in json.dumps([dict(m) for m in request.messages])
    state=bridge.read(tmp_path/'native/checkpoint.json')
    assert state['next_iteration']==1 and state['pending_post_decision'] is None
    # Full-completion resume must reuse all results, without new Actor/optimizer calls.
    before_calls=(len(requests),len(calls))
    with patch.object(bridge.actor,'run',side_effect=AssertionError('Unexpected repeated Actor')):
        resumed=runner.run(cases=bridge.cases_for(shared,cfg),initial_skill='Original\n',resume=True)
    assert (len(requests),len(calls))==before_calls and resumed.final_skill==result.final_skill


def test_fractional_score_conversion_and_tamper_rejection(tmp_path):
    native,bridge,shared,cfg=binding.components()
    fixture=config(tmp_path/'data',n=1)
    task=next(iter(fixture['task_items'].values()))
    task['answer_region']='Sheet1!A1:C3'
    record=bridge.read(bridge.actor.run(task,'Original\n',tmp_path/'actor',shared,
        generate=lambda *a:response('```python\n'+CODE%('')+'```'),execute=fast_execute))
    raw=bridge.convert_record(record)
    assert raw['n_cells_match']==8 and raw['n_cells_total']==9 and raw['per_cell_pass_rate']==0.8889
    record['score']['per_cell_pass_rate']=8/9
    bridge.convert_record(record)
    record['score']['per_cell_pass_rate']=0.889
    with pytest.raises(ValueError,match='Score counts/rates differ'):
        bridge.convert_record(record)
