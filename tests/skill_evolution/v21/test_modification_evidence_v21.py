from copy import deepcopy
import shutil

import pytest

from tests.skill_evolution.v19.test_memory_generation_v19 import setup, case
from tests.skill_evolution.v20.test_local_generation_v20 import prepared, compiled, editor_raw
from src.skill_evolution.v20.local_generation_v20 import apply_verified_editor
from src.skill_evolution.v19.edit_tracking_v19 import encode, parse, digest
from src.skill_evolution.v19.evolution_replay_v19 import _input, _manifest, _load_set, _run_set, _file_digest, _save
from src.skill_evolution.v21.modification_evidence_v21 import build_modification_evidence, save_modification_evidence, load_modification_evidence, open_memory_evidence, prepare_memory_evidence


@pytest.fixture
def completed(setup):
    root, _, current = setup
    from src.skill_evolution.v19.evolution_replay_v19 import load_parent_experiences
    from src.skill_evolution.v17.experience_cards_v17 import build_experience_cards
    from src.skill_evolution.v17.experience_grouping_v17 import prepare_grouping_request
    parent = parse((root / 'memory/head.json').read_text())['retained_skill']
    sources, scope = load_parent_experiences(run_id='test-run', round_id='r2', parent_skill=parent,
                                             backend=current['backend'], artifact_dir=current['parent_dir'])
    current['grouping_result']['alias_to_source'] = prepare_grouping_request(
        build_experience_cards(sources, scope=scope), scope=scope)['alias_to_source']
    source = prepared(setup, historical=True)
    editor = compiled(source)
    generation = apply_verified_editor(editor_raw(editor), editor_input=editor)
    audit = {'schema_version': 'generation_audit_v20.1', 'source': source.payload,
             'reviews': parse(editor.reviews_json), 'plan': editor.plan, 'result': generation}
    backend = current['backend']
    parent_dir = current['parent_dir']
    candidate_dir = root / 'candidate-r2'
    parent_input = _input('test-run', 'r2', 'PARENT', source.payload['parent_skill'], _manifest(backend))
    parents = _load_set(parent_dir, parent_input)
    candidate_input = _input('test-run', 'r2', 'CANDIDATE', generation['candidate_skill'], _manifest(backend),
                             parent_set=_file_digest(parent_dir / 'state.json'))
    _run_set(backend, candidate_input, candidate_dir, resume=False, max_workers=1, parents=parents)
    return dict(audit=audit, backend=backend, parent_dir=parent_dir, candidate_dir=candidate_dir)


def test_real_checkpoint_projection_retains_both_axes_and_never_runs_models(completed):
    backend = completed['backend']
    calls, evaluations = backend.calls.copy(), backend.evaluations.copy()
    evidence = build_modification_evidence(**completed)
    p = evidence.payload
    assert backend.calls == calls and backend.evaluations == evaluations
    assert len(p['current_pair_refs']) == 3
    view = open_memory_evidence(evidence, pair_refs=p['current_pair_refs'])
    pairs = list(view['pairs'].values())
    outcomes = [(view['trajectories'][pair['parent']]['supervision']['success'],
                 view['trajectories'][pair['candidate']]['supervision']['success']) for pair in pairs]
    assert sorted(outcomes) == [(False, True), (True, False), (True, True)]
    assert len(view['events']) == 30  # both complete five-event trajectories for all three tasks
    for pair in pairs:
        for role in ('parent', 'candidate'):
            trajectory = view['trajectories'][pair[role]]
            assert trajectory['role'] == role.upper()
            assert trajectory['source_round_id'] == 'r2'
            assert trajectory['skill_ref'] == p[role + '_skill_ref']
            assert trajectory['supervision']['supervision_ref'].startswith(pair['pair_id'])
            assert trajectory['supervision']['level'] == 0
            assert type(trajectory['supervision']['compliant']) is bool
        assert view['source_records'][pair['pair_id']]['edit_refs'] == []
    for private in ('PRIVATE-', 'HIDDEN_', 'task_id', 'seed', 'private_database',
                    'expected_action', 'PRIVATE_EVALUATOR_REASON', 'monitor_score', 'gate_decision'):
        assert private not in evidence.payload_json
    assert 'effect' not in p['archive']['pairs'][p['current_pair_refs'][0]]


