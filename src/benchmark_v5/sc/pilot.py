"""Two-round LG1 engineering loop. No final Test, oracle, raw arm or outcome-driven reruns."""
import argparse
from copy import deepcopy
from unittest.mock import patch
from benchmark_v5.core import ROOT, canonical, digest, verify_audit
from benchmark_v5.calibration.runner import read, write, sha, now
from benchmark_v5.calibration.transport import chat
from benchmark_v5.learning import runner, protocol
from benchmark_v5.learning.cases import lg_case, world_for
from .environment import build
from .evaluation import evaluate, training_feedback, VERSION
from .rescore import DEST

SYSTEM = ('你是授权沙盒业务Agent。使用公开请求、工具和当前Skill办理当前任务，核验当前事实，'
          '遵守公开授权与必要程序，不编造证据或状态。未知业务规律可以依据工具反馈合理处理。'
          '最后调用finish提交真实结构化回执。只有提供的Skill跨任务保留。')
EDITOR = ('你是Skill更新器。依据当前Skill和授权Train任务的真实执行、S/C反馈更新通用Skill。'
          '保留正确经验，修复有证据的缺陷，区分观察、推断与未知边界；不要把订单ID或个案答案写成规则。'
          '不能读取Monitor、Test、Oracle、私有世界或评价源码。只返回完整新版Skill文本，不调用工具。'
          '文本力求简短，不能从稀疏日期样本编造精确阈值。')
S0 = ('核验公开委托、当前订单和资料，依据当前事实完成授权业务；遵守公开程序要求，'
      '保留真实操作凭证，准确反馈结果。服务商具体资料组合与替代规则尚未知。')


def cases():
    # Reuse known development structures, distinct identities. This is not a new mechanism or Test.
    return [lg_case('ENG-T1', age=5*86400, split='engineering_train'),
            lg_case('ENG-T2', issuer='carrier', age=5*86400, split='engineering_train'),
            lg_case('ENG-T3', age=10*86400, split='engineering_train'),
            lg_case('ENG-T4', age=5*86400, reason='accidental', split='engineering_train'),
            lg_case('ENG-M1', age=2*86400, split='engineering_monitor'),
            lg_case('ENG-M2', issuer='carrier', age=2*86400, split='engineering_monitor')]


def config():
    limits = dict(protocol.LIMITS)
    limits.update(model_turns=12, tool_calls=40, completion_tokens=32768,
                  cumulative_prompt_tokens=240000, timeout_seconds=600, transport_retries=0)
    return dict(model=protocol.MODEL, temperature=0.2, reasoning_effort='high', limits=limits,
                rounds=2, monitor=['ENG-M1', 'ENG-M2'], train=[['ENG-T1', 'ENG-T2'], ['ENG-T3', 'ENG-T4']],
                classification='engineering_only_no_final_test', grader=VERSION,
                selection='none: run two scheduled updates, never choose or optimize on Monitor')


def state(version, content, source_ids):
    result = protocol.make_state('LG1', version, [], content)
    result.update(train_sources=list(source_ids))
    result['sha256'] = digest({k: v for k, v in result.items() if k != 'sha256'})
    return result


def initial_messages(env, skill, version):
    return [dict(role='system', content=SYSTEM), dict(role='user', content=canonical(dict(
        request=env.request(), skill=protocol.state_content(skill, 'LG1', version))))]


def freeze():
    if (DEST/'freeze.json').exists():
        raise RuntimeError('ALREADY_FROZEN')
    write(DEST/'protocol.json', config())
    write(DEST/'private/cases.json', cases())
    write(DEST/'states/S0.json', state('S0', S0, []))
    (DEST/'states/S0.md').write_text(S0+'\n')
    files = list((ROOT/'src/benchmark_v5/sc').glob('*.py'))
    files += list((ROOT/'src/benchmark_v5/learning').glob('*.py'))
    files += list((ROOT/'tests/benchmarks/v5/sc').glob('*.py'))
    files += [ROOT/'src/benchmark_v5/core.py', ROOT/'src/benchmark_v5/calibration/transport.py',
              ROOT/'src/benchmark_v5/calibration/runner.py',
              ROOT/'docs/benchmarks/v5/SC.md', DEST/'protocol.json', DEST/'private/cases.json']
    write(DEST/'freeze.json', dict(frozen_at_utc=now(), source_sha256={str(p.relative_to(ROOT)): sha(p) for p in files}))
    print('Frozen: 10 episodes (4 Train + 6 Monitor), 2 Skill updates; no final Test', flush=True)


