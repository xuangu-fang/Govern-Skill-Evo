"""Capacity-only recovery preserves frozen semantics and completed stages."""
from copy import deepcopy
import json
import pytest
from src.skill_evolution.v23 import evolution as ev, preconditioner, memory
from tests.skill_evolution.v23.test_evolution import Harness, config, run

LIMITS = {'max_input_chars': 1000000, 'max_message_utf8_bytes': 1500000}


def stopped(root):
    h = Harness(); h.fail = 'preconditioner'; h.failures = 3; h.stop = 'timeout'
    with pytest.raises(ev.Stopped):
        run(root, h, config=config(1))
    return h


def test_capacity_resume_preserves_completed_stages(tmp_path):
    h = stopped(tmp_path)
    original = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and (
        'grouping' in p.parts or 'diagnosis' in p.parts or 'parent_runs' in p.parts or
        p.name in ('initial_config.json', 'config.json', 'round_input.json', 'error.json'))}
    amendment = tmp_path/'capacity.json'
    ev.save(amendment, {'stage': 'preconditioner', 'reason': 'Authorized local capacity change', 'input_limits': LIMITS})
    result = run(tmp_path, h, resume=True, recovery_file=amendment)
    assert result['status'] == 'complete'
    assert h.calls.count('grouping') == h.calls.count('diagnosis') == 1
    assert len(h.actor_calls) == 4
    assert all(p.read_bytes() == content for p, content in original.items())
    effective = ev._config(tmp_path)
    assert all(effective[k] == v for k, v in LIMITS.items())
    assert effective['call_config']['max_tokens'] == 16384
    ev.validate_config(effective)
    before = h.calls[:]; run(tmp_path, h, resume=True); assert before == h.calls


@pytest.mark.parametrize('change', ['prompt', 'actor', 'model', 'config', 'unreviewed_adapter'])
def test_capacity_recovery_rejects_unapproved_changes(tmp_path, monkeypatch, change):
    stopped(tmp_path)
    proposal = {'stage': 'preconditioner', 'reason': 'Capacity only', 'input_limits': LIMITS}
    contract = ev.frozen_contract()
    if change in ('prompt', 'actor', 'unreviewed_adapter'):
        key = {'prompt': 'src/skill_evolution/v23/preconditioner_prompt.md',
               'actor': 'src/adapters/alfworld/skill_runtime.py',
               'unreviewed_adapter': 'src/skill_evolution/v23/evolution.py'}[change]
        contract[key] += '\n# changed\n'
        monkeypatch.setattr(ev, 'frozen_contract', lambda: contract)
    elif change == 'model': proposal['call_config'] = config()['call_config']
    else:
        cfg = ev.read(tmp_path/'config.json'); cfg['max_steps'] = 51; ev.save(tmp_path/'config.json', cfg)
    path = tmp_path/'capacity.json'; ev.save(path, proposal)
    with pytest.raises(ValueError): ev.record_recovery(tmp_path, path)
    assert not list((tmp_path/'recoveries').glob('*.json'))


def test_explicit_adapter_content_is_required_and_recorded(tmp_path, monkeypatch):
    stopped(tmp_path)
    key = 'src/skill_evolution/v23/evolution.py'
    old = ev.frozen_contract(); new = deepcopy(old); new[key] += '\n# reviewed capacity adapter\n'
    monkeypatch.setattr(ev, 'frozen_contract', lambda: new)
    path = tmp_path/'capacity.json'
    ev.save(path, {'stage': 'preconditioner', 'reason': 'Reviewed adapter', 'input_limits': LIMITS,
                  'orchestrator_change': {'before': old[key], 'after': new[key]}})
    ev.record_recovery(tmp_path, path); ev._check_contract(tmp_path)
    record = ev.read(tmp_path/'recoveries/001.json')
    assert record['previous_content'][key] == old[key]
    assert record['contract_changes'] == {key: new[key]}
    assert record['previous_input_limits'] == {'max_input_chars': 300000, 'max_message_utf8_bytes': 400000}


@pytest.mark.parametrize('value', [0, -1, True, '1500000'])
def test_invalid_byte_limits(value):
    with pytest.raises(ValueError): ev.message_byte_limit({'max_message_utf8_bytes': value})


def test_byte_alias_and_conflict():
    assert ev.message_byte_limit({'max_input_bytes': 400000}) == 400000
    assert ev.message_byte_limit(LIMITS) == 1500000
    with pytest.raises(ValueError): ev.message_byte_limit({**LIMITS, 'max_input_bytes': 400000})


def test_actual_r02_full_input_fits_authorized_capacity():
    root = ev.ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
    rd = root/'rounds/R02'
    frozen = ev.read(rd/'round_input.json')
    g = rd/'grouping'/ev.read(rd/'grouping/result.json')['path']
    d = rd/'diagnosis'/ev.read(rd/'diagnosis/result.json')['path']
    saved = {**preconditioner.read_upstream(g, d), 'memory': frozen['memory']}
    encoded = json.dumps(preconditioner.messages_for(saved), ensure_ascii=False)
    assert len(encoded) == 337927
    assert len(encoded) > 300000
    assert len(encoded) <= LIMITS['max_input_chars']
    assert len(encoded.encode('utf-8')) <= ev.message_byte_limit(LIMITS)
    assert ev.read(rd/'preconditioner/attempts/001/error.json')['request_invoked'] is False


