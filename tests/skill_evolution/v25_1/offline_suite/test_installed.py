"""Exercise installed configuration routing, archives and actual rendered messages."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
from src.skill_evolution.v25_1 import evolution as ev, preconditioner
from src.skill_evolution.v25_1.config import validate_method, method_config
from src.skill_evolution.v25_1.benchmark import using_benchmark
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench import protocol
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from .support import config, ActorResponses, MethodResponses, fast_execute

ROOT = Path(__file__).resolve().parents[4]
ARM = ROOT / 'experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/config'
CFG = json.loads((ARM/'config.json').read_text())


def test_real_config_and_frozen_imports(tmp_path):
    report = tmp_path / 'reports'
    adapter = SpreadsheetBenchAdapter()
    with using_benchmark(adapter):
        ev.validate_config(CFG)
        ev.validate_config(json.loads((ARM/'evaluation/config.json').read_text()))
        version, prompt = preconditioner.prompt_for(CFG['method']['memory_view'],
            CFG['method']['preconditioner_contract'], CFG['method']['preconditioner_prompt'])
        approved = ARM/'bundle/approved_prompts'
        expected = approved/'v25_1/preconditioner.md'
        assert prompt.read_bytes() == expected.read_bytes()
        contract = ev.frozen_contract()
    assert set(ev.enabled_modules(CFG)) == {'grouping','diagnosis','preconditioner','editor','replay'}
    imports = {k:str(Path(v.__file__).resolve()) for k,v in list(sys.modules.items())
               if k.startswith('src.skill_evolution.v25_1') and getattr(v, '__file__', None)}
    assert imports and all(Path(p).is_relative_to(ROOT/'src/skill_evolution/v25_1') for p in imports.values())
    report.mkdir(parents=True, exist_ok=True)
    ev.save(report/'import_paths.json', imports)
    ev.save(report/'contract.json', contract)
    task = CFG['task_items'][CFG['batches'][0][0]]
    ev.save(report/'actor_messages.json', protocol.initial_messages(task, CFG['initial_skill']['text'],
        'SYNTHETIC PREVIEW: no dataset workbook read', CFG['actor_profile']))
    ev.save(report/'no_skill_messages.json', protocol.initial_messages(task, None,
        'SYNTHETIC PREVIEW: no dataset workbook read', CFG['actor_profile']))
    (report/'execution_context.md').write_text(protocol.execution_context(protocol.background(CFG['actor_profile'])))
    bad = deepcopy(CFG['method']); bad['preconditioner_prompt'] = 'unknown'
    with pytest.raises(ValueError):
        validate_method(bad)


def test_selected_version_reaches_generator_and_saved_archive(tmp_path):
    report = tmp_path / 'reports'
    cfg = config(tmp_path/'synthetic')
    cfg['method'] = deepcopy(CFG['method'])
    cfg['module_max_tokens'] = deepcopy(CFG['module_max_tokens'])
    method = MethodResponses()
    actors = ActorResponses()
    adapter = SpreadsheetBenchAdapter(generate=actors, execute=fast_execute)
    systems = {}
    def generate(messages, directory):
        result = method(messages, directory)
        systems[method.calls[-1]] = messages[0]['content']
        return result
    root = tmp_path/'synthetic_campaign'
    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=cfg, generate=generate, actor_runner=adapter.actor_task)
        assert result['status'] == 'complete'
        ev.final_parent(root)
        d = root/'rounds/R01/preconditioner/attempts/001'
        meta = ev.read(d/'run.json')
        assert meta['prompt_version'] == CFG['method']['preconditioner_prompt']
        assert (d/'prompt.md').read_text() == systems['preconditioner']
        count = len(method.calls), len(actors.calls)
        ev.run_campaign(root, resume=True, generate=generate, actor_runner=adapter.actor_task)
        assert count == (len(method.calls), len(actors.calls))
        other = preconditioner.KNOWLEDGE_PROMPT_VERSION
        with pytest.raises(ValueError, match='Saved Preconditioner prompt differs'):
            preconditioner.run_preconditioner(meta['grouping_directory'], meta['diagnosis_directory'], d,
                generate=generate, memory=meta['memory'], memory_contract=meta['memory_contract'],
                call_config=meta['call_config'], prompt_version=other)
    assert method.calls == ['grouping','diagnosis','preconditioner','editor','replay']
    report.mkdir(parents=True, exist_ok=True)
    ev.save(report/'module_system_messages.json', systems)
    ev.save(report/'routing.json', {'selected':meta['prompt_version'], 'saved':meta['prompt_version'],
        'modules':method.calls, 'real_model_requests':0, 'synthetic_only':True,
        'completed_resume_duplicate_calls':0, 'cross_version_resume_rejected':True})
