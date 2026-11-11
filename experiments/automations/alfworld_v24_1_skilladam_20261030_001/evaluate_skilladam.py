"""Final SkillAdam ALFWorld Test; defaults to offline validation, requires --start."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import frozen_file, load_plan
sys.path[:0] = [str(ROOT), str(ROOT/'scripts/runs')]
from scripts.runs.alfworld.alfworld_aligned_common import read, write, sha, require, configure_runtime, run_batch

PLAN = Path(__file__).with_name('plan.json')


def completed_skill(plan):
    """Both methods must have finished training, including pending Momentum."""
    vroot = ROOT/plan['jobs']['v24_1']['training_output']
    from src.skill_evolution.v24_1 import evolution as ev
    from src.skill_evolution.v24_1.benchmark import using_benchmark
    from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
    cfg = read(vroot/'config.json')
    require(cfg == read(ROOT/plan['jobs']['v24_1']['experiment']/'config/campaign.json'),
            'V24.1 training configuration differs from the authorized experiment')
    require(read(vroot/'state.json')['next_round'] == len(cfg['batches'])+1, 'V24.1 training incomplete')
    with using_benchmark(ALFWorldAdapter()):
        require(ev.final_parent(vroot) is not None, 'V24.1 final Skill missing')
    training = ROOT/plan['jobs']['skilladam']['training_output']
    completed, checkpoint = read(training/'completion.json'), read(training/'checkpoint.json')
    require(completed['status'] == 'complete' and len(completed['iterations']) == 6,
            'SkillAdam training incomplete')
    require(checkpoint['next_iteration'] == 6 and checkpoint['pending_post_decision'] is None,
            'SkillAdam iterations or Momentum incomplete')
    skill = (training/'final_skill.md').read_text()
    require(bool(skill.strip()) and skill == checkpoint['current_skill'], 'SkillAdam final Skill mismatch')
    return skill


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true')
    args = parser.parse_args()
    plan = load_plan(PLAN)
    for name, expected in plan['frozen_inputs_sha256'].items():
        require(sha(frozen_file(name)) == expected, 'Scheduled input changed: '+name)
    skill = completed_skill(plan)
    experiment = ROOT/plan['jobs']['skilladam']['experiment']
    actor, tasks = read(experiment/'actor.json'), read(experiment/'splits/test/items.json')
    require(len(tasks) == len({t['id'] for t in tasks}) == 134 and
            all(t['id'].startswith('test:') for t in tasks), 'Invalid final Test manifest')
    require(actor['workers'] == 10 and actor['request_attempts'] == 6, 'Actor profile changed')
    output = ROOT/plan['jobs']['skilladam']['test_output']
    if not args.start:
        print(json.dumps({'status':'ready','test_tasks':len(tasks),'model_requests':0}))
        return
    output.mkdir(parents=True, exist_ok=True)
    with (output/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        signature = {'skill':skill,'actor':actor,'tasks':tasks}
        if (output/'inputs.json').exists():
            require(read(output/'inputs.json') == signature, 'Test inputs changed on resume')
        else:
            write(output/'inputs.json', signature)
        if (output/'summary.json').exists():
            require(read(output/'summary.json')['status'] == 'complete', 'Invalid Test result')
            return
        configure_runtime(actor)
        rows = run_batch(actor, tasks, skill, output)
        require([r['id'] for r in rows] == [t['id'] for t in tasks], 'Test coverage mismatch')
        write(output/'summary.json', {'status':'complete','completed':len(rows),
              'success':sum(r['hard'] for r in rows), 'success_rate':sum(r['hard'] for r in rows)/len(rows),
              'skill_sha256':sha(output/'actor_skill.md'),'tasks':rows,
              'training_updated':False})


if __name__ == '__main__':
    main()
