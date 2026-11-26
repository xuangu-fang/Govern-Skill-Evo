"""Bind the v26.6 method prompts to the existing OfficeQA execution protocol."""
from copy import deepcopy
from hashlib import sha256

from ..v26_3.protocol import render_prompt as render_officeqa_prompt
from ..v26_5 import protocol as previous
from ..v26_5.protocol import (
    ACTOR, FORMAL_CONTEXT, IDENTITY, LIMITS, MODEL_INPUT_VIEW, RECORD_VERSION,
    REPLAY_VERSION, REVISION, ROOT, SCORER_PROFILE, actor_base_protocol,
    actor_config, background, digest, equal, execution_context, expected_background,
    fields, initial_skill, public_task, require, score_view, source_pages, validate_actor,
    validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_6'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_6_campaign_v1'
DIAGNOSIS_VERSION = 'v26_6_officeqa_diagnosis_v1'
PRECONDITIONER_VERSION = 'v26_6_officeqa_preconditioner_v1'
EDITOR_VERSION = 'v26_6_officeqa_editor_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {
    PROMPT_ROOT / 'diagnosis.md': '274b5b19a944a59ff221e35dc53809fa706ce30b67a59aac56aa3928894efab3',
    PRECONDITIONER_PATH: '18df56e5066cddbc77a43e35c66ab2594ba045ef1f69641bd492221033f84970',
    PROMPT_ROOT / 'editor.md': '4e2b2ffa6948b87a0ce9bef5ccb4ec8d7445698f786845f2514c448a79d9519f',
    PROMPT_ROOT / 'replay.md': previous.APPROVED[previous.PROMPT_ROOT / 'replay.md'],
}

PLAN = deepcopy(previous.PLAN)
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts'].update(diagnosis=DIAGNOSIS_VERSION,
                               preconditioner=PRECONDITIONER_VERSION, editor=EDITOR_VERSION)


def render_prompt(path, value):
    require(path in APPROVED, 'Unknown v26.6 prompt')
    prompt = render_officeqa_prompt(path, value)
    require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
            f'Approved v26.6 {path.stem} prompt differs')
    return prompt
