from copy import deepcopy

import pytest

from src.skill_evolution.v19.edit_tracking_v19 import encode, digest
from src.skill_evolution.v19.attribution_v19 import AttributionRejected, build_attribution_input, build_attribution_request, validate_attribution_response, run_attribution, load_attribution
from src.skill_evolution.v19.evolution_replay_v19 import _load, _save, _file_digest
from tests.skill_evolution.v19.test_evolution_replay_v19 import scenario, case, run
from tests.skill_evolution.v19.test_edit_tracking_v19 import value_for, ledger_for
from tests.skill_evolution.v19.test_evolution_replay_v19 import Backend
from src.skill_evolution.v19.evolution_replay_v19 import run_parent_evolution, run_candidate_replay


@pytest.fixture
def prepared(scenario):
    run(scenario)
    backend, ledger, parent, candidate = scenario
    kwargs = dict(backend=backend, parent_dir=parent, replay_dir=candidate)
    return ledger, kwargs, build_attribution_input(ledger, **kwargs)


def record(data, indices=(0,), effect='BENEFICIAL', level='BEHAVIOR_SUPPORTED'):
    observations = []
    for index in indices:
        pair = data['pairs'][index]
        observations.append({'pair_id': pair['pair_id'], 'relation': 'SUPPORT',
            **{r + '_evidence_refs': [next(e['evidence_ref'] for e in pair[r]['events']
                                              if e['event_type'] == 'tool_call')]
               for r in ('parent', 'candidate')},
            'supervision_refs': [pair[r]['supervision']['supervision_ref'] for r in ('parent', 'candidate')],
            'behavior_comparison': 'Both issued the visible change call; textual framing differed.'})
    return {'edit_ids': [e['edit_id'] for e in data['edits']], 'effect': effect, 'evidence_level': level,
            'observations': observations, 'interpretation': 'Tentative association in the cited scope.',
            'applicability': 'Only the cited visible requests; no claim about unseen situations.',
            'alternative_explanations': ['Other edits, dialogue variation and stochastic model outputs.'],
            'uncertainty': 'Same observed action does not establish causality.',
            'suggested_followup': 'DEFER'}


def response(*records):
    return encode({'schema_version': 'attribution_response_v19.1', 'records': list(records)})


def complete(raw):
    return {'raw_response': raw, 'finish_reason': 'stop', 'refusal': None}


def validate(data, *records):
    return validate_attribution_response(response(*records), learner_input=data)


def test_safe_complete_input_and_no_gate(prepared):
    ledger, kwargs, data = prepared
    assert len(data['pairs']) == 3 and data['edits'] == ledger.payload['edits']
    request = build_attribution_request(data)
    for private in ('PRIVATE-', 'HIDDEN_', 'private_database', 'gate_decision', 'expected_action', 'seed'):
        assert private not in request['user_prompt']
    assert request['max_retries'] == 0
    assert data['candidate_skill'] == ledger.source['candidate_skill']
    assert data['ledger_sha256'] == digest(ledger.output_json)


@pytest.mark.parametrize('effect,indices,level', [
    ('BENEFICIAL', (0,), 'BEHAVIOR_SUPPORTED'), ('HARMFUL', (1,), 'OUTCOME_ASSOCIATION'),
    ('MIXED', (0, 1), 'BEHAVIOR_SUPPORTED'), ('NO_OBSERVED_EFFECT', (2,), 'BEHAVIOR_SUPPORTED'),
    ('NOT_EXERCISED', (2,), 'UNRESOLVED'), ('UNKNOWN', (), 'UNRESOLVED'),
])
def test_all_effects_are_representable(prepared, effect, indices, level):
    _, _, data = prepared
    result = validate(data, record(data, indices, effect, level))
    out = result.payload
    assert out['validation_scope'] == 'STRUCTURE_AND_REFERENCES_ONLY'
    assert out['records'][0]['effect'] == effect
    assert out['records'][0]['attribution_id'].startswith('ATTRIBUTION/')
    out['records'].clear()
    assert result.payload['records']


@pytest.mark.parametrize('mutation', [
    lambda r,d: r.update(edit_ids=['EDIT/unknown']),
    lambda r,d: r.update(edit_ids=r['edit_ids']*2),
    lambda r,d: r.update(effect='GOOD'),
    lambda r,d: r.update(uncertainty=''),
    lambda r,d: r.update(alternative_explanations=[]),
    lambda r,d: r.update(confidence=0.9),
    lambda r,d: r.update(observations=[]),
    lambda r,d: r['observations'][0].update(pair_id=d['pairs'][1]['pair_id']),
    lambda r,d: r['observations'][0].update(parent_evidence_refs=r['observations'][0]['candidate_evidence_refs']),
    lambda r,d: r['observations'][0].update(supervision_refs=r['observations'][0]['supervision_refs'][:1]),
    lambda r,d: r['observations'][0].update(parent_evidence_refs=r['observations'][0]['supervision_refs'][:1]),
    lambda r,d: r['observations'][0].update(parent_evidence_refs=[]),
    lambda r,d: r['observations'][0].update(parent_evidence_refs=[d['pairs'][0]['parent']['events'][0]['evidence_ref']]),
    lambda r,d: r['observations'][0].update(expected_action='secret'),
    lambda r,d: r.update(observations=r['observations']*2),
    lambda r,d: r.update(evidence_level='UNRESOLVED'),
])
def test_malformed_and_cross_role_evidence_rejected(prepared, mutation):
    _, _, data = prepared
    r = record(data)
    mutation(r, data)
    with pytest.raises(AttributionRejected): validate(data, r)


