from copy import deepcopy

import pytest

from tests.skill_evolution.test_memory_update_v21 import (
    update_input, completed, setup, case, response as update_response, fresh_event, completion,
)
from tests.skill_evolution.test_memory_generation_v19 import current
from tests.skill_evolution.test_separated_review_v19 import inputs, response as finding_response
from tests.skill_evolution.test_local_generation_v20 import proposal, final, compiled, editor_raw
from src.skill_evolution.edit_tracking_v19 import encode, parse
from src.skill_evolution.evidence_wire_v21 import expand
from src.skill_evolution.current_diagnosis_v19 import validate_current_findings
from src.skill_evolution.issue_fusion_v20 import validate_issue_fusion
from src.skill_evolution.evidence_review_v20 import validate_evidence_review, build_evidence_review_request
from src.skill_evolution.local_generation_v20 import (
    review_inputs, compile_verified, verified_editor_request, apply_verified_editor,
)
from src.skill_evolution.memory_update_v21 import validate_memory_update
from src.skill_evolution.modification_evidence_v21 import (
    ModificationEvidence, build_modification_evidence, open_memory_evidence,
)
from src.skill_evolution.memory_consumption_v21 import (
    GenerationInput, build_issue_fusion_input, build_issue_fusion_request,
    build_generation_input, run_local_generation, restore_generation,
)


@pytest.fixture
def following(setup, update_input):
    result = validate_memory_update(encode(update_response(update_input)), request=update_input)
    kwargs = current(setup[0], round_id='r3')
    # Match the real grouper's anonymized source lineage for round-trip replay.
    from src.skill_evolution.evolution_replay_v19 import load_parent_experiences
    from src.skill_evolution.experience_cards_v17 import build_experience_cards
    from src.skill_evolution.experience_grouping_v17 import prepare_grouping_request
    parent = inputs(kwargs)[0].payload['current_skill']
    sources, scope = load_parent_experiences(run_id='test-run', round_id='r3', parent_skill=parent,
        backend=kwargs['backend'], artifact_dir=kwargs['parent_dir'])
    kwargs['grouping_result']['alias_to_source'] = prepare_grouping_request(
        build_experience_cards(sources, scope=scope), scope=scope)['alias_to_source']
    rs = inputs(kwargs)
    fs = tuple(validate_current_findings(encode(finding_response(r)), request=r) for r in rs)
    return dict(memory_evidence=result.updated_evidence, parent_skill=parent,
                current_requests=rs, current_findings=fs), kwargs


def prepare(kwargs, *, historical=True, history_only=False, decision='PROPOSE'):
    kwargs = dict(kwargs)
    if history_only:
        kwargs['current_findings'] = tuple(validate_current_findings(encode({
            'schema_version': 'current_findings_response_v19.1', 'summary': 'No current problem.',
            'findings': []}), request=r) for r in kwargs['current_requests'])
    fusion = build_issue_fusion_input(**kwargs)
    memory = kwargs['memory_evidence'].payload['memory']
    finding_ids = [f['finding_id'] for fs in kwargs['current_findings'] for f in fs.payload['findings']]
    issue = memory['issues'][0]
    selected = proposal(finding_ids, [issue['issue_id']] if historical else [],
                        [issue['attempts'][0]['attempt_id']] if historical else [])
    selected['decision'] = decision
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [selected], 'unassociated_findings': []}), request=fusion)
    return build_generation_input(**kwargs, fusion_input=fusion, fusion_result=result)


def test_updated_assessment_reaches_compact_fusion_and_both_sides_reach_review(following):
    kwargs, _ = following
    source = prepare(kwargs)
    fusion = build_issue_fusion_input(**kwargs)
    prompt = build_issue_fusion_request(fusion)
    issue = kwargs['memory_evidence'].payload['memory']['issues'][0]
    assert 'current_understanding' in prompt['user_prompt']
    assert issue['attempts'][-1]['assessment'] not in prompt['user_prompt']
    assert 'events' not in parse(prompt['user_prompt'])
    assert all(a['current_binding'] == 'UNRESOLVED' for i in fusion.payload['memory_issues'] for a in i['attempts'])
    request = review_inputs(source)[0]
    p = request.payload
    assert p['memory_issues'][0]['problem'] == issue['problem']
    assert p['memory_issues'][0]['attempts'] == [issue['attempts'][0]]
    assert p['memory_issues'][0]['current_understanding']
    assert 'OLD/1/E1' in p['known_counterevidence_refs']
    assert 'ATTR/unrelated' not in p['source_records']
    assert len(p['pairs']) == 1
    assert 'OLD/2/E0' not in p['events']
    for pair in p['pairs'].values():
        assert pair['round_id'] == 'r2'
        assert all(pair[role] in p['trajectories'] for role in ('parent', 'candidate'))
    assert {t['source_round_id'] for t in p['trajectories'].values()} >= {'r2', 'r3', 'old'}
    assert any(r.startswith('UNDERSTANDING_V21/') for r in p['source_records'])
    assert build_evidence_review_request(request)['prompt_version'] == 'evidence-review-v21.9'
    editor = compiled(source)
    ep = parse(verified_editor_request(editor)['user_prompt'])
    assert ep['edit_units'][0]['memory_issues'] == p['memory_issues']


