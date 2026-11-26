from copy import deepcopy
import json

import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26 import evolution as ev, modules, stages
from src.skill_evolution.v26.config import method_config
from src.skill_evolution.v26.contracts import memory
from src.skill_evolution.v26.benchmarks.officeqa import prompting, protocol as p
from src.skill_evolution.v26.transport import RequestFailure
from .conftest import response


class FixedModules:
    """Deterministic JSON fixture, never a model client."""
    def __init__(self, *, branch=None, conflict=False):
        self.calls = []; self.branch = branch; self.conflict = conflict; self.editor_count = 0

    def __call__(self, name, messages, directory, config):
        self.calls.append((name, deepcopy(messages), str(directory), deepcopy(config)))
        value = json.loads(messages[1]['content'])
        if name == 'grouping':
            result = {'groups': [{'group_id': f'G{i}', 'members': [run['ref']],
                      'decision_problem': 'Select evidence for the requested answer.',
                      'shared_basis': f"Observed {run['ref']}:1.", 'important_differences': []}
                      for i, run in enumerate(value['runs'], 1)]}
        elif name == 'diagnosis':
            result = {'decision': 'revise', 'reason': 'P1:1 supports a focused hypothesis.',
                      'plan': {'goal': 'Use relevant source evidence.', 'updates': [
                          {'id': 'U1', 'text': 'Inspect the relevant source before answering.\n',
                           'basis': ['G1', 'P1:1']}], 'checks': []}}
            if self.branch == 'diagnosis_no_change': result.update(decision='no_change', plan=None)
        elif name == 'preconditioner':
            row = {'target': 'U1', 'focus': [], 'change': 'KEEP',
                   'reason': 'Supported by `Evidence:P1:1` within the stated scope.', 'to': None}
            result = {'adjustments': [row], 'checks': None}
            if self.branch == 'withdraw':
                row.update(focus=['D'], change='Withdraw this proposal.', to=[])
                result['checks'] = []
        elif name == 'editor':
            self.editor_count += 1
            parent = value['parent']; new = f'Candidate {self.editor_count}\n'
            old_header = '--- /dev/null\n' if parent is None else '--- a/SKILL.md\n'
            patch = old_header + '+++ b/SKILL.md\n@@\n'
            if parent is not None: patch += ''.join('-' + line for line in parent.splitlines(True))
            patch += '+' + new
            result = {'patch': patch, 'reason': 'Implement the supplied Effective Plan.'}
            if self.branch == 'editor_no_change': result['patch'] = ''
            if self.branch == 'needs_revision': result['patch'] = None
        elif name == 'replay':
            result = {'entries': [{'revises': [], 'knowledge': [
                {'text': 'The actual edit accompanied a paired answer difference in the supplied case; causation is unresolved.',
                 'evidence': ['diff', 'P1:1', 'Q1:outcome']}]}]}
            if self.branch == 'empty_replay': result = {'entries': []}
        elif name == 'verifier':
            result = {'results': [{'target': row['target'], 'verdict': 'CONFLICT' if self.conflict else 'SUPPORTED',
                       'issues': [{'statement': 'paired answer difference', 'reason': 'Synthetic correction fixture.',
                                   'evidence': ['Q1:outcome']}] if self.conflict else []} for row in value['targets']]}
        elif name == 'repair':
            result = {'changes': [{'target': row['target'], 'knowledge': {
                **row['knowledge'], 'text': row['knowledge']['text'].replace('paired answer difference', 'paired answer observation')}}
                for row in value['targets']]}
        else: raise AssertionError(name)
        return {'content': json.dumps(result), 'finish_reason': 'stop',
                'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}}


@pytest.fixture
def campaign(office):
    root, _, _, factory = office
    def create(*, answers=('0', '1000'), branch=None, conflict=False, batches=None, initial=True):
        adapter, provider = factory({'a': [response(x) for x in answers]}, gate_metric=p.EM_GATE)
        config = {'method': method_config(), 'benchmark': adapter.identity, 'actor': adapter.transport.metadata(),
                  'gate_metric': p.EM_GATE, 'optimization_splits': ['train'], 'batches': batches or [['a']],
                  'initial_skill': {'source': 'synthetic', 'text': 'Parent\n'} if initial else None,
                  'max_attempts': 6, 'continue_no_change': True, 'max_input_chars': 5000000,
                  'max_message_utf8_bytes': 6000000,
                  'module_calls': {name: {'endpoint': 'https://offline.invalid/chat/completions',
                      'model': f'fixture-{name}', 'max_tokens': 1000+i, 'timeout_seconds': 300, 'temperature': 1.0}
                      for i, name in enumerate(prompting.PROMPT_VERSIONS)}}
        return root / 'campaign', adapter, provider, config, FixedModules(branch=branch, conflict=conflict)
    return create


@pytest.mark.parametrize('answers,expected', [(('0', '1000'), 'ACCEPT'), (('1000', '1000'), 'RETAIN'), (('1000', '0'), 'RETAIN')])
def test_campaign_accept_retain_and_read_only_final_reload(campaign, answers, expected):
    root, adapter, provider, config, generate = campaign(answers=answers)
    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=config, generate=generate)
        assert result['status'] == 'complete'
        before_counts = (len(generate.calls), len(provider.requests))
        final = ev.final_parent(root)
        assert final.read_text() == ('Candidate 1\n' if expected == 'ACCEPT' else 'Parent\n')
        ev.run_campaign(root, generate=None)
        assert (len(generate.calls), len(provider.requests)) == before_counts
        active = memory.load_memory(root / 'rounds/R01/memory', memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        assert len(active['entries']) == 1  # RETAIN still learns.
    assert stages.read(root / 'rounds/R01/result.json')['outcome'] == expected
    assert [call[0] for call in generate.calls] == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier']


def test_all_seven_modules_and_one_repair(campaign):
    root, adapter, _, config, generate = campaign(conflict=True)
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        ev.final_parent(root)
    assert [c[0] for c in generate.calls] == list(prompting.PROMPT_VERSIONS)
    review = stages.read(root / 'rounds/R01/knowledge_review/result.json')
    assert review['repair_applied'] and not review['second_semantic_verification']
    assert 'paired answer observation' in json.dumps(stages.read(root / 'rounds/R01/memory/view.json'))


@pytest.mark.parametrize('branch,names', [
    ('diagnosis_no_change', ['grouping', 'diagnosis']),
    ('withdraw', ['grouping', 'diagnosis', 'preconditioner']),
    ('editor_no_change', ['grouping', 'diagnosis', 'preconditioner', 'editor'])])
def test_no_change_branches_skip_candidate_replay_and_memory(campaign, branch, names):
    root, adapter, provider, config, generate = campaign(branch=branch)
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        assert ev.final_parent(root).read_text() == 'Parent\n'
    assert [c[0] for c in generate.calls] == names and len(provider.requests) == 1
    assert not (root / 'rounds/R01/candidate_runs').exists()
    assert stages.read(root / 'state.json')['active_memory'] == 'initial_memory'


def test_editor_null_is_semantic_stop_not_an_invalid_output_retry(campaign):
    root, adapter, provider, config, generate = campaign(branch='needs_revision')
    with using_benchmark(adapter):
        with pytest.raises(ev.Stopped, match='semantic'): ev.run_campaign(root, config=config, generate=generate)
        count = len(generate.calls)
        with pytest.raises(ValueError, match='Semantic blocker'): ev.run_campaign(root, generate=generate, resume=True)
        assert len(generate.calls) == count and len(provider.requests) == 1
    assert stages.read(root / 'state.json')['next_round'] == 1
    assert (root / 'rounds/R01/editor/result.json').exists()


def test_empty_replay_skips_verifier_repair_but_commits(campaign):
    root, adapter, _, config, generate = campaign(branch='empty_replay', initial=False)
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        assert ev.final_parent(root).read_text() == 'Candidate 1\n'
    assert [c[0] for c in generate.calls][-1] == 'replay'
    assert stages.read(root / 'rounds/R01/memory/active.json')['commits'] == ['campaign_R01']


@pytest.mark.parametrize('phase', ['candidate_runs', 'knowledge_review', 'memory_prepared', 'before_publish', 'after_publish'])
def test_crash_recovery_reuses_requests_and_publishes_once(campaign, phase):
    root, adapter, provider, config, generate = campaign()
    def crash(name):
        if name == phase: raise KeyboardInterrupt('Synthetic interruption')
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate, hook=crash)
        ev.run_campaign(root, generate=generate, resume=True)
        ev.final_parent(root)
    assert len(provider.requests) == 2 and len(generate.calls) == 6
    assert stages.read(root / 'state.json')['next_round'] == 2
    assert stages.read(root / 'rounds/R01/memory/active.json')['commits'] == ['campaign_R01']