@pytest.mark.parametrize('effect,indices', [
    ('BENEFICIAL', (0,1)), ('HARMFUL', (0,1)), ('MIXED', (0,)),
    ('NO_OBSERVED_EFFECT', (0,)), ('BENEFICIAL', (2,)), ('HARMFUL', (0,)),
])
def test_result_directions_cannot_hide_regression(prepared, effect, indices):
    _, _, data = prepared
    with pytest.raises(AttributionRejected): validate(data, record(data, indices, effect))


def test_counterevidence_and_conflicting_dimensions(prepared):
    _, _, data = prepared
    r = record(data, (0,1), 'MIXED')
    r['observations'][1]['relation'] = 'COUNTEREVIDENCE'
    assert validate(data, r)
    r['effect'] = 'BENEFICIAL'
    with pytest.raises(AttributionRejected): validate(data, r)
    # Unit-level validator check; actual production data always comes from disk revalidation.
    local = deepcopy(data)
    local['pairs'][0]['outcome_transition']['compliant_delta'] = -1
    assert validate(local, record(local, (0,), 'MIXED'))
    with pytest.raises(AttributionRejected): validate(local, record(local))


def test_unknown_is_explicit_not_failure_fallback(prepared):
    _, _, data = prepared
    r = record(data, (), 'UNKNOWN', 'UNRESOLVED')
    r['suggested_followup'] = 'CONSIDER_REMOVE'
    with pytest.raises(AttributionRejected): validate(data, r)
    with pytest.raises(AttributionRejected): validate_attribution_response('broken', learner_input=data)
    with pytest.raises(AttributionRejected): validate(data)


def test_outcome_only_can_use_labels_but_not_behavior_level(prepared):
    _, _, data = prepared
    r = record(data, level='OUTCOME_ASSOCIATION')
    r['observations'][0].update(parent_evidence_refs=[], candidate_evidence_refs=[])
    assert validate(data, r)
    r['evidence_level'] = 'BEHAVIOR_SUPPORTED'
    with pytest.raises(AttributionRejected): validate(data, r)


def test_joint_and_scoped_records_cover_all_edits(case, tmp_path):
    backend = Backend()
    value = value_for(case, backend.parent, [('MISSING', []), ('MISSING', [])])
    ledger = ledger_for(value, [(0, '- First'), (1, '- Second')])
    parent, replay = tmp_path/'parent', tmp_path/'replay'
    run_parent_evolution(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                         backend=backend, artifact_dir=parent)
    run_candidate_replay(ledger, backend=backend, parent_dir=parent, artifact_dir=replay)
    data = build_attribution_input(ledger, backend=backend, parent_dir=parent, replay_dir=replay)
    r = record(data, (0,1), 'MIXED')
    assert len(validate(data, r).payload['records']) == 1
    r['edit_ids'] = r['edit_ids'][:1]
    with pytest.raises(AttributionRejected): validate(data, r)
    unknown = record(data, (), 'UNKNOWN', 'UNRESOLVED')
    unknown['edit_ids'] = [data['edits'][1]['edit_id']]
    assert len(validate(data, r, unknown).payload['records']) == 2
    with pytest.raises(AttributionRejected): validate(data, r, unknown, unknown)


def test_audited_run_load_resume_and_tampering(prepared, tmp_path):
    ledger, kwargs, data = prepared
    calls=[]
    def transport(request):
        calls.append(request)
        return complete(response(record(data, (0,1), 'MIXED')))
    path=tmp_path/'attribution'
    batch=run_attribution(ledger, **kwargs, artifact_dir=path, transport=transport)
    assert batch == load_attribution(ledger, **kwargs, artifact_dir=path)
    assert batch == run_attribution(ledger, **kwargs, artifact_dir=path, transport=transport, resume=True)
    assert len(calls) == 1
    with pytest.raises(AttributionRejected): run_attribution(ledger, **kwargs, artifact_dir=path, transport=transport)
    saved=_load(path/'attributions.json'); saved['records'][0]['interpretation']='forged'
    _save(path/'attributions.json', saved)
    marker=_load(path/'validation.json'); marker['files']['attributions.json']=_file_digest(path/'attributions.json')
    _save(path/'validation.json', marker)
    with pytest.raises(AttributionRejected): load_attribution(ledger, **kwargs, artifact_dir=path)


@pytest.mark.parametrize('reply', [complete('broken'), {'raw_response':'{}','finish_reason':'length'},
                                  {'raw_response':'{}','finish_reason':'stop','refusal':'no'}])
