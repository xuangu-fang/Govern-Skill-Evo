from copy import deepcopy
import json
import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.contracts import diagnosis, memory
from src.skill_evolution.v26 import knowledge_repair, knowledge_evidence, replay
from src.skill_evolution.v26.benchmarks.officeqa import facts, evidence, protocol as p


def saved_plan(records):
    saved = facts.build_facts(records)
    saved['grouping'] = {'groups': [dict(group_id=f'G{i}', members=[run['ref']],
        decision_problem='Read the relevant source.', shared_basis=f"Observed {run['ref']}:1_t1.",
        important_differences=[]) for i, run in enumerate(saved['facts']['runs'], 1)]}
    saved['diagnosis'] = {'decision': 'revise', 'reason': 'Evidence P1:1_t1 supports a focused change.',
        'plan': {'goal': 'Inspect relevant evidence.', 'updates': [
            {'id': 'U1', 'text': 'Inspect the cited document.', 'basis': ['G1', 'P1:1_t1']}], 'checks': []}}
    return saved


def proposal(text='The edited Skill accompanied a correct answer.', refs=None):
    return {'entries': [{'revises': [], 'knowledge': [{'text': text, 'evidence': refs or ['diff', 'P1:1_t1', 'Q1:outcome']}]}]}


def test_grouping_diagnosis_preconditioner_editor_views(make_bundle):
    _, adapter, parents, _ = make_bundle(two=True)
    saved = saved_plan(parents)
    with using_benchmark(adapter):
        incoming = evidence.diagnosis_input(saved)
        diagnosis.validate_diagnosis(saved['diagnosis'], incoming)
        assert set(incoming) == {'parent', 'runs', 'grouping'}
        internal = evidence.preconditioner_input(saved)
        visible = evidence.preconditioner_model_input(saved)
        assert 'grouping' in internal and 'grouping' not in visible
        assert [r['ref'] for r in visible['runs']] == ['P1']
        assert visible['memory'] == {'format': 'memory_knowledge_only_v1', 'entries': []}
        keep = {'adjustments': [{'target': 'U1', 'focus': [], 'change': 'KEEP',
                                'reason': 'Supported by `Evidence:P1:1_t1`.', 'to': None}], 'checks': None}
        editor = evidence.editor_model_input(saved, keep)
        assert set(editor) == {'parent', 'plan'} and editor['plan'] == saved['diagnosis']['plan']
        assert 'runs' not in editor and 'memory' not in editor
        withdraw = deepcopy(keep); withdraw['adjustments'][0].update(focus=['D'], change='Withdraw', to=[]); withdraw['checks'] = []
        assert evidence.editor_model_input(saved, withdraw) is None


@pytest.mark.parametrize('bad_ref', ['P1:99', 'P1:1_t3', 'P9', 'G9'])
def test_diagnosis_rejects_unavailable_evidence(make_bundle, bad_ref):
    _, adapter, parents, _ = make_bundle(); saved = saved_plan(parents)
    saved['diagnosis']['plan']['updates'][0]['basis'] = [bad_ref]
    with using_benchmark(adapter), pytest.raises(ValueError):
        diagnosis.validate_diagnosis(saved['diagnosis'], evidence.diagnosis_input(saved))


def test_diagnosis_current_decisions_and_group_coverage(make_bundle):
    _, adapter, parents, _ = make_bundle(); saved = saved_plan(parents)
    with using_benchmark(adapter):
        incoming = evidence.diagnosis_input(saved)
        diagnosis.validate_diagnosis({'decision': 'no_change', 'reason': 'No supported change', 'plan': None}, incoming)
        with pytest.raises(ValueError):
            diagnosis.validate_diagnosis({'decision': 'need_evidence', 'reason': 'Missing', 'plan': None}, incoming)
        saved['grouping']['groups'].append(deepcopy(saved['grouping']['groups'][0]))
        with pytest.raises(ValueError): evidence.diagnosis_input(saved)


