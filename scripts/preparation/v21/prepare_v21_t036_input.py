"""Prepare the opt-in T036 wording revision through the existing v4 runtime.

No model calls. Old benchmark freezes and historical rollouts stay unchanged.
The returned orchestrator can be used by a subsequent explicit local replay.
"""
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
REVISION = ROOT / 'experiments/methods/v21/v21_t036_input_001/config'


def load(path):
    return json.loads(path.read_text())


def prepare():
    from tau2.data_model.tasks import Task
    from src.skill_evolution.v18 import benchmark_runtime_v18_v4 as runtime
    from src.skill_evolution.v18.formal_v18_v4 import frozen_policies
    from src.skill_evolution.v15.information_boundary_v15 import unpack

    revision = load(REVISION / 'revision.json')
    for path, expected in revision['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert hashlib.sha256((REVISION / 'task.json').read_bytes()).hexdigest() == revision['task_sha256']
    freeze = ROOT / revision['base_freeze']
    config = load(freeze / 'config.json')
    task_id = revision['task_id']
    registry = runtime.BenchmarkRegistry()
    original = registry.get(task_id)
    frozen_tasks = load(freeze / 'tasks.json')
    # Every existing task/spec must still match the historical freeze.
    for key, entry in registry.entries.items():
        assert {'payload': entry.payload, 'spec': entry.spec, 'split': entry.split} == frozen_tasks[key]
    payload = load(REVISION / 'task.json')
    expected = json.loads(json.dumps(original.payload))
    assert expected['user_scenario']['instructions']['reason_for_call'] == revision['before']
    expected['user_scenario']['instructions']['reason_for_call'] = revision['after']
    assert payload == expected  # Exactly one field; evaluation targets unchanged.
    registry.entries[task_id] = replace(original, payload=payload, task=Task.model_validate(payload))
    adapter = runtime.UnifiedEnvironmentAdapter(registry)
    with frozen_policies(config):
        orchestrator, view = adapter.build_orchestrator(task_id,
            base_config=config['base_config'], seed=config['seed'],
            skill_path=freeze / 'S0.md', initial_skill_path=freeze / 'S0.md')
    old_prompt = load(freeze / 'user_prompts.json')[task_id]
    prompt = orchestrator.user.prompt_record()
    assert old_prompt['system_prompt'].count(revision['before']) == 1
    assert prompt['system_prompt'] == old_prompt['system_prompt'].replace(revision['before'], revision['after'])
    assert unpack(view, 'AGENT_VISIBLE_VIEW') == load(freeze / 'contexts.json')[task_id]
    old_initial = load(ROOT / 'artifacts/methods/v20/v20_pilot_001/round-01/parent_evolution/tasks/T036/initial_db.json')
    assert orchestrator.environment.tools.db.model_dump(mode='json') == old_initial
    return orchestrator, runtime.DeterministicEvaluatorDispatcher(registry), prompt


if __name__ == '__main__':
    from loguru import logger
    logger.remove()
    orchestrator, evaluator, prompt = prepare()
    output = ROOT / 'artifacts/methods/v21/v21_t036_input_001'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'user_prompt.json').write_text(json.dumps(prompt, ensure_ascii=False, indent=2) + '\n')
    result = {'status':'INPUT_PREPARED_AND_VERIFIED', 'revision':'v21-t036-input-001',
        'model_calls':0, 'changed_task_fields':['user_scenario.instructions.reason_for_call'],
        'initial_db_unchanged':True, 'agent_visible_context_unchanged':True,
        'evaluation_targets_unchanged':True, 'other_80_tasks_unchanged':True,
        'historical_source_hashes_unchanged':True,
        'corrected_prompt_sha256':prompt['system_prompt_sha256'],
        'next_validation':'New local Parent rollout needed to inspect actual user paraphrase; no outcome claim.'}
    (output / 'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
