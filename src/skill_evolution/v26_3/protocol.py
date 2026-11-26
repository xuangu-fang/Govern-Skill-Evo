"""The v26.2 production route and the approved v26.3 method prompt."""
from copy import deepcopy
from hashlib import sha256

from ..v26_2 import protocol as previous
from ..v26_2.protocol import (
    FORMAL_CONTEXT, IDENTITY, LIMITS, MODEL_INPUT_VIEW, RECORD_VERSION, REVISION,
    ROOT, SCORER_PROFILE, actor_base_protocol, background, digest, equal,
    execution_context, fields, initial_skill, public_task, require, score_view,
    source_pages, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_3'
PROMPT_ROOT = DESIGN / 'prompts'
METHOD_VERSION = 'v26_3_campaign_v1'
PRECONDITIONER_VERSION = 'v26_3_officeqa_preconditioner_v1'
PRECONDITIONER_PATH = PROMPT_ROOT / 'preconditioner.md'

PLAN = deepcopy(previous.PLAN)
ACTOR = PLAN['actor']
ACTOR.update(model='deepseek-v4.1-flash',
             endpoint='http://llm-proxy.intra.xiaojukeji.com/chat/completions')
for call in PLAN['module_calls'].values():
    call.update(model=ACTOR['model'], endpoint=ACTOR['endpoint'])
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts']['preconditioner'] = PRECONDITIONER_VERSION
PLAN['method']['prompt_paths'] = {stage: f'prompts/{stage}.md' for stage in PLAN['method']['prompts']}


def actor_config():
    return deepcopy(ACTOR)


def validate_actor(value):
    expected = actor_config()
    if value.get('transport') == 'offline_fixture':
        expected.update(transport='offline_fixture', endpoint=None)
    require(equal(value, expected), 'v26.3 OfficeQA Actor settings differ')


def expected_background():
    # Preserve checks on the base protocol, oracle limits and native tool schemas.
    return {**previous.expected_background(), 'model': ACTOR['model']}


def render_prompt(path, value):
    require(equal(value, expected_background()), 'v26.3 method execution background differs')
    prompt = previous.render_prompt(path, previous.expected_background())
    if path == PRECONDITIONER_PATH:
        require(sha256(prompt.encode()).hexdigest() ==
                'cb59b127b989017d3c1c7fc399d3f171c67bb519dfb729bccf07c136d1e9e115',
                'Approved v26.3 Preconditioner differs')
    return prompt