def test_two_epochs_use_published_skill_and_knowledge_only_memory(campaign):
    root, adapter, provider, config, generate = campaign(answers=('0', '1000', '1000', '0'), batches=[['a'], ['a']])
    config['epoch_schedule'] = {'epochs': 2, 'round_epochs': [1, 2], 'batch_size': 1}
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        assert ev.final_parent(root).read_text() == 'Candidate 1\n'
    calls = [json.loads(c[1][1]['content']) for c in generate.calls if c[0] == 'preconditioner']
    assert calls[1]['parent'] == 'Candidate 1\n' and len(calls[1]['memory']['entries']) == 1
    assert set(calls[1]['memory']) == {'format', 'entries'} and len(provider.requests) == 4
    assert stages.read(root / 'rounds/R02/result.json')['outcome'] == 'RETAIN'


@pytest.mark.parametrize('mutation', ['prompt', 'config', 'data', 'state', 'response', 'candidate', 'gate', 'memory'])
def test_resume_rejects_drift_without_calls(campaign, monkeypatch, mutation):
    root, adapter, provider, config, generate = campaign()
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        counts = (len(generate.calls), len(provider.requests))
        if mutation == 'prompt':
            original = adapter.frozen_files
            monkeypatch.setattr(adapter, 'frozen_files', lambda: {**original(), 'drift': 'changed'})
        elif mutation == 'config':
            value = stages.read(root / 'config.json'); value['max_attempts'] = 5; stages.save(root / 'config.json', value)
        elif mutation == 'data':
            path = adapter.runtime.text_root / 'treasury_bulletin_2011_03.txt'; path.write_text('changed source')
        elif mutation == 'state':
            value = stages.read(root / 'state.json'); value['parent'] = 'initial_skill.md'; stages.save(root / 'state.json', value)
        elif mutation == 'response':
            path = root / 'rounds/R01/grouping/attempts/001/response.json'; value = stages.read(path)
            value['content'] = '{}'; stages.save(path, value)
        elif mutation == 'candidate': (root / 'rounds/R01/editor/attempts/001/candidate.md').write_text('changed')
        elif mutation == 'gate':
            path = root / 'rounds/R01/gate/result.json'; value = stages.read(path)
            value['result']['decision'] = 'RETAIN'; stages.save(path, value)
        elif mutation == 'memory':
            path = root / 'rounds/R01/knowledge_review/candidate.json'; stages.save(path, {'entries': []})
        with pytest.raises((ValueError, ev.Stopped)): ev.run_campaign(root, generate=generate, resume=True)
        assert (len(generate.calls), len(provider.requests)) == counts


