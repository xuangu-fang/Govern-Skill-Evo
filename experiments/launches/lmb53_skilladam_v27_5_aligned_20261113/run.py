"""Preflight, train, or evaluate the five-round LMB SkillAdam baseline."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs import evaluate_lmb_skilladam_v27_2_feedback as evaluation
from scripts.runs import run_lmb_skilladam_v27_2_feedback as training
from skilladam.core.case_sampler import DisjointCaseSampler, IterationCases
from src.skill_evolution.v27.facts import require

CONFIG = HERE / 'config.json'
REFERENCE = ROOT / 'experiments/launches/v27_5_lmb53_20261113/config.json'
TRAIN = ROOT / 'experiments/baselines/lmb_skilladam' / HERE.name
TEST = ROOT / 'experiments/evaluations' / (HERE.name + '_test')


class AlignedRunner(training.feedback.FeedbackRunner):
    def _build_sampler(self, cases):
        schedule = training.base.read(REFERENCE)['batches']
        ids = [task for batch in schedule for task in batch]
        require(list(map(len, schedule)) == [11, 11, 11, 10, 10] and len(set(ids)) == 53,
                'Expected five rounds covering 53 distinct tasks')
        require(ids == [case.case_id for case in cases] == list(self.config.optimization_case_ids),
                'Case order differs from v27.5')
        require(self.config.validation_mode == 'same_batch' and not self.config.shuffle_optimization_pool
                and self.config.sampling_strategy == 'sequential', 'Unexpected native sampler settings')
        return DisjointCaseSampler([
            IterationCases(tuple(batch), tuple(batch), validation_mode='same_batch') for batch in schedule
        ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('preflight', 'train', 'test'), nargs='?', default='preflight')
    stage = parser.parse_args().stage
    require(Path(sys.prefix).name == 'LiveMathematicianBench', 'Use the LiveMathematicianBench environment')
    expected = training.base.read(training.CONFIG)
    expected['v27_config'] = str(REFERENCE.relative_to(ROOT))
    expected['native'].update(train_size=11, validation_size=11)
    expected['native']['feedback_loop'].update(min_iterations=5, max_iterations=5)
    require(training.base.read(CONFIG) == expected, 'Unexpected SkillAdam configuration drift')

    original_prepare = training.prepare

    def prepare():
        cfg, dataset, initial, native, context, snapshot = original_prepare()
        actor = training.base.NativeAdapter(dataset.root)
        runner = AlignedRunner(config=native, adapter=actor, backend=None, context=context,
                               output_dir=TRAIN / 'native')
        batches = list(runner._build_sampler(training.base.native_cases(dataset)))
        require([list(b.validation_case_ids) for b in batches] == snapshot['batches'],
                'Same-batch validation differs from the frozen training schedule')
        snapshot['sources'][str(Path(__file__).resolve().relative_to(ROOT))] = hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest()
        return cfg, dataset, initial, native, context, snapshot

    # The existing baseline builds a sampler once for offline validation and again
    # for the real feedback loop. Bind both to the same runner for this launch.
    with ExitStack() as stack:
        stack.enter_context(training.actor_profile())
        stack.enter_context(patch.object(training, 'CONFIG', CONFIG))
        stack.enter_context(patch.object(training.base, 'SkillAdamRunner', AlignedRunner))
        stack.enter_context(patch.object(training.feedback, 'FeedbackRunner', AlignedRunner))
        stack.enter_context(patch.object(training, 'prepare', prepare))
        if stage == 'preflight':
            *_, snapshot = prepare()
            _, protocol = evaluation.protocol()
            print(json.dumps({'status': 'valid', 'batch_sizes': list(map(len, snapshot['batches'])),
                              'optimization_cases': sum(map(len, snapshot['batches'])),
                              'test_cases': len(protocol['tasks']), 'validation': 'same_batch'}))
        elif stage == 'train':
            training.run(TRAIN, resume=(TRAIN / 'frozen.json').exists())
        else:
            print(json.dumps(evaluation.evaluate(TRAIN, TEST, resume=(TEST / 'evaluation.json').exists())))


if __name__ == '__main__':
    main()