def test_pairs_use_ids_not_candidate_completion_order(make_bundle):
    bundle, adapter, parents, candidates = make_bundle(two=True)
    assert [r['task_id'] for r in candidates] == ['b', 'a']
    with using_benchmark(adapter):
        view = evidence.model_input(bundle)
        assert [r['task_id'] for r in view['runs']] == ['a', 'a', 'b', 'b']
        assert [r['ref'] for r in view['runs']] == ['P1', 'Q1', 'P2', 'Q2']
        assert view['pairs'][0]['candidate_result']['em'] == 1
        assert not {'audit', 'source_assets', 'endpoint', 'sources'} & set(view)
        assert 'GOLD_ONLY_SENTINEL' not in json.dumps(view)
        assert 'request_audit' not in json.dumps(view)


@pytest.mark.parametrize('mutation', ['source', 'task', 'actor', 'role', 'same_run', 'missing', 'duplicate'])
def test_pair_incompatibilities_rejected(make_bundle, mutation):
    bundle, adapter, parents, candidates = make_bundle(two=True)
    candidates = deepcopy(candidates)
    if mutation == 'source': candidates[0]['provenance']['source_assets'][next(iter(candidates[0]['provenance']['source_assets']))]['text_sha256'] = '0' * 64
    elif mutation == 'task': candidates[0]['task']['question'] += 'changed'
    elif mutation == 'actor':
        candidates[0]['execution']['actor']['max_completion_tokens'] += 1
        candidates[0]['provenance']['record_sha256'] = p.digest(candidates[0]['execution'])
    elif mutation == 'role': candidates[0]['provenance']['role'] = 'parent'
    elif mutation == 'same_run': candidates[0]['run_id'] = parents[0]['run_id']
    elif mutation == 'missing': candidates.pop()
    elif mutation == 'duplicate': candidates[0] = deepcopy(candidates[1])
    with using_benchmark(adapter), pytest.raises(ValueError):
        evidence.build_replay_from_editor(bundle['audit']['editor'], 'offline', parents, candidates)


@pytest.mark.parametrize('ref', ['P1:1_t1', 'P1:1', 'P1:0', 'P1:outcome', 'P1', 'diff'])
def test_exact_reference_extraction(make_bundle, ref):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        extracted = evidence.extract(ref, bundle)
        if ref == 'diff': assert extracted['diff'] == bundle['payload']['diff']
        else:
            assert extracted['task_id'] == 'a' and extracted['role'] == 'parent'
            assert extracted['record']['ref'] == ref
        if ref == 'P1:1_t1':
            assert extracted['record']['call']['id'] == 'call_0'
            assert 'call_1' not in json.dumps(extracted)
            assert all(m['role'] != 'tool' for m in extracted['record']['request_messages'])
        with pytest.raises(ValueError): evidence.extract('P1:1_t99', bundle)


def test_bundle_edit_and_score_tampering_rejected(make_bundle):
    bundle, adapter, _, _ = make_bundle()
    with using_benchmark(adapter):
        for key in ('diff', 'score', 'pair', 'context'):
            bad = deepcopy(bundle)
            if key == 'diff': bad['payload']['diff'] += 'bad'
            elif key == 'score': bad['payload']['runs'][0]['outcome']['score']['em'] = 1
            elif key == 'pair': bad['pair_audit'][0]['parent_run_id'] = 'wrong'
            else: bad['execution_context']['description'] += 'wrong'
            with pytest.raises(ValueError): evidence.validate_bundle(bad)


