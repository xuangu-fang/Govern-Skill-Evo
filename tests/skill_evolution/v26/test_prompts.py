"""No provider calls: actual evidence projections + inherited output validators."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tarfile

import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa import evidence, facts, prompting as pr
from src.skill_evolution.v26.benchmarks.officeqa.input_view import restore
from src.skill_evolution.v26.contracts import diagnosis, grouping, memory
from src.skill_evolution.v26 import knowledge_verifier, knowledge_repair, replay, unnumbered_patch
from .test_evidence import saved_plan, proposal
from .conftest import response


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'artifacts/methods/v26/inheritance_20261028_001'
AUDIT = ROOT / 'artifacts/methods/v26/prompts_20261029_001'


def keep():
    return {'adjustments': [{'target': 'U1', 'focus': [], 'change': 'KEEP',
                            'reason': 'The scope remains supported by `Evidence:P1:1_t1`.', 'to': None}],
            'checks': None}


def conflict():
    return {'results': [{'target': {'entry_index': 0, 'knowledge_index': 0}, 'verdict': 'CONFLICT',
                        'issues': [{'statement': 'correct answer', 'reason': 'Fixture issue, not a semantic verdict.',
                                    'evidence': ['Q1:outcome']}]}]}


def payload(messages):
    assert [m['role'] for m in messages] == ['system', 'user']
    assert not re.search(r'\{\{(?:execution_context|recorded_context|actor_base_prompt)\}\}', messages[0]['content'])
    return restore(json.loads(messages[1]['content']))


def test_seven_builders_use_existing_projections_without_extra_evidence(make_bundle):
    bundle, adapter, parents, _ = make_bundle(two=True)
    saved = saved_plan(parents); candidate = proposal()
    before = deepcopy((bundle, saved, candidate))
    with using_benchmark(adapter):
        verifier, _ = evidence.build_input(bundle, candidate)
        messages = {
            'grouping': pr.grouping_messages(saved),
            'diagnosis': pr.diagnosis_messages(saved),
            'preconditioner': pr.preconditioner_messages(saved),
            'editor': pr.editor_messages(saved, keep()),
            'replay': pr.replay_messages(bundle),
            'verifier': pr.verifier_messages(bundle, candidate),
            'repair': pr.repair_messages(verifier, conflict(), candidate),
        }
        expected = [saved['facts'], evidence.diagnosis_input(saved), evidence.preconditioner_model_input(saved),
                    evidence.editor_model_input(saved, keep()), evidence.model_input(bundle), verifier,
                    evidence.build_repair_input(verifier, conflict(), candidate)]
        for (module, msgs), view in zip(messages.items(), expected):
            assert payload(msgs) == view
            system = msgs[0]['content']
            assert 'OfficeQA' in system and '<actor_base_protocol>' in system
            assert not any(word in system for word in ('SpreadsheetBench', 'worksheet', 'workbook',
                                                       'per_cell_pass_rate', 'executed_code', 'INPUT_PATH'))
            assert 'GOLD_ONLY_SENTINEL' not in json.dumps(msgs)
            assert 'UNOBSERVED_PAGE_SENTINEL' not in json.dumps(msgs)
            assert 'request_audit' not in msgs[1]['content']
            assert pr.prompt_identity(module)['prompt_version'] == pr.PROMPT_VERSIONS[module]
        assert len(payload(messages['preconditioner'])['runs']) == 1
        assert 'grouping' not in payload(messages['preconditioner'])
        assert set(payload(messages['editor'])) == {'parent', 'plan'}
        assert set(payload(messages['verifier'])['source_records']) == {'diff', 'P1:1_t1', 'Q1:outcome'}
        assert adapter.gate_metric is None  # Rendering does not select an experiment metric.
    assert (bundle, saved, candidate) == before


def test_no_work_branches_and_all_keep(make_bundle):
    bundle, adapter, parents, _ = make_bundle(); saved = saved_plan(parents)
    with using_benchmark(adapter):
        assert pr.editor_messages(saved, keep()) is not None
        withdraw = keep(); withdraw['adjustments'][0].update(focus=['D'], change='Withdraw', to=[])
        withdraw['checks'] = []
        assert pr.editor_messages(saved, withdraw) is None
        assert pr.verifier_messages(bundle, {'entries': []}) is None
        view, _ = evidence.build_input(bundle, proposal())
        verdict = conflict(); verdict['results'][0].update(verdict='SUPPORTED', issues=[])
        assert pr.repair_messages(view, verdict, proposal()) is None
        saved['diagnosis'] = {'decision': 'no_change', 'reason': 'No justified update.', 'plan': None}
        with pytest.raises(ValueError, match='revise'): pr.preconditioner_messages(saved)


def test_retry_audit_not_serialized_as_method_evidence(make_run):
    bad = {'choices': [{'finish_reason': 'stop', 'message': {'content': None, 'tool_calls': 'BAD_TYPE'}}]}
    record, adapter, provider, _ = make_run([bad, response('1000')])
    saved = facts.build_facts([record])
    with using_benchmark(adapter):
        view = payload(pr.grouping_messages(saved))
    run = view['runs'][0]
    assert run['outcome']['api_requests'] == 2 and run['outcome']['model_rounds'] == 1
    assert len(provider.requests) == 2
    assert 'BAD_TYPE' not in json.dumps(view)
    assert run['attempts'][0]['request_messages'] == run['initial']['messages']


def test_all_output_contracts_remain_usable_with_prompt_inputs(make_bundle):
    bundle, adapter, parents, _ = make_bundle(); saved = saved_plan(parents); candidate = proposal()
    with using_benchmark(adapter):
        grouping.validate_grouping(saved['grouping'], payload(pr.grouping_messages(saved)))
        diagnosis.validate_diagnosis(saved['diagnosis'], payload(pr.diagnosis_messages(saved)))
        editor_input = payload(pr.editor_messages(saved, keep()))  # Validates Preconditioner/compiler.
        assert editor_input['plan']['updates'][0]['id'] == 'U1'
        patch = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Parent\n+Candidate\n'
        assert unnumbered_patch.apply_patch(editor_input['parent'], patch) == 'Candidate\n'
        replay.validate_result(candidate, bundle['payload'])
        view = payload(pr.verifier_messages(bundle, candidate))
        knowledge_verifier.validate_result(conflict(), view)
        repair_view = payload(pr.repair_messages(view, conflict(), candidate))
        repaired = {'changes': [{'target': {'entry_index': 0, 'knowledge_index': 0},
                                 'knowledge': candidate['entries'][0]['knowledge'][0]}]}
        assert knowledge_repair.merge(repaired, repair_view, candidate, bundle['payload']) == candidate


def test_historical_knowledge_only_and_exact_target_source_scope(make_bundle, tmp_path):
    first, adapter, _, _ = make_bundle(); first_candidate = proposal()
    with using_benchmark(adapter):
        memory.commit_memory(tmp_path / 'memory', context_id='R01', context=first, result=first_candidate,
                             memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        active = memory.load_memory(tmp_path / 'memory', memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
    bundle, adapter, parents, _ = make_bundle(memory=active)
    saved = saved_plan(parents); saved['memory'] = active
    candidate = proposal(refs=['diff', 'Q1:outcome', 'R01/diff', 'R01/P1:1_t1'])
    with using_benchmark(adapter):
        for messages in (pr.preconditioner_messages(saved), pr.replay_messages(bundle)):
            view = payload(messages)
            assert set(view['memory']) == {'format', 'entries'}
            assert 'sources' not in view['memory']
            assert 'R01/P1:1_t1' in json.dumps(view['memory'])
        view = payload(pr.verifier_messages(bundle, candidate, {'R01': first}))
        assert set(view['source_records']) == set(candidate['entries'][0]['knowledge'][0]['evidence'])
        single = view['source_records']['R01/P1:1_t1']
        assert single['record']['call']['id'] == 'call_0' and 'call_1' not in json.dumps(single)
        with pytest.raises(ValueError, match='historical'): pr.verifier_messages(bundle, candidate)


@pytest.mark.parametrize('key', ['../diagnosis.md', '/tmp/editor.md', 'preconditioner_legacy_v8.md',
                               'replay_exact_code_view.md', 'missing.md'])
def test_resources_reject_wrong_versions_and_paths(make_bundle, key):
    _, adapter, _, _ = make_bundle()
    with pytest.raises(ValueError): adapter.resource(key)


def test_resource_freezing_and_version_identity(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        frozen = adapter.frozen_files()
        assert all(any(key.endswith('/prompts/' + name) for key in frozen) for name in pr.RESOURCE_NAMES)
        for module in pr.PROMPT_VERSIONS:
            identity = pr.prompt_identity(module)
            for name, sha in identity['resources_sha256'].items():
                assert sha == hashlib.sha256(adapter.resource(name).read_bytes()).hexdigest()
            with pytest.raises(ValueError, match='version'):
                pr.render(module, bundle['background'], prompt_version='v25_preconditioner_scope_aware_keep_v8')
    with pytest.raises(RuntimeError, match='Bind'): pr.prompt_identity('replay')


def test_background_settings_are_recorded_and_not_replaced(make_bundle):
    bundle, adapter, _, _ = make_bundle(); bg = deepcopy(bundle['background'])
    bg['max_completion_tokens'] = 777; bg['model'] = 'literal {{actor_base_prompt}}'
    with using_benchmark(adapter):
        system = pr.execution_context(bg)
        assert '"max_completion_tokens":777' in system
        assert 'literal {{actor_base_prompt}}' in system
        assert '"request_timeout_seconds":300' in system
        assert '"max_total_tool_calls":null' in system
        bg['private_endpoint'] = 'PRIVATE_SENTINEL'
        with pytest.raises(ValueError, match='Noncanonical'): pr.execution_context(bg)


def test_validation_diagnostic_is_literal_and_has_no_execution_side_effect(make_bundle):
    _, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        result = pr.validation_feedback(location='changes[0] {{error}}', error='Missing field')
    assert 'changes[0] {{error}}' in result and 'Error: Missing field' in result


def test_prompt_migration_is_frozen_v25_plus_audited_changes():
    manifest = json.loads((BASE / 'baseline_manifest.json').read_text())
    audit = json.loads((AUDIT / 'migration.json').read_text())
    assert audit['snapshot_sha256'] == manifest['snapshot']['sha256']
    with tarfile.open(BASE / 'source_snapshot.tar.gz') as archive:
        for module, row in audit['files'].items():
            raw = archive.extractfile(row['source']).read()
            assert hashlib.sha256(raw).hexdigest() == row['source_sha256']
            migrated = raw.decode()
            for change in audit['changes']:
                if change['module'] == module:
                    assert migrated.count(change['before']) == change['occurrences']
                    migrated = migrated.replace(change['before'], change['after'])
            actual = (ROOT / row['path']).read_text()
            assert actual == migrated
            assert hashlib.sha256(actual.encode()).hexdigest() == row['sha256']
            if module in pr.PROMPT_VERSIONS: assert row['version'] == pr.PROMPT_VERSIONS[module]
        # The selected v7 must really be the snapshot's default, not v8's scope-aware Keep.
        v7 = 'src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts/preconditioner_legacy_v7.md'
        assert archive.extractfile(v7).read() == archive.extractfile(audit['files']['preconditioner']['source']).read()


@pytest.mark.parametrize('module,marker', [
    ('diagnosis', '## 5. Output Format'), ('preconditioner', '## 7. Exact output contract'),
    ('editor', '## 3. Produce an Unnumbered Diff Patch'), ('replay', '## 7. Output contract'),
    ('repair', 'OUTPUT\n')])
def test_core_output_contract_text_unchanged(module, marker):
    source = f'src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts/{module}.md'
    with tarfile.open(BASE / 'source_snapshot.tar.gz') as archive:
        old = archive.extractfile(source).read().decode().split(marker, 1)[1]
    new = pr.resource_path(f'{module}.md').read_text().split(marker, 1)[1]
    if module == 'replay':
        old, new = (s.split('## Current pairing view')[0] for s in (old, new))
    assert new == old