@pytest.mark.parametrize('mutation', ['test_split', 'undeclared_validation', 'duplicate', 'no_gate', 'unknown_flag', 'changed_actor'])
def test_configuration_rejected_before_execution(campaign, mutation):
    root, adapter, provider, config, generate = campaign()
    if mutation == 'test_split': config['batches'] = [['t']]; config['optimization_splits'] = ['test']
    elif mutation == 'undeclared_validation': config['batches'] = [['v']]
    elif mutation == 'duplicate': config['batches'] = [['a'], ['a']]
    elif mutation == 'no_gate': config['gate_metric'] = None
    elif mutation == 'unknown_flag': config['stage0'] = True
    elif mutation == 'changed_actor': config['actor']['max_completion_tokens'] = 999
    with using_benchmark(adapter), pytest.raises(ValueError): ev.run_campaign(root, config=config, generate=generate)
    assert not generate.calls and not provider.requests


def test_memory_commit_crash_before_active_switch_is_idempotent(campaign, monkeypatch):
    root, adapter, _, config, generate = campaign(); original = memory.write_record
    crashed = False
    def interrupted(path, value):
        nonlocal crashed
        if path.name == 'active.json' and path.parent.name == 'memory' and value.get('commits') and not crashed:
            crashed = True; raise KeyboardInterrupt('Immutable commit saved, index not switched')
        return original(path, value)
    with using_benchmark(adapter):
        monkeypatch.setattr(memory, 'write_record', interrupted)
        with pytest.raises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate)
        assert stages.read(root / 'state.json')['active_memory'] == 'initial_memory'
        ev.run_campaign(root, generate=generate, resume=True)
        ev.final_parent(root)
    assert len(generate.calls) == 6
    assert stages.read(root / 'rounds/R01/memory/active.json')['commits'] == ['campaign_R01']


def test_single_writer_lock_blocks_second_mutator(campaign):
    import fcntl
    root, adapter, provider, config, generate = campaign(); root.mkdir()
    with (root / '.lock').open('a') as lock, using_benchmark(adapter):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError): ev.run_campaign(root, config=config, generate=generate)
    assert not generate.calls and not provider.requests


