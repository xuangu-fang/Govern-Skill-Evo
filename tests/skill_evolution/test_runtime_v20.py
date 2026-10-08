from pathlib import Path
import json
from types import SimpleNamespace

from src.skill_evolution.issue_memory_v20 import initialize_issue_memory, merge_update
from src.skill_evolution.runtime_v20 import (_fusion_records, build_v20_memory_update,
                                              build_v20_post_generation)


def test_default_post_generation_replays_candidate_gate_and_updates_attempt(tmp_path):
    memory = initialize_issue_memory(store_dir=tmp_path / 'memory', run_id='run')
    source = {
        'fusion_result': {'issues': [{
            'proposal_issue_id': 'PISSUE/current', 'decision': 'PROPOSE',
            'issue_statement': 'The current rule misses a condition.',
            'memory_issue_refs': [], 'current_finding_refs': ['CF/current'],
        }]},
    }

    class Benchmark:
        def run_candidate_evolution(self, **kwargs):
            assert kwargs['artifact_dir'] == Path(tmp_path / 'round' / 'candidate_evolution')
            return {'schema_version': 'candidate_replay_v20.1', 'status': 'COMPLETE',
                    'task_count': 1, 'rows': [], 'success_count': 1, 'compliance_count': 1}

        def run_private_gate_v20(self, **kwargs):
            return {'status': 'COMPLETE', 'decision': 'RETAIN', 'run_id': 'run',
                    'round_id': 'round-01', 'parent_skill_sha256': 'parent',
                    'candidate_skill_sha256': 'candidate'}

        def build_local_attribution(self, **kwargs):
            return {'schema_version': 'local_attribution_v20.1', 'records': [],
                    'scope': 'STRUCTURAL_EDIT_TO_REPLAY_BINDING_NOT_CAUSAL_EFFECT'}

    ctx = {'run_id': 'run', 'round_id': 'round-01', 'parent_skill': '- Parent\n',
           'candidate_skill': '- Candidate\n', 'root': tmp_path / 'round', 'memory': memory,
           'audit': {'source': source, 'result': {'edits': [{
               'edit_id': 'EDIT_V20/' + 'a' * 64, 'operation': 'ADD',
               'memory_issue_refs': [], 'current_finding_refs': ['CF/current'],
           }]}}}
    result = build_v20_post_generation(benchmark=Benchmark())(ctx)
    assert result['gate']['decision'] == 'RETAIN'
    merged = merge_update(memory.memory, result['memory_update'])
    assert len(merged['issues']) == 1
    assert len(merged['issues'][0]['attempts']) == 1


def test_post_generation_preserves_empty_update_when_no_edit(tmp_path):
    memory = initialize_issue_memory(store_dir=tmp_path / 'memory', run_id='run')

    class Benchmark:
        def run_candidate_evolution(self, **kwargs):
            return {'status': 'COMPLETE'}

        def run_private_gate_v20(self, **kwargs):
            return {'status': 'COMPLETE', 'decision': 'ACCEPT', 'run_id': 'run',
                    'round_id': 'round-01', 'parent_skill_sha256': 'parent',
                    'candidate_skill_sha256': 'candidate'}

        def build_local_attribution(self, **kwargs):
            return {'schema_version': 'local_attribution_v20.1', 'records': [],
                    'scope': 'STRUCTURAL_EDIT_TO_REPLAY_BINDING_NOT_CAUSAL_EFFECT'}

    ctx = {'run_id': 'run', 'round_id': 'round-01', 'parent_skill': '- Parent\n',
           'candidate_skill': '- Candidate\n', 'root': tmp_path / 'round', 'memory': memory,
           'audit': {'source': {'fusion_result': {'issues': []}}, 'result': {'edits': []}}}
    result = build_v20_post_generation(benchmark=Benchmark())(ctx)
    assert result['memory_update']['issues'] == []


