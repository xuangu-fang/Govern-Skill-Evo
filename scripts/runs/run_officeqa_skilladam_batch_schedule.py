"""Run OfficeQA SkillAdam with explicit sequential same-batch sizes."""
import argparse
from functools import partial
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.runs import run_officeqa_skilladam_task_budget as budget
from skilladam.core.case_sampler import IterationCases

launch = budget.launch


def schedule(native, sizes, case_ids):
    ordered = tuple(native.optimization_case_ids)
    launch.require(tuple(case_ids) == ordered, 'Optimization pool order changed')
    launch.require(native.validation_mode == 'same_batch'
                   and native.sampling_strategy == 'sequential'
                   and not native.shuffle_optimization_pool, 'Expected sequential same-batch sampling')
    launch.require(len(sizes) == native.feedback_loop.max_iterations
                   and all(type(n) is int and n > 0 for n in sizes)
                   and sum(sizes) == len(ordered), 'Schedule must cover exactly one epoch')
    batches = []
    start = 0
    for size in sizes:
        ids = ordered[start:start + size]
        batches.append(IterationCases(ids, ids, validation_mode='same_batch'))
        start += size
    return tuple(batches)


class ScheduledRunner(launch.TrainingSkillAdamRunner):
    def __init__(self, *, sizes, **kwargs):
        super().__init__(**kwargs)
        self.sizes = sizes

    def _build_sampler(self, cases):
        return schedule(self.config, self.sizes, (case.case_id for case in cases))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'train'))
    parser.add_argument('directory')
    parser.add_argument('--config', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    config = launch.read(args.config)
    launch.require(config['schedule_launcher_sha256'] == launch.digest(__file__),
                   'Schedule launcher identity changed')
    plan, dataset, _, _, _ = budget.prepare(config, args.directory)
    native = launch.adam_config(plan['native_config'])
    sizes = config['batch_sizes']
    batches = schedule(native, sizes, (case.case_id for case in dataset.cases('train')))
    credentials = budget.base.read_credentials(ROOT / '.env')
    base_url = credentials['OPENAI_BASE_URL'].rstrip('/')
    launch.require(config['optimizer']['base_url'] == base_url
                   and plan['actor']['endpoint'] == base_url + '/chat/completions',
                   'Endpoints differ from .env')
    if args.action == 'preflight':
        print(json.dumps({'batches': [b.training_case_ids for b in batches],
                          'actor': plan['actor']['model'], 'optimizer': config['optimizer']['model'],
                          'requests': 0}, indent=2))
        return
    key = credentials['OPENAI_API_KEY']
    backend = budget.base.generation_backend(config, args.directory, key)
    key_name = 'OFFICEQA_SKILLADAM_ACTOR_KEY'
    with (budget.runtime_binding(config), patch.dict(os.environ, {key_name: key}),
          patch.object(launch, 'TrainingSkillAdamRunner', partial(ScheduledRunner, sizes=sizes))):
        result = launch.train(config, args.directory, actor_key_env=key_name,
                              resume=args.resume, optimizer_backend=backend)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