def test_actor_batch_failure_drains_and_resume_preserves_six_attempts(campaign, office):
    from src.adapters.officeqa.transport import RequestFailure as ActorFailure
    root, _, _, config, generate = campaign()
    adapter, provider = office[3]({'a': [ActorFailure('timeout') for _ in range(6)],
                                  'b': [response('1000')]}, gate_metric=p.EM_GATE)
    config['actor'] = adapter.transport.metadata(); config['batches'] = [['a', 'b']]
    with using_benchmark(adapter):
        with pytest.raises(Exception): ev.run_campaign(root, config=config, generate=generate)
        assert len(provider.requests) == 7 and not generate.calls
        before = ev.cost_summary(root)
        assert before['actor_http_requests'] == 7 and before['incomplete_actor_cases'] == 1
        assert before['total_tokens']['unknown_requests'] == 6
        with pytest.raises(Exception): ev.run_campaign(root, generate=generate, resume=True)
        assert len(provider.requests) == 7
        assert ev.cost_summary(root) == before
    records = [json.loads(line) for line in (root / 'rounds/R01/parent_runs/actor/results.jsonl').read_text().splitlines()]
    assert len(records) == 1  # The other queued task completed despite a's failure.


def test_costs_count_requests_not_response_recovery_or_duplicate_evidence(campaign):
    root, adapter, provider, config, good = campaign(); first = True
    def generate(name, messages, directory, cfg):
        nonlocal first
        if first:
            first = False; raise RequestFailure('Unknown request usage')
        return good(name, messages, directory, cfg)
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        before = ev.cost_summary(root)
        ev.final_parent(root); ev.run_campaign(root, resume=True)
    assert ev.cost_summary(root) == before
    assert before['actor_http_requests'] == 2 and before['module_http_requests'] == 7
    assert before['model_rounds_accepted'] == 2 and before['tool_calls_committed'] == 0
    assert before['input_tokens'] == {'known_sum': 260, 'unknown_requests': 1}
    assert before['reasoning_tokens']['unknown_requests'] == 9


def test_status_cli_needs_no_credentials(campaign, capsys, monkeypatch):
    from src.skill_evolution.v26.cli import main
    root, adapter, _, config, generate = campaign(branch='diagnosis_no_change')
    with using_benchmark(adapter): ev.run_campaign(root, config=config, generate=generate)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    main(['status', str(root)])
    output = json.loads(capsys.readouterr().out)
    assert output['state']['next_round'] == 2 and not output['integrity_verified']


def test_historical_revision_retrieves_only_cited_sources_in_second_round(campaign):
    root, adapter, _, config, fixed = campaign(answers=('0', '1000', '0', '1000'), batches=[['a'], ['a']])
    config['epoch_schedule'] = {'epochs': 2, 'round_epochs': [1, 2], 'batch_size': 1}
    def generate(name, messages, directory, cfg):
        response = fixed(name, messages, directory, cfg)
        value = json.loads(messages[1]['content'])
        if name == 'replay' and value['memory']['entries']:
            entry = value['memory']['entries'][0]
            retained = deepcopy(entry['knowledge'][0])
            retained['text'] += ' The historical comparison remains conditional.'
            parsed = json.loads(response['content'])
            parsed['entries'][0]['revises'] = [entry['id']]
            parsed['entries'][0]['knowledge'].insert(0, retained)
            response['content'] = json.dumps(parsed)
        return response
    with using_benchmark(adapter):
        ev.run_campaign(root, config=config, generate=generate)
        ev.final_parent(root)
    view = stages.read(root / 'rounds/R02/knowledge_review/input.json')['verifier_input']
    history = {key for key in view['source_records'] if '/' in key}
    assert history == {'campaign_R01/diff', 'campaign_R01/P1:1', 'campaign_R01/Q1:outcome'}
    assert stages.read(root / 'rounds/R02/memory/active.json')['active_ids'] == ['M2']


def test_continue_no_change_false_stops_after_published_round(campaign):
    root, adapter, provider, config, generate = campaign(branch='diagnosis_no_change', batches=[['a'], ['b']])
    config['continue_no_change'] = False
    with using_benchmark(adapter):
        result = ev.run_campaign(root, config=config, generate=generate)
        assert result['outcome'] == 'no_change'
        with pytest.raises(ValueError, match='not complete'): ev.final_parent(root)
    assert len(provider.requests) == 1 and stages.read(root / 'state.json')['next_round'] == 2
    assert not (root / 'rounds/R02').exists()


def test_inflight_source_change_prevents_official_publication(campaign):
    root, adapter, _, config, generate = campaign()
    def change(name):
        if name == 'before_publish':
            (adapter.runtime.text_root / 'treasury_bulletin_2011_03.txt').write_text('changed during round')
    with using_benchmark(adapter), pytest.raises(ValueError, match='Frozen value changed'):
        ev.run_campaign(root, config=config, generate=generate, hook=change)
    assert stages.read(root / 'state.json')['next_round'] == 1
    assert stages.read(root / 'state.json')['active_memory'] == 'initial_memory'
