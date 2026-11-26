"""Bind the reviewed v26.5 prompts to the v26.4 production protocol."""
from copy import deepcopy
from hashlib import sha256

from ..v26_4 import protocol as previous
from ..v26_4.protocol import (
    ACTOR, DIAGNOSIS_VERSION, FORMAL_CONTEXT, IDENTITY, LIMITS, MODEL_INPUT_VIEW,
    RECORD_VERSION, REPLAY_VERSION, REVISION, ROOT, SCORER_PROFILE, actor_base_protocol,
    actor_config, background, digest, equal, execution_context, expected_background,
    fields, initial_skill, public_task, require, score_view, source_pages, validate_actor,
    validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_5'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_5_campaign_v1'
PRECONDITIONER_VERSION = 'v26_5_officeqa_preconditioner_v1'
EDITOR_VERSION = 'v26_5_officeqa_editor_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {
    PROMPT_ROOT / 'diagnosis.md': previous.APPROVED[previous.PROMPT_ROOT / 'diagnosis.md'],
    PRECONDITIONER_PATH: 'f0fa3cbe75129adc798e76023c091144cb72155094c299cbae3da571a2c82984',
    PROMPT_ROOT / 'editor.md': '0cfe6ed9a3f40171ab5ee11c8ba98829adac336f73ec32d56ce42d4365e68063',
    PROMPT_ROOT / 'replay.md': previous.APPROVED[previous.PROMPT_ROOT / 'replay.md'],
}

PLAN = deepcopy(previous.PLAN)
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts'].update(preconditioner=PRECONDITIONER_VERSION, editor=EDITOR_VERSION)


def render_prompt(path, value):
    require(path in APPROVED, 'Unknown v26.5 prompt')
    prompt = previous.render_prompt(path, value)
    require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
            f'Approved v26.5 {path.stem} prompt differs')
    return prompt