R04_LIMITS = {'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000}


def test_r04_full_input_unchanged_and_passes_real_module(tmp_path):
    root = ev.ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
    rd = root/'rounds/R04'
    def selected(name):
        stage = rd/name
        return stage/ev.read(stage/'result.json')['path']
    mem = ev.read(rd/'round_input.json')['memory']
    saved = {**preconditioner.read_upstream(selected('grouping'), selected('diagnosis')), 'memory': mem}
    original = preconditioner.messages_for(saved)
    encoded = json.dumps(original, ensure_ascii=False)
    assert len(encoded) == 1217815
    assert len(encoded.encode('utf-8')) == 1217849
    calls = []
    def offline(messages, dest):
        assert messages == original
        calls.append(messages)
        return {'content': json.dumps({'decision': 'ready', 'reason': 'Offline Keep fixture',
                                       'adjustments': [], 'checks': None}), 'finish_reason': 'stop'}
    with pytest.raises(ValueError, match='character budget'):
        preconditioner.run_preconditioner(selected('grouping'), selected('diagnosis'), tmp_path/'old',
            generate=offline, memory=mem, max_input_chars=1000000)
    assert calls == []
    preconditioner.run_preconditioner(selected('grouping'), selected('diagnosis'), tmp_path/'new',
        generate=offline, memory=mem, max_input_chars=R04_LIMITS['max_input_chars'])
    assert len(calls) == 1
    assert ev.read(tmp_path/'new/messages.json') == original
    for rn in ['R02', 'R04']:
        assert ev.read(root/'rounds'/rn/'preconditioner/attempts/001/error.json')['request_invoked'] is False


def test_all_five_module_paths_receive_new_limits(tmp_path, monkeypatch):
    cfg = config(1); cfg.pop('max_input_bytes'); cfg.update(R04_LIMITS)
    seen = {}
    for name, module in ev.MODULES.items():
        original = getattr(module, 'run_'+name)
        def capture(*args, _name=name, _original=original, **kwargs):
            seen[_name] = kwargs['max_input_chars']
            return _original(*args, **kwargs)
        monkeypatch.setattr(module, 'run_'+name, capture)
    h = Harness()
    assert run(tmp_path, h, config=cfg)['status'] == 'complete'
    assert seen == {name: 4000000 for name in ev.MODULES}
    assert ev.message_byte_limit(ev._config(tmp_path)) == 6000000
    assert ev._config(tmp_path)['call_config']['max_tokens'] == 16384


@pytest.mark.parametrize('name', list(ev.MODULES))
@pytest.mark.parametrize('extra', [0, 1])
def test_exact_utf8_byte_boundary_on_each_stage(tmp_path, name, extra):
    cfg = config(1); cfg.pop('max_input_bytes'); cfg.update(R04_LIMITS)
    # Build JSON whose bytes exactly reach the cap; one extra byte must fail.
    messages = [{'role': 'user', 'content': '\u4e2d'}]
    overhead = len(json.dumps(messages, ensure_ascii=False).encode('utf-8'))
    messages[0]['content'] += 'a' * (6000000 - overhead + extra)
    assert len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) == 6000000 + extra
    root = ev.initialize(tmp_path, cfg); rd = root/'rounds/R01'; rd.mkdir(parents=True)
    called = []
    def generate(actual, dest):
        called.append(actual); return {'ok': True}
    def invoke(dest, request, call_config):
        dest.mkdir(parents=True)
        return request(messages, dest)
    if extra:
        with pytest.raises(ev.Stopped, match='byte budget'):
            ev._model_stage(root, rd, name, invoke, cfg, generate, False)
        assert not called
        error = ev.read(rd/name/'attempts/001/error.json')
        assert error['request_invoked'] is False and error['retryable'] is False
    else:
        ev._model_stage(root, rd, name, invoke, cfg, generate, False)
        assert len(called) == 1


def test_second_capacity_overlay_only_changes_thresholds(tmp_path):
    stopped(tmp_path)
    p = tmp_path/'proposal.json'
    for limits in [LIMITS, R04_LIMITS]:
        ev.save(p, {'stage': 'preconditioner', 'reason': 'Explicit capacity recovery', 'input_limits': limits})
        ev.record_recovery(tmp_path, p)
    effective = ev._config(tmp_path)
    expected = ev.read(tmp_path/'initial_config.json'); expected.pop('max_input_bytes'); expected.update(R04_LIMITS)
    assert effective == expected
    assert ev.read(tmp_path/'recoveries/001.json')['input_limits'] == LIMITS
    assert ev.read(tmp_path/'recoveries/002.json')['previous_input_limits'] == LIMITS
    assert ev.read(tmp_path/'recoveries/002.json')['contract_changes'] == {}