def check():
    for p, h in read(DEST/'freeze.json')['source_sha256'].items():
        if sha(ROOT/p) != h:
            raise RuntimeError('FROZEN_SOURCE_CHANGED: '+p)
    for p, h in read(DEST/'protected_before.json').items():
        if sha(ROOT/p) != h:
            raise RuntimeError('HISTORICAL_FILE_CHANGED: '+p)


def execute(case_id, version, phase, transport=chat):
    skill = read(DEST/f'states/{version}.json')
    job = dict(id=f'{phase}__{version}__{case_id}', case_id=case_id, kind='LG1',
               condition=version, model=protocol.MODEL, phase=phase)
    result_path = DEST/job['id']/'result.json'
    if result_path.exists():
        return read(result_path)
    # Sequential process-local adapter leaves all frozen legacy sources untouched.
    with patch.object(runner, 'heldout_cases', cases), patch.object(runner, 'build', build), \
         patch.object(runner, 'evaluate', evaluate), patch.object(protocol, 'initial_messages', initial_messages):
        result = runner.run_episode(read(DEST/'protocol.json'), job, DEST, skill, transport=transport)
    print(canonical({k: result[k] for k in ('id', 'valid', 'budget_clean', 'stop', 'score')}), flush=True)
    return result


def observation(result):
    if result['phase'] != 'train' or not result['valid']:
        raise ValueError('ONLY_VALID_TRAIN_EXECUTION_MAY_REACH_EDITOR')
    folder = DEST/result['id']
    audit, trace = read(folder/'audit.json'), read(folder/'trace.json')
    return dict(episode_id=result['id'], request=json_content(trace['initial_messages'][1])['request'],
                interactions=[dict(tool=e['tool'], arguments=e['arguments'], result=e['result']) for e in audit['events']],
                feedback=training_feedback(audit))


def json_content(message):
    import json
    return json.loads(message['content'])


def editor_messages(previous, observations):
    if any(o['feedback']['grader_version'] != VERSION or not o['episode_id'].startswith('train__') for o in observations):
        raise ValueError('INVALID_EDITOR_FEEDBACK_SOURCE')
    return [dict(role='system', content=EDITOR), dict(role='user', content=canonical(dict(
        current_skill=previous['content'], train=observations)))]


def update(version, train_results, transport=chat):
    previous = read(DEST/f'states/S{version-1}.json')
    state_path, trace_path = DEST/f'states/S{version}.json', DEST/f'learning/S{version}.json'
    if state_path.exists():
        return
    if trace_path.exists():
        raise RuntimeError('EXISTING_LEARNER_ATTEMPT_REQUIRES_AUDIT_NO_AUTORETRY')
    observations = [observation(r) for r in train_results]
    cfg = read(DEST/'protocol.json')
    payload = dict(model=protocol.MODEL, temperature=cfg['temperature'], reasoning_effort=cfg['reasoning_effort'],
                   max_tokens=cfg['limits']['max_tokens_per_call'], messages=editor_messages(previous, observations))
    record = dict(request=payload, attempts=[], parent_sha256=previous['sha256'], started_at_utc=now())
    write(trace_path, record)
    try:
        response = runner.call_model(payload, record, cfg['limits'], transport)
        usage, message, deviations = runner.usage_and_message(response, payload)
        record.update(usage=usage, deviations=deviations, finished_at_utc=now())
        if deviations or not message.get('content') or message.get('tool_calls'):
            raise RuntimeError('INVALID_SKILL_OUTPUT_NO_RETRY')
        skill = state(f'S{version}', message['content'], previous['train_sources']+[r['id'] for r in train_results])
        write(state_path, skill)
        (DEST/f'states/S{version}.md').write_text(message['content']+'\n')
        record['output_sha256'] = skill['sha256']
        print(f'S{version} saved from {len(train_results)} actual Train episodes', flush=True)
    finally:
        write(trace_path, record)


def run(transport=chat):
    check()
    cfg = read(DEST/'protocol.json')
    for v in range(3):
        for cid in cfg['monitor']:
            r = execute(cid, f'S{v}', 'monitor', transport)
            if not r['valid'] or not r['budget_clean']:
                raise RuntimeError('ENGINEERING_STOP_INVALID_OR_BUDGET_DEVIATION')
        if v < 2:
            results = []
            for cid in cfg['train'][v]:
                r = execute(cid, f'S{v}', 'train', transport)
                if not r['valid'] or not r['budget_clean']:
                    raise RuntimeError('ENGINEERING_STOP_INVALID_OR_BUDGET_DEVIATION')
                results.append(r)
                write(DEST/r['id']/'train_feedback.json', training_feedback(read(DEST/r['id']/'audit.json')))
            update(v+1, results, transport)
        check()