@pytest.mark.parametrize('history_only,historical', [(True, True), (False, False)])
def test_history_only_and_current_only_directions(following, history_only, historical):
    source = prepare(following[0], historical=historical, history_only=history_only)
    request = review_inputs(source)[0]
    if history_only:
        assert not request.payload['findings']
        assert all(t['source_round_id'] != 'r3' for t in request.payload['trajectories'].values())
    else:
        assert not request.payload['memory_issues'] and not request.payload['pairs']
        assert all(t['source_round_id'] == 'r3' for t in request.payload['trajectories'].values())
    assert apply_verified_editor(editor_raw(compiled(source)), editor_input=compiled(source))['status'] == 'EDITED'


@pytest.mark.parametrize('damage', ['summary_as_event', 'drop_counter', 'historical_rule'])
def test_review_keeps_original_evidence_and_current_authority(following, damage):
    request = review_inputs(prepare(following[0]))[0]
    raw = final(request)
    if damage == 'summary_as_event':
        raw['evidence_refs'] = [next(iter(request.payload['source_records']))]
    elif damage == 'drop_counter':
        raw['counterevidence_refs'] = []
    else:
        raw['gap'] = {'kind': 'NEEDS_REVISION', 'statement': 'Change history.',
                      'related_rule_refs': [next(iter(request.payload['historical_edits']))]}
    with pytest.raises(ValueError, match='reference errors'):
        validate_evidence_review(encode(raw), request=request)


@pytest.mark.parametrize('damage', ['memory', 'bundle', 'parent', 'round'])
def test_source_binding_rejects_stale_or_inconsistent_inputs(following, damage):
    source = prepare(following[0])
    p = source.payload
    if damage == 'memory':
        p['memory']['issues'][0]['attempts'][0]['assessment'] = 'Tampered.'
    elif damage == 'bundle':
        p['memory_evidence']['memory']['issues'][0]['problem'] = 'Tampered.'
    elif damage == 'parent':
        p['parent_skill'] += '- Changed\n'
    else:
        p['fusion_input']['round_id'] = 'r4'
    with pytest.raises(ValueError):
        review_inputs(GenerationInput(encode(p)))


def test_no_edit_never_calls_review_or_editor(following, tmp_path):
    source = prepare(following[0], decision='NO_EDIT')
    def forbidden(_):
        raise AssertionError('No model is needed')
    audit = run_local_generation(source=source, output=tmp_path/'no-edit',
        review_transport=forbidden, editor_transport=forbidden)
    assert audit['result']['status'] == 'NO_UPDATE'
    assert not audit['reviews'] and not audit['result']['edits']
    assert restore_generation(audit)[1] == audit['result']


def test_fusion_no_edit_keeps_observed_problems_without_downstream_calls(following, tmp_path):
    """Constructed Fusion output checks routing, not semantic proposal quality."""
    from src.skill_evolution.memory_consumption_v21 import run_memory_consumption
    calls = []
    kwargs = following[0]
    original_memory = kwargs['memory_evidence'].payload_json
    reason = ('Current guidance covers the described procedure; the supplied findings '
        'do not identify a remaining behavioral mismatch. Outcome uncertainty alone '
        'does not justify a duplicate rule. This does not establish execution success.')

    def fusion(prompt):
        calls.append(prompt['prompt_version'])
        p = parse(prompt['user_prompt'])
        item = p['memory_issues'][0]
        selected = proposal([f['finding_id'] for f in p['current_findings']],
                            [item['issue_id']], [])
        selected.update(decision='NO_EDIT', reason=reason)
        return completion({'schema_version': 'issue_fusion_response_v20.1',
                           'issues': [selected], 'unassociated_findings': []})

    def forbidden(_):
        raise AssertionError('Fusion NO_EDIT must not call Review or Editor')

    audit = run_memory_consumption(**kwargs, output=tmp_path/'fusion-no-edit',
        fusion_transport=fusion, review_transport=forbidden, editor_transport=forbidden)
    assert calls == ['issue-fusion-v21.6']
    result = parse((tmp_path/'fusion-no-edit/fusion-result.json').read_text())
    expected = {f['finding_id'] for fs in kwargs['current_findings']
                for f in fs.payload['findings'] if f['kind'] == 'OBSERVED_PROBLEM'}
    assert expected and expected <= set(result['issues'][0]['current_finding_refs'])
    assert result['issues'][0]['reason'] == reason
    assert not result['unassociated_findings']
    assert not audit['reviews'] and audit['result']['candidate_skill'] is None
    assert audit['result']['status'] == 'NO_UPDATE'
    assert kwargs['memory_evidence'].payload_json == original_memory
    assert restore_generation(audit)[1] == audit['result']


