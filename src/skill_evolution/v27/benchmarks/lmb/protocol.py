"""Frozen single-turn LMB protocol and strict JSON identities."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from skilladam.benchmarks.lmb.rollout import build_messages as upstream_messages
from ...facts import require, text

# Explicit prompt adaptation, following v23.5 action_only_v1. Upstream stays untouched.
PROMPT_PROFILE = 'lmb_answer_element_words_v2'
VENDOR_PROMPT = Path(__file__).with_name('context').joinpath('actor_base_protocol.md').read_text().replace(
    '## Task Format', '{skill_section}## Task Format', 1)


def build_messages(*, question, choices, method, skill):
    messages = list(upstream_messages(question=question, choices=choices, method=method, skill=skill))
    clean_skill = skill.strip() if isinstance(skill, str) else ''
    section = f'## Skill\n{clean_skill}\n\n' if clean_skill else ''
    messages[0] = {'role': 'system', 'content': VENDOR_PROMPT.format(skill_section=section)}
    return tuple(messages)


RECORD_VERSION = 'v27_lmb_execution_v1'
FACTS_VERSION = 'v27_lmb_facts_v1'
INPUT_VIEW = 'v27_lmb_pairs_content_v1'
MODEL_INPUT_VIEW = 'v27_lmb_content_input_v1'
EM_GATE = 'v27_lmb_em_v1'
FORMAL_CONTEXT = 'lmb_single_turn_v1'
CONTENT_REVISION = '6f53c5ff7227633ea954b2847cd590314d582047'
IDENTITY = {'name': 'LiveMathematicianBench', 'execution_profile': 'lmb_single_turn_length_retry_v3',
            'evidence_version': FACTS_VERSION}
ACTOR = {'transport': 'direct_http', 'endpoint': 'https://api.deepseek.com/chat/completions',
         'model': 'deepseek-flash', 'max_tokens': 49152, 'temperature': 1.0,
         'reasoning_effort': 'medium', 'thinking': {'type': 'enabled'},
         'timeout_seconds': 300, 'connect_timeout_seconds': 10, 'request_attempts_total': 6,
         'sdk_retries': 0, 'retry_delay_seconds': 1.0, 'retry_policy': 'technical_and_length_shared_six_v1'}
EXECUTION_CONFIG = {'max_model_rounds': 1, 'tools': [], 'request_attempts_total': 6,
                    'length': 'retry_unchanged_within_total_budget', 'answer_feedback_to_actor': False}


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def equal(left, right): return exact(left) == exact(right)

def digest(value): return hashlib.sha256(exact(value).encode()).hexdigest()

def file_digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), f'{label}: unexpected fields')


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f'Invalid {name}')
    return value


def score_view(metrics):
    fields(metrics, ('em','f1'), 'Scores')
    require(all(type(v) in (int,float) and v in (0,1) for v in metrics.values())
            and metrics['em'] == metrics['f1'], 'Invalid binary LMB scores')
    return deepcopy(metrics)


def validate_choices(choices):
    require(isinstance(choices,list) and len(choices)==5, 'LMB needs five choices')
    for label,choice in zip('ABCDE',choices):
        fields(choice, ('label','text'), 'Choice')
        require(choice['label']==label, 'Invalid choice order/label'); text(choice['text'],'choice text')
    return choices


def validate_task(task):
    fields(task, ('id','split','question','choices'), 'Task')
    text(task['id'],'task ID'); text(task['question'],'question'); validate_choices(task['choices'])
    require(task['split'] in ('train','validation','test'), 'Invalid split')
    return task


def public_task(case):
    return validate_task({'id':case.case_id,'split':case.metadata['split'],
                         'question':case.payload['question'],'choices':deepcopy(case.payload['choices'])})


def messages(task, skill):
    return list(build_messages(question=task['question'], choices=task['choices'], method='skilladam', skill=skill))


def background(actor):
    require(equal(actor,ACTOR), 'Actor differs from frozen Prompt runtime')
    return {'version':FACTS_VERSION, **deepcopy(ACTOR), **deepcopy(EXECUTION_CONFIG)}


def execution_context(value):
    require(equal(value,background(ACTOR)), 'Noncanonical LMB execution context')
    return Path(__file__).with_name('context').joinpath('actor_runtime.md').read_text().strip()