def test_memory_update_maps_existing_issue_refs_and_keeps_concrete_evidence(tmp_path):
    memory = initialize_issue_memory(store_dir=tmp_path / 'memory', run_id='run')
    memory_value = merge_update(memory.memory, {
        'schema_version': 'issue_memory_update_v20.1', 'run_id': 'run', 'round_id': 'round-01',
        'issues': [{'new_issue_key': 'old-problem', 'problem': 'An old bounded problem.',
                    'source_refs': ['CF/old'], 'attempts': []}]})
    memory = type(memory)(memory.head_json, json.dumps(memory_value, sort_keys=True,
                                                       separators=(',', ':')))
    issue_id = memory.memory['issues'][0]['issue_id']
    ctx = {'run_id': 'run', 'round_id': 'round-02', 'parent_skill': '- Parent\n',
           'candidate_skill': '- Candidate\n', 'memory': memory,
           'audit': {'source': {'fusion_result': {'issues': [{
               'proposal_issue_id': 'PISSUE/current', 'decision': 'PROPOSE',
               'memory_issue_refs': [issue_id], 'current_finding_refs': ['CF/current'],
               'issue_statement': 'The old issue recurs with new evidence.'}]}},
                     'result': {'edits': [{
                         'edit_id': 'EDIT_V20/' + 'c' * 64, 'operation': 'REPLACE',
                         'after_text': 'Require a verified identifier before lookup.',
                         'memory_issue_refs': [issue_id], 'current_finding_refs': ['CF/current']}]}}}
    ctx['audit']['reviews'] = [{
        'proposal_id': 'PISSUE/current', 'verdict': 'VERIFIED',
        'reason': 'The current Parent rule still permits an unverified identifier.',
        'gap': {'statement': 'Require the identifier check before lookup.'},
    }]
    update = build_v20_memory_update(
        ctx, ctx['audit']['result'],
        {'task_count': 3, 'success_count': 2, 'compliance_count': 3},
        {'decision': 'ACCEPT'})
    row = update['issues'][0]
    attempt = row['attempts'][0]
    assert row['issue_id'] == issue_id
    assert attempt['source_refs'] == ['CF/current']
    assert 'Require a verified identifier' in attempt['approach']
    assert 'success 2/3' in attempt['assessment']
    assert 'Evidence Review VERIFIED' in attempt['assessment']
    assert 'identifier check before lookup' in attempt['assessment']
    assert all(not ref.startswith('GENERATION/') for ref in attempt['source_refs'])


def test_fusion_proposal_without_current_finding_has_a_resolvable_record():
    records = _fusion_records(SimpleNamespace(payload={
        'issues': [{'proposal_issue_id': 'PISSUE/history', 'decision': 'PROPOSE',
                    'issue_statement': 'Historical issue.', 'current_finding_refs': [],
                    'memory_issue_refs': [], 'memory_attempt_refs': []},
                   {'proposal_issue_id': 'PISSUE/no-edit', 'decision': 'NO_EDIT',
                    'issue_statement': 'No edit.', 'current_finding_refs': [],
                    'memory_issue_refs': [], 'memory_attempt_refs': []}]}))
    assert records == [{'ref': 'PISSUE/history', 'kind': 'REVIEW',
                        'statement': 'Historical issue.', 'evidence_refs': [],
                        'counterevidence_refs': [], 'edit_refs': [], 'source_refs': []}]


def test_history_only_update_does_not_copy_stale_source_ref(tmp_path):
    memory = initialize_issue_memory(store_dir=tmp_path / 'memory', run_id='run')
    memory_value = merge_update(memory.memory, {
        'schema_version': 'issue_memory_update_v20.1', 'run_id': 'run', 'round_id': 'round-01',
        'issues': [{'new_issue_key': 'history-only', 'problem': 'Historical problem.',
                    'source_refs': ['GENERATION/' + 'd' * 64], 'attempts': []}]})
    memory = type(memory)(memory.head_json, json.dumps(memory_value, sort_keys=True,
                                                       separators=(',', ':')))
    issue_id = memory.memory['issues'][0]['issue_id']
    ctx = {'run_id': 'run', 'round_id': 'round-02', 'parent_skill': '- Parent\n',
           'memory': memory, 'audit': {'source': {'fusion_result': {'issues': [{
               'proposal_issue_id': 'PISSUE/history', 'decision': 'PROPOSE',
               'memory_issue_refs': [issue_id], 'current_finding_refs': [],
               'issue_statement': 'Historical problem recurs.'}]}},
           'result': {'edits': [{'edit_id': 'EDIT_V20/' + 'e' * 64, 'operation': 'ADD',
                                  'after_text': 'Handle the bounded historical case.',
                                  'memory_issue_refs': [issue_id], 'current_finding_refs': []}]}}}
    update = build_v20_memory_update(ctx, ctx['audit']['result'], {}, {'decision': 'ACCEPT'})
    assert update['issues'][0]['attempts'][0]['source_refs'] == ['PISSUE/history']
