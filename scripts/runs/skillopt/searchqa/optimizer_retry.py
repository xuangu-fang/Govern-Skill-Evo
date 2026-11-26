"""Bind SearchQA's model settings to the exact OfficeQA training retry implementation."""
from contextlib import contextmanager
import json
import os
from unittest.mock import patch

from skillopt.model.openai_compatible_backend import configure_openai_compatible
from src.adapters.officeqa.skillopt_budget import ATTEMPTS, CAP_MULTIPLIER, LENGTHS_BEFORE_INCREASE
from src.adapters.officeqa.skillopt_optimizer import configured_provider
from src.skill_evolution.v28.storage import read


def retry_config():
    return dict(max_attempts_total=ATTEMPTS, lengths_before_increase=LENGTHS_BEFORE_INCREASE,
                cap_multiplier=CAP_MULTIPLIER, persist_attempts_on_resume=True,
                stages=['analyst', 'merge', 'ranking', 'slow_update', 'meta_skill'])


@contextmanager
def optimizer_provider(root, key, *, http_transport=None):
    cfg = read(root / 'optimizer.json')
    extra = {k: cfg[k] for k in ('thinking', 'reasoning_effort', 'stream')}
    with patch.dict(os.environ, {'OPTIMIZER_OPENAI_COMPATIBLE_EXTRA_BODY': json.dumps(extra)}):
        configure_openai_compatible(base_url=cfg['base_url'], api_key=key, model=cfg['model'],
                                    temperature=cfg['temperature'], timeout_seconds=cfg['timeout_seconds'],
                                    max_tokens=cfg['max_tokens'])
        with configured_provider(root / 'campaign', http_transport=http_transport) as budget:
            yield budget
