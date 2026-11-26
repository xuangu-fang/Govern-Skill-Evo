"""Bind the v26.8 Preconditioner to the v26.7 OfficeQA campaign."""
from copy import deepcopy
from hashlib import sha256

from ..v26_3.protocol import render_prompt as render_officeqa_prompt
from ..v26_7 import protocol as previous
from ..v26_7.protocol import (
    ACTOR, DIAGNOSIS_VERSION, EDITOR_VERSION, FORMAL_CONTEXT, IDENTITY, LIMITS,
    MODEL_INPUT_VIEW, RECORD_VERSION, REPLAY_VERSION, REVISION, ROOT, SCORER_PROFILE,
    actor_base_protocol, actor_config, background, digest, equal, execution_context,
    expected_background, fields, initial_skill, public_task, require, score_view,
    source_pages, validate_actor, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_8'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_8_campaign_v1'
PRECONDITIONER_VERSION = 'v26_8_officeqa_preconditioner_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {PROMPT_ROOT / path.name: digest_value for path, digest_value in previous.APPROVED.items()}
APPROVED[PRECONDITIONER_PATH] = '1c071b6953b651a93f1b2773e0cb9f1024e3ea406d5c0e4f20b5fcbe431b3141'

PLAN = deepcopy(previous.PLAN)
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts']['preconditioner'] = PRECONDITIONER_VERSION


def render_prompt(path, value):
    require(path in APPROVED, 'Unknown v26.8 prompt')
    prompt = render_officeqa_prompt(path, value)
    require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
            f'Approved v26.8 {path.stem} prompt differs')
    return prompt
