"""Read the dual-official ALFWorld training and its two independent final Tests."""
import json

from scripts.runs.alfworld.alfworld_aligned_common import read
from ..archive import read_evaluation, read_training
from .layout import ARTIFACTS, EXPERIMENTS

RUN = 'skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001'
RETEST = 'skilladam_alfworld_retest134_20261107_231301'


def read_test(run_id, items, actor, skill):
    return read_evaluation(ARTIFACTS / run_id, RUN, items, actor, skill)


def read_archive():
    config = EXPERIMENTS / RUN / 'config'
    training, skill = read_training(ARTIFACTS / RUN, config)
    items = read(config / 'splits/test/items.json')
    actor = read(config / 'actor.json')
    return training, [read_test(run_id, items, actor, skill) for run_id in (RUN + '_test134', RETEST)]


if __name__ == '__main__':
    training, evaluations = read_archive()
    print(json.dumps(dict(run_id=RUN, iterations=len(training['iterations']), evaluations=evaluations), indent=2))