def test_proposal_loads_counterevidence_and_candidate_without_expanding_whole_round(completed):
    evidence = build_modification_evidence(**completed)
    proposal = evidence.payload['proposals'][0]['proposal_issue_id']
    view = open_memory_evidence(evidence, proposal_refs=[proposal])
    assert set(view['source_records']) >= {'ATTR/old', 'ATTR/failed'}
    assert 'ATTR/unrelated' not in view['source_records']
    assert len(view['pairs']) == 1
    assert set(view['parent_pairs'].values()) == set(view['pairs'])
    assert {p['task_ref'] for p in view['pairs'].values()} == {'T001'}
    assert view['reviews'] and view['memory_issues']
    assert 'OLD/1/E1' in view['events']  # original counterevidence, not only summary
    assert 'OLD/2/E0' not in view['events']
    assert any(t['role'] == 'CANDIDATE' for t in view['trajectories'].values())
    assert view['current_edits'] == evidence.payload['edits']


def test_old_issue_can_open_new_pair_without_a_selected_proposal(completed):
    evidence = build_modification_evidence(**completed)
    p = evidence.payload
    issue = p['memory']['issues'][0]['issue_id']
    pair = next(ref for ref in p['current_pair_refs'] if p['archive']['pairs'][ref]['task_ref'] == 'T003')
    view = open_memory_evidence(evidence, issue_refs=[issue], pair_refs=[pair])
    assert not view['proposals']
    assert view['memory_issues'][0]['issue_id'] == issue
    assert pair in view['pairs']
    assert 'ATTR/failed' in view['source_records']


def test_save_reload_is_idempotent_and_bound_to_expected_reference(completed, tmp_path):
    evidence = build_modification_evidence(**completed)
    path = tmp_path / 'v21-evidence.json'
    ref = save_modification_evidence(evidence, path)
    before = path.stat().st_mtime_ns
    assert save_modification_evidence(evidence, path) == ref
    assert path.stat().st_mtime_ns == before
    loaded = load_modification_evidence(path, expected_ref=ref)
    assert loaded == evidence
    assert open_memory_evidence(loaded, pair_refs=loaded.payload['current_pair_refs'])
    value = loaded.payload
    value['round_id'] = 'wrong'
    _save(path, value)
    with pytest.raises(ValueError, match='digest mismatch'):
        load_modification_evidence(path, expected_ref=ref)
    with pytest.raises(ValueError, match='existing evidence differs'):
        save_modification_evidence(evidence, path)


@pytest.mark.parametrize('part', ['candidate_skill', 'round', 'manifest', 'incomplete', 'label', 'monitor'])
def test_mismatched_or_incomplete_sources_are_rejected(completed, part):
    kwargs = dict(completed)
    if part == 'candidate_skill':
        kwargs['audit'] = deepcopy(completed['audit'])
        kwargs['audit']['result']['candidate_skill'] += 'tamper'
    elif part == 'round':
        path = completed['candidate_dir'] / 'input.json'
        value = parse(path.read_text()); value['round_id'] = 'different'; _save(path, value)
    elif part == 'manifest':
        completed['backend'].version = 'different'
    elif part == 'incomplete':
        _save(completed['candidate_dir'] / 'state.json', {'status': 'RUNNING'})
    elif part == 'label':
        path = completed['candidate_dir'] / 'tasks/T001/evaluation.json'
        value = parse(path.read_text()); value['compliant'] = not value['compliant']; _save(path, value)
    else:
        original = completed['backend'].manifest()
        completed['backend'].manifest = lambda: {**original, 'schema_version': 'monitor_manifest_v19.1'}
    with pytest.raises(ValueError):
        build_modification_evidence(**kwargs)


@pytest.mark.parametrize('kwargs', [
    {'pair_refs': ['PAIR/missing']}, {'source_refs': ['ATTR/missing']},
    {'issue_refs': ['ISSUE/missing']}, {'proposal_refs': ['PISSUE/missing']},
])
def test_unknown_reference_never_becomes_silently_missing_evidence(completed, kwargs):
    with pytest.raises(ValueError):
        open_memory_evidence(build_modification_evidence(**completed), **kwargs)


def test_offline_entry_is_read_only_and_reopens_saved_evidence(completed, tmp_path):
    root = tmp_path / 'source-round'
    root.mkdir()
    shutil.copytree(completed['parent_dir'], root / 'parent_evolution')
    shutil.copytree(completed['candidate_dir'], root / 'candidate_evolution')
    _save(root / 'generation/generation-audit.json', completed['audit'])
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    output = tmp_path / 'derived-v21/evidence.json'
    evidence = prepare_memory_evidence(round_dir=root, backend=completed['backend'], output=output)
    assert evidence == load_modification_evidence(output, expected_ref=evidence.evidence_ref)
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='outside the source round'):
        prepare_memory_evidence(round_dir=root, backend=completed['backend'], output=root / 'evidence.json')


