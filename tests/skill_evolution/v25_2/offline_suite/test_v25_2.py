"""Synthetic V25.2 routing/contract checks; no model or dataset execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from src.skill_evolution.v25_2 import diagnosis, evolution as ev, preconditioner
from src.skill_evolution.v25_2 import output_feedback as feedback
from src.skill_evolution.v25_2.benchmark import using_benchmark
from src.skill_evolution.v25_2.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25_2.benchmarks.spreadsheetbench.timeline import EXECUTION_INSTRUCTION
from src.skill_evolution.v25_2.contracts.diagnosis import validate_diagnosis
from src.skill_evolution.v25_2.prompts import render_prompt
from .support import config, ActorResponses, MethodResponses, fast_execute, response

from src.skill_evolution.v25_2.cli import EXPERIMENT

ARM = EXPERIMENT / 'config'
CFG = json.loads((ARM / 'config.json').read_text())


def configured(path):
    value = config(path)
    value['method'] = deepcopy(CFG['method'])
    value['module_max_tokens'] = deepcopy(CFG['module_max_tokens'])
    return value


def test_reviewed_prompts_reach_actual_generator_and_archive(tmp_path):
    actors, method = ActorResponses(), MethodResponses()
    adapter = SpreadsheetBenchAdapter(generate=actors, execute=fast_execute)
    root = tmp_path / 'synthetic_campaign'
    captured = {}

    def generate(messages, directory):
        result = method(messages, directory)
        captured[method.calls[-1]] = deepcopy(messages)
        return result

    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=configured(tmp_path / 'data'),
                                 generate=generate, actor_runner=adapter.actor_task)
        assert result['status'] == 'complete'
        routing = {}
        for name, key in [('diagnosis', 'diagnosis_version'),
                          ('preconditioner', 'preconditioner_prompt')]:
            path = root / 'rounds/R01' / name / 'attempts/001'
            saved = ev.read(path / 'input.json')
            expected = render_prompt(feedback.prompt_text(
                ARM / 'approved_prompts' / (name + '.md'),
                feedback.policy(feedback.saved_context(path))), saved['background'])
            if name == 'preconditioner':
                expected += '\n\n' + preconditioner.KNOWLEDGE_VIEW_PATH.read_text()
            # Both synthetic inputs contain execution-only runs; the unchanged
            # evidence adapter appends its timeline explanation to the template.
            expected = expected.rstrip() + '\n\n' + EXECUTION_INSTRUCTION
            assert captured[name][0]['content'] == expected
            assert ev.read(path / 'messages.json') == captured[name]
            assert (path / 'prompt.md').read_text() == expected
            meta = ev.read(path / 'run.json')
            assert meta['prompt_version'] == CFG['method'][key]
            routing[name] = {'selected': CFG['method'][key], 'saved': meta['prompt_version']}
        assert 'Select at most two Updates' in captured['diagnosis'][0]['content']
        assert "not the Plan's\nobservational Checks" in captured['preconditioner'][0]['content']
        diagnosis.load_diagnosis(root / 'rounds/R01/diagnosis/attempts/001')
        preconditioner.load_preconditioner(root / 'rounds/R01/preconditioner/attempts/001')
        ev.final_parent(root)
        before = len(method.calls), len(actors.calls)
        ev.run_campaign(root, resume=True, generate=generate, actor_runner=adapter.actor_task)
        assert before == (len(method.calls), len(actors.calls))
    ev.save(tmp_path / 'v25_2_routing.json', {
        'versions': routing, 'synthetic_only': True, 'real_model_requests': 0,
        'archived_prompts_match_reviewed_templates': True, 'resume_duplicate_calls': 0})


@pytest.mark.parametrize('mode', ['KEEP', 'MODIFY', 'WITHDRAW', 'NO_CHANGE'])
def test_existing_decisions_and_observational_checks_still_work(tmp_path, mode):
    actors = ActorResponses()
    method = MethodResponses(decision='no_change' if mode == 'NO_CHANGE' else 'revise')
    adapter = SpreadsheetBenchAdapter(generate=actors, execute=fast_execute)
    root = tmp_path / 'synthetic_campaign'

    def generate(messages, directory):
        result = method(messages, directory)
        value = json.loads(result['content'])
        if method.calls[-1] == 'diagnosis' and value['plan']:
            value['plan']['updates'][0]['text'] += '\n'
        if method.calls[-1] == 'preconditioner':
            item = value['adjustments'][0]
            if mode == 'MODIFY':
                old = json.loads(messages[1]['content'])['plan']['updates'][0]['text']
                new = 'Include the final data row while preserving unrelated cells and footer rows.\n'
                item.update(focus=['S'], change='Preserve footer rows while including required data rows.',
                    reason='`Evidence:P1:1` supports revising the row boundary without unrelated edits.',
                    to={'patch': '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-' + old + '+' + new})
            elif mode == 'WITHDRAW':
                item.update(focus=['D'], change='Withdraw this proposed row-boundary change.', to=[])
                value['checks'] = []
            elif mode == 'KEEP':
                # An observational Check can change even when all Updates are kept.
                value['checks'] = [{'id': 'cost_check', 'update_ids': ['u1'],
                                    'question': 'Did the proposed repair increase execution cost?'}]
        return response(json.dumps(value))

    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=configured(tmp_path / 'data'),
                                 generate=generate, actor_runner=adapter.actor_task)
        assert result['status'] == 'complete'
        if mode == 'NO_CHANGE':
            assert method.calls == ['grouping', 'diagnosis']
        else:
            archived = preconditioner.load_preconditioner(
                root / 'rounds/R01/preconditioner/attempts/001')
            if mode == 'WITHDRAW':
                assert archived['effective_plan'] is None
                assert method.calls == ['grouping', 'diagnosis', 'preconditioner']
            else:
                assert method.calls == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay']
                effective = archived['effective_plan']
                if mode == 'MODIFY':
                    assert 'footer rows' in effective['updates'][0]['text']
                else:
                    assert effective['checks'][0]['id'] == 'cost_check'
                    assert effective['updates'] == archived['diagnosis']['plan']['updates']
        ev.final_parent(root)


def test_update_ceiling_is_prompt_guidance_not_new_validator_rule():
    payload = {'grouping': {'groups': [{'group_id': 'G1', 'members': ['P1']}]},
               'runs': [{'ref': 'P1', 'attempts': [{'ref': 'P1:1'}]}]}
    value = {'decision': 'revise', 'reason': 'P1:1 motivates the proposed repairs.',
             'plan': {'goal': 'Improve input handling.', 'updates': [
                 {'id': f'u{i}', 'text': 'Preserve task requirements.', 'basis': ['P1:1']}
                 for i in range(1, 4)], 'checks': []}}
    assert validate_diagnosis(value, payload) == value


def test_v25_1_method_cannot_be_silently_used_in_v25_2():
    from src.skill_evolution.v25_2.config import validate_method
    old = deepcopy(CFG['method'])
    old['diagnosis_version'] = 'v25_diagnosis_evidence_scoped_updates_v5'
    old['preconditioner_prompt'] = 'v25_1_current_update_evidence_to_behavior_v1'
    with pytest.raises(ValueError):
        validate_method(old)
