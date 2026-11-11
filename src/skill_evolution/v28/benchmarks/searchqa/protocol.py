"""SearchQA single-turn messages with exact, untruncated task text."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from ... import validation

PROMPT_PROFILE = 'v28_searchqa_actor_answer_element_words_v1'
SCORER_PROFILE = 'v28_searchqa_skilladam_scoring_v1'
GATE_PROFILE = 'v28_searchqa_em_strict_increase_v1'
CONTEXT = Path(__file__).with_name('context')
ROOT = Path(__file__).resolve().parents[5]
RECORD_VERSION = 'v28_searchqa_execution_v1'
FACTS_VERSION = 'v28_searchqa_facts_v1'
MODEL_INPUT_VIEW = 'v28_searchqa_pairs_content_v1'
FORMAL_CONTEXT = 'searchqa_single_turn_v1'
ACTOR = {'transport': 'direct_http', 'endpoint': 'https://api.deepseek.com/chat/completions',
         'model': 'deepseek-flash', 'max_tokens': 49152, 'temperature': 1.0,
         'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'},
         'timeout_seconds': 300, 'connect_timeout_seconds': 10, 'request_attempts_total': 6,
         'sdk_retries': 0, 'retry_delay_seconds': 1.0, 'retry_policy': 'technical_and_length_shared_six_v1'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def equal(left, right):
    return exact(left) == exact(right)


def digest(value):
    return hashlib.sha256(exact(value).encode()).hexdigest()


def file_digest(path):
    state = validation.current()
    if state is not None:
        state.watch_file(path)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), f'{label}: unexpected fields')


def background(config):
    require(any(equal(config, actor_config(size)) for size in (15, 30)),
            'Actor differs from a frozen v28 configuration')
    return deepcopy(config)


def actor_config(batch_size=15):
    require(type(batch_size) is int and batch_size in (15, 30, 50, 60), 'Unsupported SearchQA batch size')
    return {**deepcopy(ACTOR), 'max_tokens': 32768 if batch_size in (30, 50, 60) else 49152}


def implementation_identity():
    state = validation.current()
    if state is None:
        return _implementation_identity()
    if 'implementation' not in state.identities:
        state.identities['implementation'] = _implementation_identity()
    return deepcopy(state.identities['implementation'])


def _implementation_identity():
    """Behavior profiles only; source files are not execution prerequisites."""
    return {'prompt': prompt_identity(), 'scorer': SCORER_PROFILE, 'gate': GATE_PROFILE}


def actor_base_protocol():
    base = (CONTEXT / 'actor_system.md').read_text().removesuffix('\n').format(skill_section='')
    require(base == (CONTEXT / 'actor_base_protocol.md').read_text().removesuffix('\n'),
            'Method Actor base differs from executable Actor')
    return base


def execution_context(config):
    background(config)
    text = (CONTEXT / 'actor_runtime.md').read_text().removesuffix('\n')
    return text.replace('49,152', f"{config['max_tokens']:,}")


def validate_case(case):
    nonempty_text(case.case_id, 'Task ID')
    fields(case.payload, ('question', 'context'), 'Case payload')
    nonempty_text(case.payload['question'], 'Question')
    nonempty_text(case.payload['context'], 'Context')
    validate_answers(case.reference)
    require(isinstance(case.metadata, dict) and case.metadata.get('split') in ('train', 'test'), 'Invalid case split')
    require(case.metadata.get('source_split') in ('train', 'val', 'test'), 'Invalid source split')
    require((case.metadata['split'] == 'test') == (case.metadata['source_split'] == 'test'), 'Source/effective split mismatch')
    return case


def public_task(case):
    validate_case(case)
    return {'id': case.case_id, 'split': case.metadata['split'], **deepcopy(case.payload)}


def messages(payload, skill):
    return list(build_messages(question=payload['question'], context=payload['context'], skill=skill))


def nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be non-empty text')
    return value


def validate_answers(answers):
    if not isinstance(answers, list) or not answers:
        raise ValueError('Gold answers must be a non-empty list')
    for answer in answers:
        nonempty_text(answer, 'Gold answer')
    return answers


def build_messages(*, question, context, skill):
    nonempty_text(question, 'Question')
    nonempty_text(context, 'Context')
    if skill is not None and not isinstance(skill, str):
        raise ValueError('Skill must be text or None')
    clean_skill = skill.strip() if skill else ''
    section = clean_skill + '\n\n' if clean_skill else ''
    # Remove only the template's terminal LF. Interpolation is single-pass;
    # braces and whitespace inside supplied task/Skill text remain literal.
    state = validation.current()
    def template(name):
        path = CONTEXT / name
        return (state.template(path) if state is not None else path.read_text()).removesuffix('\n')
    system = template('actor_system.md')
    user = template('actor_user.md')
    return (
        {'role': 'system', 'content': system.format(skill_section=section)},
        {'role': 'user', 'content': user.format(context=context, question=question)},
    )


def messages_for_row(row, skill):
    """Validate the reference before execution, but project only task text."""
    if not isinstance(row, dict):
        raise ValueError('Task row must be an object')
    nonempty_text(row.get('id'), 'Task ID')
    validate_answers(row.get('answers'))
    return build_messages(question=row.get('question'), context=row.get('context'), skill=skill)


def prompt_identity():
    return {'profile': PROMPT_PROFILE}