def test_prior_bundle_sources_survive_without_copying_all_historical_events(completed, setup):
    from tests.skill_evolution.v19.test_memory_generation_v19 import current
    from tests.skill_evolution.v19.test_separated_review_v19 import inputs, response
    from tests.skill_evolution.v20.test_local_generation_v20 import proposal
    from src.skill_evolution.v19.current_diagnosis_v19 import validate_current_findings
    from src.skill_evolution.v20.issue_fusion_v20 import build_issue_fusion_input, validate_issue_fusion
    from src.skill_evolution.v20.local_generation_v20 import build_generation_input
    from src.skill_evolution.v20.evidence_review_v20 import EvidenceArchive
    previous = build_modification_evidence(**completed)
    root, old, _ = setup
    next_current = current(root, round_id='r3')
    requests = inputs(next_current)
    findings = tuple(validate_current_findings(encode(response(r)), request=r) for r in requests)
    original = completed['audit']['source']
    fusion = build_issue_fusion_input(memory=original['memory'], parent_skill=original['parent_skill'],
        run_id='test-run', round_id='r3', current_requests=requests, current_findings=findings)
    selected = proposal([findings[0].payload['findings'][0]['finding_id']])
    result = validate_issue_fusion(encode({'schema_version': 'issue_fusion_response_v20.1',
        'issues': [selected], 'unassociated_findings': []}), request=fusion)
    source = build_generation_input(memory=original['memory'], fusion_input=fusion, fusion_result=result,
        archive=EvidenceArchive(encode(original['archive'])), parent_skill=original['parent_skill'],
        current_requests=requests, current_findings=findings)
    editor = compiled(source)
    generation = apply_verified_editor(editor_raw(editor), editor_input=editor)
    audit = {'schema_version': 'generation_audit_v20.1', 'source': source.payload,
             'reviews': parse(editor.reviews_json), 'plan': editor.plan, 'result': generation}
    manifest = _manifest(next_current['backend'])
    parent_dir = next_current['parent_dir']
    parents = _load_set(parent_dir, _input('test-run', 'r3', 'PARENT', source.payload['parent_skill'], manifest))
    candidate_dir = root / 'candidate-r3'
    value = _input('test-run', 'r3', 'CANDIDATE', generation['candidate_skill'], manifest,
                    parent_set=_file_digest(parent_dir / 'state.json'))
    _run_set(next_current['backend'], value, candidate_dir, resume=False, max_workers=1, parents=parents)
    evidence = build_modification_evidence(audit=audit, backend=next_current['backend'],
        parent_dir=parent_dir, candidate_dir=candidate_dir, history=(previous,))
    old_pair = previous.payload['current_pair_refs'][0]
    view = open_memory_evidence(evidence, source_refs=[old_pair])
    assert set(view['pairs']) == {old_pair}
    assert {t['source_round_id'] for t in view['trajectories'].values()} == {'r2'}
    assert len(view['events']) == 10
    assert set(evidence.payload['current_pair_refs']).isdisjoint(previous.payload['current_pair_refs'])
    assert evidence.payload['history_refs'] == [previous.evidence_ref]


def test_same_round_cannot_be_imported_as_committed_history(completed):
    evidence = build_modification_evidence(**completed)
    with pytest.raises(ValueError, match='history run/round mismatch'):
        build_modification_evidence(**completed, history=(evidence,))


def test_summary_cannot_override_original_joint_outcomes(completed):
    _save(completed['candidate_dir'] / 'candidate-summary.json',
          {'success_count': 999, 'compliance_count': 999, 'rows': []})
    evidence = build_modification_evidence(**completed)
    p = evidence.payload
    results = [p['archive']['trajectories'][p['archive']['pairs'][ref]['candidate']]['supervision']
               for ref in p['current_pair_refs']]
    assert sum(r['success'] for r in results) == 2
    assert sum(r['compliant'] for r in results) == 2


def test_pairing_still_rejects_different_initial_state_with_valid_file_hashes(completed):
    from src.skill_evolution.v19.evolution_replay_v19 import _write_checkpoint, RAW_FILES
    directory = completed['candidate_dir'] / 'tasks/T001'
    path = directory / 'initial_db.json'
    value = parse(path.read_text()); value['value'] = 42; _save(path, value)
    _write_checkpoint(directory, 'raw_complete.json', RAW_FILES)
    _write_checkpoint(directory, 'checkpoint.json', (*RAW_FILES, 'raw_complete.json', 'evaluation.json'))
    state_path = completed['candidate_dir'] / 'state.json'
    state = parse(state_path.read_text())
    state['task_checkpoints']['T001'] = _file_digest(directory / 'checkpoint.json')
    _save(state_path, state)
    with pytest.raises(ValueError, match='paired initial_db mismatch'):
        build_modification_evidence(**completed)
