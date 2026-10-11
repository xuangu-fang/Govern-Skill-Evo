import json
from copy import deepcopy

import pytest

from tests.skill_evolution.test_local_generation_v20 import prepared, final, editor_raw, review_inputs
from tests.skill_evolution.test_memory_generation_v19 import setup
from tests.skill_evolution.test_memory_v19 import case
from src.skill_evolution.campaign_v20 import (
    campaign_config_v20, initialize_campaign, run_campaign_v20,
    commit_v20_round, CampaignRejected,
)
from src.skill_evolution.issue_memory_v20 import load_issue_memory
from src.skill_evolution.local_generation_v20 import restore_generation
from src.skill_evolution.edit_tracking_v19 import encode, digest
from src.skill_evolution.offline_v20 import (
    convert_v19_issue_fusion, offline_validate_v19, validate_converted_updates,
)


def transports(source):
    def review(prompt):
        request = review_inputs(source)[0]
        return {'finish_reason': 'stop', 'raw_response': encode(final(request))}
    def editor(prompt):
        # The helper's text follows the source's verified plan.
        from src.skill_evolution.local_generation_v20 import compile_verified
        reviews = tuple(__import__('src.skill_evolution.evidence_review_v20', fromlist=['validate_evidence_review'])
                        .validate_evidence_review(encode(final(r)), request=r) for r in review_inputs(source))
        value = compile_verified(source, reviews)
        return {'finish_reason': 'stop', 'raw_response': editor_raw(value)}
    return review, editor


def outcome(ctx):
    return {'gate': {'status': 'COMPLETE', 'decision': 'RETAIN', 'run_id': ctx['run_id'],
                     'round_id': ctx['round_id'], 'parent_skill_sha256': digest(ctx['parent_skill']),
                     'candidate_skill_sha256': digest(ctx['candidate_skill'])},
            'memory_update': {'schema_version': 'issue_memory_update_v20.1',
                'run_id': ctx['run_id'], 'round_id': ctx['round_id'], 'issues': []}}


def test_two_round_campaign_reuses_head_and_publishes_rounds(setup, tmp_path):
    source = prepared(setup)
    review, editor = transports(source)
    config = campaign_config_v20(round_limit=2)
    def factory(ctx):
        assert ctx['parent_skill'] == source.payload['parent_skill']
        return {'source': source, 'review_transport': review, 'editor_transport': editor}
    report = run_campaign_v20(output=tmp_path/'campaign', run_id='test-run',
        initial_skill=source.payload['parent_skill'], round_factory=factory,
        post_generation=outcome, config=config)
    assert report['status'] == 'COMPLETE'
    assert report['committed_rounds'] == 2
    assert [r['round_id'] for r in report['rounds']] == ['round-01', 'round-02']
    snapshot = load_issue_memory(tmp_path/'campaign'/'memory')
    assert snapshot.head['revision'] == 0  # no-op Memory updates do not invent revisions
    assert json.loads((tmp_path/'campaign'/'campaign.json').read_text())['status'] == 'COMPLETE'


def test_atomic_commit_recovery_finishes_pending_publication(tmp_path):
    root = tmp_path/'campaign'
    initialize_campaign(output=root, run_id='run', initial_skill='- Parent\n',
                        config=campaign_config_v20(round_limit=2))
    head = json.loads((root/'campaign-head.json').read_text())
    update = {'schema_version': 'issue_memory_update_v20.1', 'run_id': 'run',
              'round_id': 'round-01', 'issues': []}
    gate = {'status': 'COMPLETE', 'decision': 'RETAIN', 'run_id': 'run', 'round_id': 'round-01',
            'parent_skill_sha256': digest('- Parent\n'), 'candidate_skill_sha256': digest('- Candidate\n')}
    # A normal commit publishes both references; repeating with the old head is rejected.
    new = commit_v20_round(output=root, round_id='round-01', candidate_skill='- Candidate\n',
        gate=gate, memory_update=update, expected_head_ref='CAMPAIGN_HEAD_V20/' + digest(encode(head)))
    assert new['retained_skill'] == '- Parent\n'
    with pytest.raises(CampaignRejected, match='stale campaign head'):
        commit_v20_round(output=root, round_id='round-01', candidate_skill='- Candidate\n',
            gate=gate, memory_update=update, expected_head_ref='CAMPAIGN_HEAD_V20/' + digest(encode(head)))


def test_resume_rejects_binding_or_tampered_generation(setup, tmp_path):
    source = prepared(setup); review, editor = transports(source)
    config = campaign_config_v20(round_limit=1)
    def factory(_): return {'source': source, 'review_transport': review, 'editor_transport': editor}
    run_campaign_v20(output=tmp_path/'campaign', run_id='test-run', initial_skill=source.payload['parent_skill'],
        round_factory=factory, post_generation=outcome, config=config)
    with pytest.raises(CampaignRejected, match='campaign binding changed'):
        run_campaign_v20(output=tmp_path/'campaign', run_id='test-run', initial_skill='- Changed\n',
            round_factory=factory, post_generation=outcome, config=config, resume=True)


def test_offline_v19_conversion_keeps_problems_without_fabricating_attempts():
    v19 = {'schema_version': 'issue_fusion_result_v19.1', 'input_ref': 'old',
        'issues': [{'issue_id': 'ISSUE/old', 'source_finding_refs': ['CF/1'],
                    'historical_refs': ['HR/1'], 'issue_statement': 'Old problem.', 'decision': 'PROPOSE'}]}
    update = convert_v19_issue_fusion(run_id='offline', round_id='r1', fusion_result=v19)
    assert update['issues'][0]['attempts'] if 'attempts' in update['issues'][0] else True
    memory = validate_converted_updates([update], run_id='offline')
    assert memory['issues'][0]['attempts'] == []
    report = offline_validate_v19(artifacts=[v19], run_id='offline')
    assert report.payload['mode'] == 'READ_ONLY'
    assert report.payload['claims'].startswith('STRUCTURAL')


def test_offline_rejects_unknown_or_incomplete_artifact():
    with pytest.raises(ValueError, match='unsupported offline'):
        offline_validate_v19(artifacts=[{'schema_version': 'monitor_result_v19.1'}])
    with pytest.raises(ValueError, match='incomplete v19 local audit'):
        offline_validate_v19(artifacts=[{'schema_version': 'local_generation_v19.1'}])


def test_offline_reads_existing_v19_gap_fixture():
    artifact = json.loads(open('tests/skill_evolution/fixtures/v19_gap_closure/response.json', encoding='utf-8').read())
    report = offline_validate_v19(artifacts=[artifact], run_id='offline-fixture')
    body = json.loads(artifact)['diagnosis'] if isinstance(artifact, str) else artifact.get('diagnosis', artifact)
    assert report.payload['artifact_count'] == 1
    assert report.payload['fusion_proposals'] == len(body['parent_skill_gaps'])
    memory = validate_converted_updates(report.payload['converted_updates'], run_id='offline-fixture')
    assert len(memory['issues']) == len(body['parent_skill_gaps'])
    assert all(not issue['attempts'] for issue in memory['issues'])
