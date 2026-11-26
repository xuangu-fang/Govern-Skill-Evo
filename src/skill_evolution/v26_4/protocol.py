"""The v26.3 production profile with the four reviewed v26.4 prompts."""
from copy import deepcopy
from hashlib import sha256

from ..v26_3 import protocol as previous
from ..v26_3.protocol import (
    ACTOR, FORMAL_CONTEXT, IDENTITY, LIMITS, MODEL_INPUT_VIEW, RECORD_VERSION,
    REVISION, ROOT, SCORER_PROFILE, actor_base_protocol, actor_config, background,
    digest, equal, execution_context, expected_background, fields, initial_skill,
    public_task, require, score_view, source_pages, validate_actor, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_4'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_4_campaign_v1'
DIAGNOSIS_VERSION = 'v26_4_officeqa_diagnosis_v2'
PRECONDITIONER_VERSION = 'v26_4_officeqa_preconditioner_v2'
EDITOR_VERSION = 'v26_4_officeqa_editor_v2'
REPLAY_VERSION = 'v26_4_officeqa_replay_v2'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {
    PROMPT_ROOT / 'diagnosis.md': '4e9c2875fff217d242833cac7a5589776e06d94e54d0fb8ae3b3ad3c0bc6bd0f',
    PROMPT_ROOT / 'preconditioner.md': 'f4f1d078c8b7d2812e18a7b68a61b4a99a0afe18ed238e03c2f434be8548815e',
    PROMPT_ROOT / 'editor.md': 'cb16d3045e4995ba2d5df6537bd6873c75dd60dc389571855419ca54d446df85',
    PROMPT_ROOT / 'replay.md': 'b68102bc029e8b123a6a214f2eaa22e7f5ad23b612f6d0fc667d18a2acdc84b5',
}

PLAN = deepcopy(previous.PLAN)
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts'].update(diagnosis=DIAGNOSIS_VERSION, preconditioner=PRECONDITIONER_VERSION,
                                 editor=EDITOR_VERSION, replay=REPLAY_VERSION)


def render_prompt(path, value):
    prompt = previous.render_prompt(path, value)
    if path in APPROVED:
        require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
                f'Approved v26.4 {path.stem} prompt differs')
    return prompt
