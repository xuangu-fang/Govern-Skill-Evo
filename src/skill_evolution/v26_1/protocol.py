"""OfficeQA execution remains owned by v26; only the evolution binding changes."""
from copy import deepcopy
import json
from pathlib import Path
from src.skill_evolution.v26.benchmarks.officeqa.protocol import (
    IDENTITY, FORMAL_CONTEXT, fields, require, equal, digest, background,
    execution_context, public_task, score_view, validate_task, source_pages,
)

RECORD_VERSION = 'v26_1_officeqa_execution_v2'
ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / 'docs/methods/v26_1'
PROMPT_ROOT = DESIGN / 'prompts'
PLAN = json.loads((DESIGN / 'experiment_plan.json').read_text())
REVISION = PLAN['benchmark']['dataset_revision']
SCORER_PROFILE = PLAN['benchmark']['score_view']
MODEL_INPUT_VIEW = PLAN['method']['model_input_view']
ACTOR = PLAN['actor']
LIMITS = PLAN['actor_task_output_limits']['optimization']


def actor_config():
    return deepcopy(ACTOR)


def initial_skill():
    return (DESIGN / 'baseline/officeqa/initial_skill.md').read_bytes().decode('utf-8')


def actor_base_protocol():
    from skilladam.benchmarks.officeqa.rollout import VENDOR_PROMPT
    value = VENDOR_PROMPT.format(skill_section='')
    require(value == (DESIGN / 'baseline/officeqa/actor_base_protocol.md').read_text().rstrip('\n'),
            'OfficeQA base protocol changed')
    return value


def validate_actor(value):
    expected = actor_config()
    if value.get('transport') == 'offline_fixture':
        expected.update(transport='offline_fixture', endpoint=None)
    require(equal(value, expected), 'OfficeQA Actor settings differ')


def expected_background():
    value = background({**ACTOR, 'task_max_completion_tokens': LIMITS})
    require(value['tool_schemas'] == json.loads((DESIGN / 'baseline/officeqa/tool_schemas.json').read_text()),
            'OfficeQA tool schemas changed')
    require(value['tool_output_limits'] == {'read_chars': 4000, 'grep_matches': 20, 'glob_matches': 50} and
            value['oracle_limits'] == {'page_chars': 24000, 'total_chars': 80000}, 'OfficeQA limits changed')
    return value


def render_prompt(path, value):
    require(equal(value, expected_background()), 'OfficeQA method execution background differs')
    prompt = path.read_text()
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1 and
            prompt.split(marker)[1].split(end)[0] == actor_base_protocol(), 'Prompt base protocol differs')
    require('{{' not in prompt and 'shared_initial' not in prompt, 'Unexpanded or wrong-domain Prompt')
    return prompt