def validate():
    check()
    all_cases = {c['id']: c for c in cases()}
    results = []
    for path in sorted(DEST.glob('*/result.json')):
        r = read(path)
        audit, trace = read(path.parent/'audit.json'), read(path.parent/'trace.json')
        verify_audit(audit)
        env = build(all_cases[r['case_id']], world_for('LG1'))
        skill = read(DEST/f'states/{r["condition"]}.json')
        assert skill['sha256'] == r['state_sha256'] == trace['state_sha256']
        messages = initial_messages(env, skill, r['condition'])
        assert messages == trace['initial_messages']
        assert trace['tools'] == [{'type': 'function', 'function': t} for t in env.catalog()]
        tool_count = 0
        for rnd in trace['rounds']:
            assert rnd['request']['messages'] == messages
            assert rnd['request']['tools'] == trace['tools']
            response = next(a['response'] for a in reversed(rnd['attempts']) if 'response' in a)
            _, assistant, _ = runner.usage_and_message(response, rnd['request'])
            messages.append(assistant)
            assert len(assistant.get('tool_calls', [])) == len(rnd.get('tool_results', []))
            for t, expected in zip(assistant.get('tool_calls', []), rnd.get('tool_results', [])):
                import json
                try:
                    args = json.loads(t['function']['arguments'])
                except json.JSONDecodeError:
                    args = None
                if env.state['closed'] or tool_count >= config()['limits']['tool_calls']:
                    out = {'error': 'SESSION_CLOSED' if env.state['closed'] else 'CALL_BUDGET_EXHAUSTED'}
                else:
                    tool_count += 1
                    out = env.call(t['function']['name'], args)
                assert expected['tool_call_id'] == t['id']
                assert out == expected['result']
                messages.append(dict(role='tool', tool_call_id=t['id'], content=canonical(out)))
        env.end_budget()
        assert env.audit() == audit
        assert evaluate(audit) == r['score']
        if r['phase'] == 'train':
            assert training_feedback(audit) == read(path.parent/'train_feedback.json')
        results.append(r)
    for v in (1, 2):
        lr = read(DEST/f'learning/S{v}.json')
        previous = read(DEST/f'states/S{v-1}.json')
        rr = [next(r for r in results if r['phase'] == 'train' and r['case_id'] == cid)
              for cid in config()['train'][v-1]]
        assert lr['request']['messages'] == editor_messages(previous, [observation(r) for r in rr])
        skill = read(DEST/f'states/S{v}.json')
        raw = lr['attempts'][-1]['response']['choices'][0]['message']['content']
        assert skill == state(f'S{v}', raw, previous['train_sources']+[r['id'] for r in rr])
    summary = []
    for v in range(3):
        rows = [r for r in results if r['phase'] == 'monitor' and r['condition'] == f'S{v}']
        summary.append(dict(skill=f'S{v}', n=len(rows), **{k:sum(r['score'][k] for r in rows) for k in ('S','C','SC')}))
    learners = [read(DEST/f'learning/S{v}.json') for v in (1,2)]
    report = dict(classification='engineering_only_no_effect_claim', grader=VERSION,
        episodes=len(results), skill_updates=2, monitor=summary,
        replay_and_input_reconstruction=True, train_monitor_same_grader=True,
        editor_train_only=True, final_test_used=False,
        protected_files=len(read(DEST/'protected_before.json')),
        api_attempts=sum(r['api_attempts'] for r in results)+sum(len(l['attempts']) for l in learners),
        total_tokens=sum(r['usage']['total_tokens'] for r in results)+sum(l['usage']['total_tokens'] for l in learners),
        budget_deviations=sum(not r['budget_clean'] for r in results)+sum(bool(l['deviations']) for l in learners))
    assert len(results)==10
    write(DEST/'validation.json', report)
    print(canonical(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'run', 'validate'])
    args = parser.parse_args()
    try:
        globals()[args.action]()
    except Exception as exc:
        if args.action == 'run':
            write(DEST/'interruption.json', dict(at_utc=now(), error_type=type(exc).__name__,
                reason=str(exc), policy='Stopped; no automatic replacement or extra model calls.'))
        raise