def test_model_failures_not_unknown(prepared, tmp_path, reply):
    ledger, kwargs, _=prepared
    path=tmp_path/'failed'
    with pytest.raises(AttributionRejected):
        run_attribution(ledger, **kwargs, artifact_dir=path, transport=lambda _:reply)
    assert _load(path/'validation.json')['status']=='INCOMPLETE'
    assert not (path/'attributions.json').exists()


def test_transport_failure_and_missing_response_no_retry(prepared, tmp_path):
    ledger, kwargs, _=prepared
    calls=[]
    def fail(_):
        calls.append(1)
        raise RuntimeError('PRIVATE_PROVIDER_SECRET')
    path=tmp_path/'failed'
    with pytest.raises(RuntimeError): run_attribution(ledger, **kwargs, artifact_dir=path, transport=fail)
    with pytest.raises(AttributionRejected):
        run_attribution(ledger, **kwargs, artifact_dir=path, transport=fail, resume=True)
    assert calls==[1]
    assert 'PRIVATE_PROVIDER_SECRET' not in (path/'validation.json').read_text()


def test_resume_after_response_does_not_call_model(prepared, tmp_path, monkeypatch):
    import src.skill_evolution.v19.attribution_v19 as module
    ledger, kwargs, data=prepared
    path=tmp_path/'interrupted'
    original=module._save
    def stop(path_,value):
        if path_.name=='attributions.json': raise KeyboardInterrupt()
        original(path_,value)
    monkeypatch.setattr(module,'_save',stop)
    with pytest.raises(KeyboardInterrupt):
        run_attribution(ledger, **kwargs, artifact_dir=path,
                        transport=lambda _:complete(response(record(data))))
    monkeypatch.setattr(module,'_save',original)
    def forbidden(_): raise AssertionError('must not call again')
    assert run_attribution(ledger, **kwargs, artifact_dir=path, transport=forbidden,resume=True)


def test_replay_corruption_rejected_before_model(prepared, tmp_path):
    ledger, kwargs, data=prepared
    path=kwargs['replay_dir']/'learner/pairs.json'
    changed=_load(path); changed['pairs'].pop(); _save(path,changed)
    def forbidden(_): raise AssertionError('must not call')
    with pytest.raises(ValueError):
        run_attribution(ledger, **kwargs, artifact_dir=tmp_path/'never',transport=forbidden)
    assert not (tmp_path/'never').exists()


def test_incomplete_response_corruption_cannot_resume(prepared, tmp_path):
    ledger, kwargs, data = prepared
    path=tmp_path/'badresponse'
    with pytest.raises(AttributionRejected):
        run_attribution(ledger, **kwargs, artifact_dir=path, transport=lambda _:complete('broken'))
    _save(path/'response.json', complete(response(record(data))))
    with pytest.raises(AttributionRejected, match='checkpoint mismatch'):
        run_attribution(ledger, **kwargs, artifact_dir=path, resume=True)


def test_prompt_drift_refuses_completed_reuse(prepared, tmp_path, monkeypatch):
    import src.skill_evolution.v19.attribution_v19 as module
    ledger, kwargs, data=prepared
    path=tmp_path/'done'
    run_attribution(ledger, **kwargs, artifact_dir=path, transport=lambda _:complete(response(record(data))))
    monkeypatch.setattr(module,'SYSTEM_PROMPT', module.SYSTEM_PROMPT+'Changed.')
    with pytest.raises(AttributionRejected, match='version changed'):
        load_attribution(ledger, **kwargs, artifact_dir=path)


def test_empty_candidate_delete_is_attributable(case, tmp_path):
    backend = Backend()
    value=value_for(case, backend.parent, [('SHOULD_REMOVE', [0])])
    ledger=ledger_for(value, [])
    parent,replay=tmp_path/'parent',tmp_path/'replay'
    run_parent_evolution(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                         backend=backend, artifact_dir=parent)
    run_candidate_replay(ledger,backend=backend,parent_dir=parent,artifact_dir=replay)
    data=build_attribution_input(ledger,backend=backend,parent_dir=parent,replay_dir=replay)
    assert data['candidate_skill']==''
    assert data['edits'][0]['operation']=='DELETE'
    assert validate(data, record(data, (0,1), 'MIXED'))


def test_distinct_scopes_same_edit_preserved(prepared):
    _,_,data=prepared
    beneficial=record(data)
    harmful=record(data,(1,),'HARMFUL')
    batch=validate(data,beneficial,harmful)
    assert len(batch.payload['records'])==2
    assert batch.payload['records'][0]['attribution_id'] != batch.payload['records'][1]['attribution_id']


@pytest.mark.parametrize('raw', [
    '{"schema_version":"attribution_response_v19.1","records":[],"records":[]}',
    '{"schema_version":"attribution_response_v19.1","records":NaN}',
    '```json\n{}\n```', '[]', 'null',
])
def test_strict_json(prepared, raw):
    _,_,data=prepared
    with pytest.raises(AttributionRejected): validate_attribution_response(raw,learner_input=data)
