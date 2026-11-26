"""Run the aligned training and held-out evaluation sequentially in separate processes."""
from datetime import datetime
from pathlib import Path
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TRAIN = ROOT / 'experiments/baselines/lmb_skilladam' / HERE.name
TEST = ROOT / 'experiments/evaluations' / (HERE.name + '_test')
OLD = ROOT / 'experiments/baselines/lmb_skilladam/lmb53_actor65536_20261103_115844/technical_retry_v1/standard_test_summary.json'
V27 = ROOT / 'experiments/evaluations/v27_2_diag_v3_precond_v3_lmb53_20261105_210532_test'

def read(path):
    return json.loads(path.read_text())

def state(stage, **fields):
    tmp = HERE / 'status.tmp'
    tmp.write_text(json.dumps({'stage': stage, 'time': datetime.now().astimezone().isoformat(),
                               'pid': os.getpid(), **fields}, indent=2)+'\n')
    tmp.replace(HERE / 'status.json')

def command(stage, script, args):
    state(stage)
    # Training's dotenv reader uses environment values first. Remove both overrides.
    env = dict(os.environ)
    for name in ('OPENAI_API_KEY', 'OPENAI_BASE_URL'):
        env.pop(name, None)
    with (HERE / (stage + '.log')).open('a') as log:
        code = subprocess.call([sys.executable, '-B', '-u', ROOT / 'scripts/runs' / script, *args],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    if code:
        state(stage + '_stopped', exit_code=code)
        raise SystemExit(code)

def scores(root):
    rows = read(root / 'runs/records.json')
    result = {r['task_id']: r['execution']['metrics']['em'] for r in rows}
    assert len(result) == len(rows) == 124 and sum(result.values()) == read(root / 'summary.json')['success_count']
    return result

def compare():
    new, v27 = scores(TEST), scores(V27)
    prev = read(OLD)
    old = {row['task_id']: row['em'] for row in prev['cases']}
    assert len(old) == len(prev['cases']) == 124 and sum(old.values()) == prev['correct']
    assert set(new) == set(old) == set(v27)
    pairs = {}
    for name, baseline in [('old_skilladam',old), ('v27_2',v27)]:
        wins = [t for t in new if new[t] > baseline[t]]
        losses = [t for t in new if new[t] < baseline[t]]
        pairs[name] = {'wins':wins, 'losses':losses, 'both_correct':sum(new[t] == baseline[t] == 1 for t in new),
                       'both_wrong':sum(new[t] == baseline[t] == 0 for t in new)}
    totals = {k:sum(v.values()) for k,v in [('new_skilladam',new), ('old_skilladam',old), ('v27_2',v27)]}
    (HERE / 'comparison.json').write_text(json.dumps({'tasks':len(new),'correct':totals,'paired':pairs,
        'new_summary':str(TEST/'summary.json'),'old_summary':str(OLD),'v27_summary':str(V27/'summary.json')},indent=2)+'\n')
    state('complete', correct=totals)

if not (TRAIN / 'native/final_skill.md').exists():
    command('training', 'run_lmb_skilladam_v27_2_feedback.py', ['run','--output',TRAIN]
            + (['--resume'] if (TRAIN/'frozen.json').exists() else []))
if not (TEST / 'summary.json').exists():
    command('test', 'evaluate_lmb_skilladam_v27_2_feedback.py', ['run','--training-dir',TRAIN,'--output',TEST]
            + (['--resume'] if (TEST/'evaluation.json').exists() else []))
compare()
