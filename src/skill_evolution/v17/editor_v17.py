"""One-shot audited Editor runner; no retries, repair or Parent overwrite."""
import hashlib
import json
import os
from pathlib import Path
import time

from .editor_prompt_v17 import build_editor_request
from .editor_apply_v17 import apply_editor_response
from .editor_contract_v17 import EditorRejected
from .compiler_validation_v17 import plan_payload

MODEL = 'deepseek-v4-pro'
TEMPERATURE = 0.0
REASONING_EFFORT = 'high'
MAX_COMPLETION_TOKENS = 24_000
TIMEOUT_SECONDS = 300


def _transport(prepared):
    from openai import OpenAI
    if not os.environ.get('OPENAI_API_KEY') or not os.environ.get('OPENAI_BASE_URL'):
        raise RuntimeError('Missing configured model connection')
    with OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'],
                max_retries=0, timeout=TIMEOUT_SECONDS) as client:
        response = client.chat.completions.create(
            model=prepared['model'], temperature=prepared['temperature'],
            reasoning_effort=prepared['reasoning_effort'],
            max_completion_tokens=prepared['max_completion_tokens'],
            messages=[{'role': 'system', 'content': prepared['system_prompt']},
                      {'role': 'user', 'content': prepared['user_prompt']}],
            response_format=prepared['response_format'])
    choice = response.choices[0]
    return {'raw_response': choice.message.content, 'response_model': response.model,
            'response_id': response.id, 'finish_reason': choice.finish_reason,
            'refusal': getattr(choice.message, 'refusal', None),
            'usage': response.usage.model_dump() if response.usage else None}


def run_editor(value, *, artifact_dir: Path, transport=None):
    """VALID is an applied candidate, not Gate acceptance.

    Only a terminal validation.json marks completion. Filesystem errors propagate;
    incomplete directories must not be consumed. Existing directories are refused.
    """
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def save_bytes(name, content):
        temporary = directory / (name + '.tmp')
        temporary.write_bytes(content)
        temporary.replace(directory / name)
        hashes[name] = hashlib.sha256(content).hexdigest()

    def save(name, data):
        save_bytes(name, (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                                    allow_nan=False) + '\n').encode('utf-8'))

    def finish(result):
        result = {**result, 'artifact_sha256': {k: v for k, v in hashes.items() if k != 'validation.json'}}
        save('validation.json', result)
        return result

    save('validation.json', {'status': 'RUNNING', 'model_calls': 0})
    try:
        prepared = build_editor_request(value)
    except EditorRejected as exc:
        return finish({'status': 'REJECTED', 'stage': exc.stage, 'reason': exc.reason, 'model_calls': 0})
    save_bytes('parent_skill.md', value.compiler_input.parent_skill.encode('utf-8'))
    save('edit_plan.json', plan_payload(value.plan))
    if prepared is None:
        return finish({'status': 'NO_UPDATE', 'model_calls': 0})
    prepared = {**prepared, 'model': MODEL, 'temperature': TEMPERATURE,
                'reasoning_effort': REASONING_EFFORT,
                'max_completion_tokens': MAX_COMPLETION_TOKENS,
                'timeout_seconds': TIMEOUT_SECONDS, 'max_retries': 0}
    save('request.json', prepared)
    started = time.monotonic()
    try:
        response = (transport or _transport)(prepared)
    except Exception as exc:
        return finish({'status': 'REJECTED', 'stage': 'TRANSPORT',
                       'reason': type(exc).__name__, 'http_status': getattr(exc, 'status_code', None),
                       'model_calls': 1, 'elapsed_seconds': time.monotonic() - started})
    elapsed = time.monotonic() - started
    save('response.json', response)
    common = {'model_calls': 1, 'elapsed_seconds': elapsed, 'usage': response.get('usage')}
    try:
        if response.get('refusal') or response.get('finish_reason') != 'stop':
            raise EditorRejected('COMPLETION', 'refused or incomplete completion')
        applied = apply_editor_response(response.get('raw_response'), editor_input=value)
    except EditorRejected as exc:
        return finish({**common, 'status': 'REJECTED', 'stage': exc.stage, 'reason': exc.reason})
    save('edits.json', applied['output'])
    if applied['status'] == 'UNABLE':
        return finish({**common, 'status': 'UNABLE', 'reason': applied['output']['reason']})
    save_bytes('candidate_skill.md', applied['candidate_skill'].encode('utf-8'))
    return finish({**common, 'status': 'VALID', 'parent_skill_digest': applied['parent_skill_digest'],
                   'plan_sha256': applied['plan_sha256'], 'candidate_sha256': applied['candidate_sha256']})
