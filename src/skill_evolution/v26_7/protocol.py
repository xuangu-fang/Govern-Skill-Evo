"""Bind the v26.7 Preconditioner to the v26.5 OfficeQA campaign."""
from copy import deepcopy
from hashlib import sha256

from ..v26_3.protocol import render_prompt as render_officeqa_prompt
from ..v26_5 import protocol as previous
from ..v26_5.protocol import (
    ACTOR, DIAGNOSIS_VERSION, EDITOR_VERSION, FORMAL_CONTEXT, IDENTITY, LIMITS,
    MODEL_INPUT_VIEW, RECORD_VERSION, REPLAY_VERSION, REVISION, ROOT, SCORER_PROFILE,
    actor_base_protocol, actor_config, background, digest, equal, execution_context,
    expected_background, fields, initial_skill, public_task, require, score_view,
    source_pages, validate_actor, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_7'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_7_campaign_v1'
PRECONDITIONER_VERSION = 'v26_7_officeqa_preconditioner_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {PROMPT_ROOT / path.name: digest_value for path, digest_value in previous.APPROVED.items()}
APPROVED[PRECONDITIONER_PATH] = 'e6ba28272525307995181b30126969b2a8686799316a88b6f43f94c34dd0c12d'

PLAN = deepcopy(previous.PLAN)
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts']['preconditioner'] = PRECONDITIONER_VERSION


def render_prompt(path, value):
    require(path in APPROVED, 'Unknown v26.7 prompt')
    prompt = render_officeqa_prompt(path, value)
    require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
            f'Approved v26.7 {path.stem} prompt differs')
    return prompt