def test_review_no_edit_preserves_comparison_without_editor_or_retry(following, tmp_path):
    """A constructed comparison checks transport only, not model reasoning quality."""
    source = prepare(following[0])
    request = review_inputs(source)[0]
    response = final(request, verdict='NO_EDIT')
    pair = next(iter(request.payload['pairs'].values()))
    response['evidence_refs'] = [next(ref for ref, event in request.payload['events'].items()
        if event['trajectory_ref'] == pair[role]) for role in ('parent', 'candidate')]
    response['reason'] = ('Both historical sides remain relevant, but their joint outcome '
        'does not identify a local cause. Current textual coverage is not execution proof; '
        'the loaded evidence does not establish which current behavior should change.')
    calls = []

    def review(prompt):
        calls.append(prompt['prompt_version'])
        assert expand(parse(prompt['user_prompt']), prompt['reference_map']) == request.payload
        return completion(response)

    def forbidden(_):
        raise AssertionError('NO_EDIT must not call Editor')

    audit = run_local_generation(source=source, output=tmp_path/'review-no-edit',
        review_transport=review, editor_transport=forbidden)
    assert calls == ['evidence-review-v21.9']
    assert audit['result']['status'] == 'NO_UPDATE'
    assert audit['result']['candidate_skill'] is None
    _, result = restore_generation(audit)
    assert result == audit['result']
    assert audit['reviews'][0]['reason'] == response['reason']
    assert audit['reviews'][0]['evidence_refs'] == response['evidence_refs']
    assert audit['reviews'][0]['counterevidence_refs'] == request.payload['known_counterevidence_refs']


def test_one_review_and_editor_roundtrip_then_post_modification_evidence(following, tmp_path):
    from src.skill_evolution.evolution_replay_v19 import _input, _manifest, _load_set, _run_set, _file_digest
    kwargs, replay = following
    source = prepare(kwargs)
    calls = []
    def review(prompt):
        calls.append(prompt['prompt_version'])
        return completion(final(review_inputs(source)[0]))
    def editor(prompt):
        calls.append(prompt['prompt_version'])
        return {'finish_reason': 'stop', 'raw_response': editor_raw(compiled(source))}
    audit = run_local_generation(source=source, output=tmp_path/'generation',
                                review_transport=review, editor_transport=editor)
    assert calls == ['evidence-review-v21.9', 'verified-editor-v20.1']
    assert restore_generation(audit)[1] == audit['result']
    bad = deepcopy(audit); bad['result']['candidate_skill'] += 'tampered'
    with pytest.raises(ValueError, match='Candidate changed'):
        restore_generation(bad)
    backend, parent_dir = replay['backend'], replay['parent_dir']
    candidate_dir = tmp_path/'candidate-r3'
    parents = _load_set(parent_dir, _input('test-run', 'r3', 'PARENT', kwargs['parent_skill'], _manifest(backend)))
    ci = _input('test-run', 'r3', 'CANDIDATE', audit['result']['candidate_skill'], _manifest(backend),
                parent_set=_file_digest(parent_dir/'state.json'))
    _run_set(backend, ci, candidate_dir, resume=False, max_workers=1, parents=parents)
    evidence = build_modification_evidence(audit=audit, backend=backend,
        parent_dir=parent_dir, candidate_dir=candidate_dir)
    assert evidence.payload['history_refs'] == [kwargs['memory_evidence'].evidence_ref]
    view = open_memory_evidence(evidence, proposal_refs=[evidence.payload['proposals'][0]['proposal_issue_id']])
    assert {p['round_id'] for p in view['pairs'].values()} == {'r2', 'r3'}
    assert 'OLD/1/E1' in view['events']
    assert any(r.startswith('ASSESSMENT_V21/') for r in view['source_records'])


