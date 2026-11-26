"""Bind the v26.9 Diagnosis and Preconditioner to the OfficeQA campaign."""
from copy import deepcopy
from hashlib import sha256

from ..v26_1.protocol import (
    ACTOR, actor_config, expected_background, render_prompt as render_officeqa_prompt, validate_actor,
)
from ..v26_8 import protocol as previous
from ..v26_8.protocol import (
    EDITOR_VERSION, FORMAL_CONTEXT, IDENTITY, LIMITS,
    MODEL_INPUT_VIEW, RECORD_VERSION, REPLAY_VERSION, REVISION, ROOT, SCORER_PROFILE,
    actor_base_protocol, background, digest, equal, execution_context,
    fields, initial_skill, public_task, require, score_view,
    source_pages, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_9'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_9_campaign_v1'
DIAGNOSIS_VERSION = 'v26_9_officeqa_diagnosis_v1'
PRECONDITIONER_VERSION = 'v26_9_officeqa_preconditioner_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'
APPROVED = {
    PROMPT_ROOT / 'diagnosis.md': 'fcee092a7f199aa4440f7b9e17d1030cb5ffeb1f726af82218cecd842db995ae',
    PROMPT_ROOT / 'editor.md': '76e9075f1dafa7da0cefe643eada6348ceb3033aff897a70b0953267114df92c',
    PROMPT_ROOT / 'preconditioner.md': 'bef28e3641c818828edabd73eaa83f2e5ac8c994e22b00fc0270c74a699bbea5',
    PROMPT_ROOT / 'replay.md': '7406c07f9c0f3ec657aa6d25636bb59b850d79d3e9f509a030dd38406c670509',
}

PLAN = deepcopy(previous.PLAN)
PLAN['execution']['train_workers'] = 10
PLAN['actor'] = actor_config()
for call in PLAN['module_calls'].values():
    call.update(model=ACTOR['model'], endpoint=ACTOR['endpoint'])
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts'].update(diagnosis=DIAGNOSIS_VERSION, preconditioner=PRECONDITIONER_VERSION)


def render_prompt(path, value):
    require(path in APPROVED, 'Unknown v26.9 prompt')
    prompt = render_officeqa_prompt(path, value)
    require(sha256(prompt.encode('utf-8')).hexdigest() == APPROVED[path],
            f'Approved v26.9 {path.stem} prompt differs')
    return prompt