def test_verifier_and_repair_exact_targets_and_permissions(make_bundle):
    bundle, adapter, _, _ = make_bundle(); candidate = proposal()
    with using_benchmark(adapter):
        view, inventory = evidence.build_input(bundle, candidate)
        assert set(view['source_records']) == {'diff', 'P1:1_t1', 'Q1:outcome'}
        assert inventory['candidate_items'][0]['classification'] == 'new'
        assert knowledge_evidence.verify_equivalence(view, evidence.compact(view))['entire_input_equal']
        target = {'entry_index': 0, 'knowledge_index': 0}
        verdicts = {'results': [{'target': target, 'verdict': 'CONFLICT', 'issues': [{
            'statement': 'correct answer', 'reason': 'Synthetic verdict for merge testing.', 'evidence': ['Q1:outcome']}]}]}
        repair_input = evidence.build_repair_input(view, verdicts, candidate)
        unchanged = {'changes': [{'target': target, 'knowledge': candidate['entries'][0]['knowledge'][0]}]}
        assert knowledge_repair.merge(unchanged, repair_input, candidate, bundle['payload']) == candidate
        assert candidate == proposal()
        bad = deepcopy(unchanged); bad['changes'][0]['knowledge']['evidence'].append('P1:1_t2')
        with pytest.raises(ValueError): knowledge_repair.merge(bad, repair_input, candidate, bundle['payload'])
        bad = {'changes': [{'target': target, 'knowledge': None}]}
        with pytest.raises(ValueError): knowledge_repair.merge(bad, repair_input, candidate, bundle['payload'])
        verdicts['results'][0].update(verdict='SUPPORTED', issues=[])
        assert evidence.build_repair_input(view, verdicts, candidate)['targets'] == []


def test_memory_commit_history_view_and_no_reference_expansion(make_bundle, tmp_path):
    first, adapter, _, _ = make_bundle(); first_candidate = proposal(refs=['diff', 'P1:1_t1', 'Q1:outcome'])
    directory = tmp_path / 'memory'
    with using_benchmark(adapter):
        committed = memory.commit_memory(directory, context_id='R01', context=first,
                                         result=first_candidate, memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        assert memory.commit_memory(directory, context_id='R01', context=first,
            result=first_candidate, memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT) == committed
        active = memory.load_memory(directory, memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
    second, adapter, parents, _ = make_bundle(memory=active)
    with using_benchmark(adapter):
        view = evidence.model_input(second)
        assert 'sources' not in view['memory'] and set(view['memory']) == {'format', 'entries'}
        saved = saved_plan(parents); saved['memory'] = active
        assert evidence.preconditioner_model_input(saved)['memory'] == view['memory']
        unchanged = {'entries': [{'revises': ['M1'], 'knowledge': deepcopy(active['entries'][0]['knowledge'])}]}
        no_targets, _ = evidence.build_input(second, unchanged)
        assert no_targets['targets'] == [] and no_targets['source_records'] == {}
        new = proposal('Historical comparison retained with current context.',
                       ['diff', 'Q1:outcome', 'R01/diff', 'R01/P1:1_t1'])
        checked, _ = evidence.build_input(second, new, {'R01': first})
        assert 'R01/P1:1_t1' in checked['source_records']
        with pytest.raises(ValueError): evidence.extract('R01/P1', second, {'R01': first})
        with pytest.raises(ValueError): evidence.extract('R01/P1:1_t2', second, {'R01': first})
        with pytest.raises(ValueError): replay.validate_result(proposal(refs=['diff', 'R01/P1:1_t2']), second['payload'])
        tampered = deepcopy(first); tampered['payload']['runs'][0]['outcome']['answer'] = 'tampered'
        with pytest.raises(ValueError): evidence.build_input(second, new, {'R01': tampered})


def test_explicit_gate_metric_and_strict_success_rule(make_bundle):
    for panswer, qanswer, expected in [('0', '1000', 'ACCEPT'), ('1000', '1000', 'RETAIN'), ('1000', '0', 'RETAIN')]:
        _, adapter, parents, candidates = make_bundle(parent_answer=panswer, candidate_answer=qanswer)
        kwargs = dict(parent_skill='Parent\n', candidate_skill='Candidate\n')
        with pytest.raises(ValueError, match='explicitly'): adapter.build_gate(parents, candidates, ['a'], **kwargs)
        adapter.gate_metric = p.EM_GATE
        assert adapter.build_gate(parents, candidates, ['a'], **kwargs)['result']['decision'] == expected
