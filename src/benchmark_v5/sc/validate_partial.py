"""Offline audit of bounded interrupted runs, without pretending missing versions executed."""
import json
from benchmark_v5.core import ROOT, verify_audit, canonical
from benchmark_v5.calibration.runner import read, write, sha
from benchmark_v5.learning.runner import usage_and_message
from benchmark_v5.learning.cases import world_for
from .pilot import cases, initial_messages
from .environment import build
from .evaluation import evaluate, training_feedback


def validate(directory):
    for manifest in ('freeze.json', 'protected_before.json'):
        entries = read(directory/manifest)
        if manifest == 'freeze.json':entries = entries['source_sha256']
        for name, expected in entries.items():
            assert sha(ROOT/name) == expected, name
    config = read(directory/'protocol.json')
    rows = []
    for path in sorted(directory.glob('*/result.json')):
        r = read(path);a = read(path.parent/'audit.json');t = read(path.parent/'trace.json')
        verify_audit(a)
        case = next(c for c in cases() if c['id'] == r['case_id'])
        env = build(case, world_for('LG1'))
        skill = read(directory/f'states/{r["condition"]}.json')
        assert skill['sha256'] == t['state_sha256'] == r['state_sha256']
        messages = initial_messages(env, skill, r['condition'])
        assert messages == t['initial_messages']
        catalog = [{'type':'function','function':item} for item in env.catalog()]
        assert t['tools'] == catalog
        count = 0
        for rnd in t['rounds']:
            req = rnd['request']
            assert req['messages'] == messages and req['tools'] == catalog
            assert req['model'] == config['model'] and req['reasoning_effort'] == config['reasoning_effort']
            responses = [a['response'] for a in rnd['attempts'] if 'response' in a]
            if not responses:continue
            _, assistant, _ = usage_and_message(responses[-1], req)
            messages.append(assistant)
            outcomes = []
            for call in assistant.get('tool_calls', []):
                if env.state['closed'] or count >= config['limits']['tool_calls']:
                    out = {'error':'SESSION_CLOSED' if env.state['closed'] else 'CALL_BUDGET_EXHAUSTED'}
                else:
                    count += 1
                    try:args = json.loads(call['function']['arguments'])
                    except json.JSONDecodeError:args = None
                    out = env.call(call['function']['name'], args)
                outcomes.append(dict(tool_call_id=call['id'], result=out))
                messages.append(dict(role='tool', tool_call_id=call['id'], content=canonical(out)))
            assert outcomes == rnd.get('tool_results', [])
        env.end_budget()
        assert env.audit() == a
        assert not r['valid'] or evaluate(a) == r['score']
        if r['phase'] == 'train':
            fb = training_feedback(a)
            assert fb['scores'] == r['score']
            if (path.parent/'train_feedback.json').exists():
                assert fb == read(path.parent/'train_feedback.json')
        rows.append(r)
    # No learner was called in either interrupted run; no generated state is fabricated.
    assert not list((directory/'learning').glob('*.json'))
    assert not (directory/'states/S1.json').exists() and not (directory/'states/S2.json').exists()
    return dict(directory=str(directory.relative_to(ROOT)), executed=len(rows),
        planned_episodes=10, not_executed=10-len(rows), skill_updates=0,
        status='interrupted_before_S1', final_test_used=False,
        scores=[{k:r[k] for k in ('id','phase','score','budget_clean','deviations')} for r in rows],
        replayed=len(rows), contexts_reconstructed=len(rows), train_monitor_sc_consistent=True,
        actual_editor_isolation='not_exercised_no_learner_calls',
        source_hashes_and_history_unchanged=True,
        protected_files=len(read(directory/'protected_before.json')),
        api_attempts=sum(r['api_attempts'] for r in rows),
        unknown_usage_attempts=sum(r['unknown_usage_attempts'] for r in rows),
        total_tokens=sum(r['usage']['total_tokens'] for r in rows),
        budget_deviations=sum(not r['budget_clean'] for r in rows))


if __name__ == '__main__':
    dirs = [ROOT/f'artifacts/benchmarks/v5/sc-engineering-20261011-00{i}' for i in (1,2)]
    reports = [validate(d) for d in dirs]
    out = dict(validation_source_sha256=sha(ROOT/'src/benchmark_v5/sc/validate_partial.py'),
        runs=reports, total_tokens=sum(r['total_tokens'] for r in reports),
        api_attempts=sum(r['api_attempts'] for r in reports),
        conclusion='Steps 1 and 2 complete. Step 3 attempted, real multi-round loop remains unverified.')
    write(dirs[1]/'partial_validation.json',out)
    print(canonical(out))