def test_changed_joint_observation_flows_through_update_fusion_review_and_candidate(following, update_input, tmp_path):
    """Controlled transports verify data flow, not real-model reasoning quality."""
    from src.skill_evolution.memory_update_v21 import build_memory_update_input
    from src.skill_evolution.memory_consumption_v21 import run_memory_consumption
    kwargs, _ = following
    outputs, reasons = [], []
    calls = []
    # The fixture's T002 Candidate is failure/compliant; T003 is success/noncompliant.
    for task in ('T002', 'T003'):
        evidence = update_input.evidence
        pair = next(p for p in evidence.payload['archive']['pairs'].values() if p['task_ref'] == task)
        req = build_memory_update_input(evidence, pair_refs=[pair['pair_id']])
        raw = update_response(req)
        attempt = raw['issues'][0]['attempts'][0]
        tid = pair['candidate']
        label = req.payload['trajectories'][tid]['supervision']
        attempt['assessment'] = (f"Candidate observation: success={label['success']}, compliant={label['compliant']}; "
            'neither outcome identifies a local cause; the other dimension and earlier limitations still matter.')
        attempt['source_refs'] = [next(ref for ref, e in req.payload['events'].items() if e['trajectory_ref'] == tid)]
        raw['issues'][0]['current_understanding'] = attempt['assessment']
        updated = validate_memory_update(encode(raw), request=req).updated_evidence
        local = {**kwargs, 'memory_evidence': updated}
        def fusion(prompt):
            calls.append('fusion')
            p = parse(prompt['user_prompt'])
            item = p['memory_issues'][0]
            assert attempt['assessment'] == item['current_understanding']
            selected = proposal([f['finding_id'] for f in p['current_findings']], [item['issue_id']],
                                [item['attempts'][-1]['attempt_id']])
            selected['reason'] = 'Recheck both labels and old limitations: ' + item['current_understanding']
            return completion({'schema_version': 'issue_fusion_response_v20.1', 'issues': [selected],
                               'unassociated_findings': []})
        def review(prompt):
            calls.append('review')
            p = expand(parse(prompt['user_prompt']), prompt['reference_map'])
            last = p['memory_issues'][0]['attempts'][-1]
            record = p['source_records'][last['source_refs'][0]]
            ref = record['evidence_refs'][0]
            observed = p['trajectories'][p['events'][ref]['trajectory_ref']]['supervision']
            assert observed['success'] != observed['compliant']
            text = ('Check the change result against the requested outcome; do not relax required procedures.'
                    if not observed['success'] else
                    'Check the intended change against the applicable procedure; retain the requested outcome.')
            reasons.append(text)
            return completion({'proposal_id': p['proposal_id'], 'verdict': 'VERIFIED',
                'evidence_refs': [ref], 'counterevidence_refs': p['known_counterevidence_refs'],
                'reason': text + ' The cause and local contribution remain unproven; this tests a hypothesis.',
                'gap': {'kind': 'MISSING', 'statement': text, 'related_rule_refs': []}})
        def editor(prompt):
            calls.append('editor')
            units = parse(prompt['user_prompt'])['edit_units']
            return completion({'status': 'EDITED', 'reason': 'Apply the bounded reviewed hypothesis.',
                'edits': [{'edit_unit_index': u['edit_unit_index'],
                           'text': '- ' + u['verified_reviews'][0]['gap']['statement']} for u in units]})
        audit = run_memory_consumption(**local, output=tmp_path/task,
            fusion_transport=fusion, review_transport=review, editor_transport=editor)
        assert restore_generation(audit)[1] == audit['result']
        outputs.append(audit['result']['candidate_skill'])
    assert calls == ['fusion', 'review', 'editor'] * 2
    assert outputs[0] != outputs[1] and reasons[0] != reasons[1]
    assert not (tmp_path/'T002'/'head.json').exists()


def test_incomplete_fusion_stops_without_fabricated_review_or_retry(following, tmp_path):
    from src.skill_evolution.memory_consumption_v21 import run_memory_consumption
    calls = []
    def incomplete(_):
        calls.append('fusion')
        return {'finish_reason': 'length', 'raw_response': '{}'}
    with pytest.raises(ValueError, match='incomplete Fusion'):
        run_memory_consumption(**following[0], output=tmp_path/'stopped', fusion_transport=incomplete)
    assert calls == ['fusion']
    assert parse((tmp_path/'stopped/status.json').read_text())['status'] == 'INCOMPLETE'
    assert not (tmp_path/'stopped/generation').exists()


def test_preflight_cli_uses_trusted_bundle_without_calls(following, tmp_path, capsys, monkeypatch):
    from scripts.consume_v21_memory import main
    kwargs, _ = following
    source = prepare(kwargs)
    evidence_path = tmp_path/'updated-evidence.json'
    evidence_path.write_text(kwargs['memory_evidence'].payload_json)
    current_path = tmp_path/'current.json'; current_path.write_text(source.payload_json)
    monkeypatch.setattr('sys.argv', ['consume_v21_memory.py', '--evidence', str(evidence_path),
        '--expected-ref', kwargs['memory_evidence'].evidence_ref, '--current-source', str(current_path)])
    main()
    report = parse(capsys.readouterr().out)
    assert report['model_calls'] == 0 and not report['active_head_written']
    assert report['input_budget']['proxy_input_tokens'] > 0
