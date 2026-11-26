"""Agreed DocVQA messages; original image bytes and complete question text."""
import base64
from copy import deepcopy
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
CONTEXT = Path(__file__).with_name('context')
REVISION = '539088ef8a8ada01ac8e2e6d4e372586748a265e'
DEFAULT_DATA_ROOT = ROOT / 'data/docvqa/releases' / REVISION
PROMPT_PROFILE = 'v29_docvqa_actor_v1'
SCORER_PROFILE = 'v29_docvqa_skilladam_scoring_v1'
GATE_PROFILE = 'v29_docvqa_hard_strict_increase_v1'
RECORD_VERSION = 'v29_docvqa_execution_v1'
FACTS_VERSION = 'v29_docvqa_facts_v1'
MODEL_INPUT_VIEW = 'v29_docvqa_pairs_content_v1'
FORMAL_CONTEXT = 'docvqa_single_turn_v1'
ACTOR = {'transport': 'direct_http', 'endpoint': 'https://api.deepseek.com/chat/completions',
         'model': 'deepseek-flash', 'max_tokens': 32768, 'temperature': 1.0,
         'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'},
         'timeout_seconds': 300, 'connect_timeout_seconds': 10,
         'request_attempts_total': 6, 'sdk_retries': 0, 'retry_delay_seconds': 1.0,
         'retry_policy': 'technical_and_length_shared_six_v1'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), f'{label}: unexpected fields')


def equal(left, right):
    return left == right


def background(config):
    return validate_config(config)


def actor_base_protocol():
    return (CONTEXT / 'actor_system.md').read_text(encoding='utf-8').replace(
        '{skill_section}', '').removesuffix('\n')


def execution_context(config):
    validate_config(config)
    return (CONTEXT / 'actor_runtime.md').read_text(encoding='utf-8').removesuffix('\n')


def nonempty_text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label} must be nonempty text')
    return value


def validate_answers(answers):
    require(isinstance(answers, list) and bool(answers), 'Reference answers must be a nonempty list')
    for answer in answers:
        nonempty_text(answer, 'Reference answer')
    return answers


def actor_config():
    return deepcopy(ACTOR)


def validate_config(config):
    require(config == ACTOR, 'Actor configuration differs from the agreed v29 settings')
    return deepcopy(config)


def initial_skill():
    return (CONTEXT / 'initial_skill.md').read_text(encoding='utf-8')


def validate_case(case):
    nonempty_text(case.case_id, 'Task ID')
    require(set(case.payload) == {'question', 'image_path'}, 'Expected question and image_path payload')
    nonempty_text(case.payload['question'], 'Question')
    nonempty_text(case.payload['image_path'], 'Image path')
    validate_answers(case.reference)
    require(case.metadata.get('split') in ('train', 'test'), 'Invalid effective split')
    require(case.metadata.get('source_split') in ('train', 'val', 'test'), 'Invalid original split')
    require((case.metadata['split'] == 'test') == (case.metadata['source_split'] == 'test'),
            'Original/effective split differs')
    return case


def build_messages(*, question, image_path, skill, image_root=None):
    nonempty_text(question, 'Question')
    require(skill is None or isinstance(skill, str), 'Skill must be text or None')
    path = Path(nonempty_text(image_path, 'Image path'))
    if not path.is_absolute():
        require(image_root is not None, 'Relative image path requires an explicit image root')
        path = Path(image_root) / path
    image = path.read_bytes()  # A missing image must fail before any API request.
    require(bool(image), 'Image file is empty')
    mime = mimetypes.guess_type(path.name)[0] or 'image/png'
    uri = f'data:{mime};base64,' + base64.b64encode(image).decode('ascii')
    section = f'## Skill\n{skill.strip()}\n\n' if skill and skill.strip() else ''
    system = (CONTEXT / 'actor_system.md').read_text(encoding='utf-8').replace('{skill_section}', section)
    user = (CONTEXT / 'actor_user.md').read_text(encoding='utf-8').replace('{question}', question)
    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': [
            {'type': 'text', 'text': user},
            {'type': 'image_url', 'image_url': {'url': uri}},
        ]},
    ]


def messages_for_case(case, skill):
    validate_case(case)
    return build_messages(**case.payload, skill=skill, image_root=case.metadata.get('image_root'))


def text_projection(messages, image_path):
    """Replace only the image block; preserve the actual executed system/user text."""
    projected = deepcopy(messages)
    require(len(projected) == 2 and projected[0].get('role') == 'system'
            and projected[1].get('role') == 'user', 'Expected one system/user pair')
    parts = projected[1]['content']
    require(isinstance(parts, list) and len(parts) == 2 and parts[0].get('type') == 'text'
            and parts[1].get('type') == 'image_url', 'Expected text followed by one image')
    parts[1] = {'type': 'text', 'text':
                f'[Image attached to Actor: {image_path}; image pixels are not supplied to this module.]'}
    return projected
