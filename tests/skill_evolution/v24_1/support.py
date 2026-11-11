from src.skill_evolution.v24_1 import config
from src.skill_evolution.v24_1.benchmark import current
from tests.skill_evolution.v24.test_equivalence import CapturedHarness
from tests.skill_evolution.v23_5.test_knowledge_review import cfg


def migrated(rounds=1):
    value = cfg(rounds)
    value['method']['knowledge_review'] = config.REVIEW_DISABLED
    value.update(actor_max_workers=10, max_attempts=6, retry_delay_seconds=0)
    for key in ('verifier', 'repair'):
        value['module_max_tokens'].pop(key, None)
    return config.baseline_config(value, benchmark=current())
