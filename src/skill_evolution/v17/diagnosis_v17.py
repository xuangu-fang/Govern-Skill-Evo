"""One request per group, audited and strictly validated; no retries or repair."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

from .diagnosis_prompt_v17 import build_diagnosis_request
from .diagnosis_validation_v17 import DiagnosisRejected, validate_diagnosis_response
from ..v15.information_boundary_v15 import unpack

MODEL = 'deepseek-v4-pro'
TEMPERATURE = 0.0
REASONING_EFFORT = 'high'
MAX_COMPLETION_TOKENS = 24_000
TIMEOUT_SECONDS = 300


def _transport(prepared: dict) -> dict:
    from openai import OpenAI
    if not os.environ.get('OPENAI_API_KEY') or not os.environ.get('OPENAI_BASE_URL'):
        raise RuntimeError('Missing configured model connection')
    # Explicitly disable SDK retries as well as application retries.
    with OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'],
                max_retries=0, timeout=TIMEOUT_SECONDS) as client:
        response = client.chat.completions.create(
            model=prepared['model'], temperature=prepared['temperature'],
            reasoning_effort=prepared['reasoning_effort'],
            max_completion_tokens=prepared['max_completion_tokens'],
            messages=[{'role': 'system', 'content': prepared['system_prompt']},
                      {'role': 'user', 'content': prepared['user_prompt']}],
            response_format=prepared['response_format'],
        )
    choice = response.choices[0]
    return {'raw_response': choice.message.content, 'response_model': response.model,
            'response_id': response.id, 'finish_reason': choice.finish_reason,
            'refusal': getattr(choice.message, 'refusal', None),
            'usage': response.usage.model_dump() if response.usage else None}


def run_group_diagnosis(request, *, artifact_dir: Path, transport=None, experiment_scope: str = '') -> dict:
    """Persist before dispatch; rejected groups return REJECTED without an output.

    A fresh directory prevents accidental reruns/overwrites. VALID is a contract
    result, not a semantic correctness claim or Gate decision. Continue other
    independent groups at the campaign layer, never retry this group here.
    """
    prepared = {**build_diagnosis_request(request, experiment_scope=experiment_scope), 'model': MODEL,
                'temperature': TEMPERATURE, 'reasoning_effort': REASONING_EFFORT,
                'max_completion_tokens': MAX_COMPLETION_TOKENS,
                'timeout_seconds': TIMEOUT_SECONDS, 'max_retries': 0}
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                               allow_nan=False) + '\n', encoding='utf-8')

    save('request.json', prepared)
    save('provenance.json', request.provenance)
    save('validation.json', {'status': 'RUNNING', 'attempts': 1})
    started = time.monotonic()
    try:
        response = (transport or _transport)(prepared)
    except Exception as exc:
        result = {'status': 'REJECTED', 'stage': 'TRANSPORT',
                  'reason': type(exc).__name__, 'http_status': getattr(exc, 'status_code', None),
                  'attempts': 1, 'elapsed_seconds': time.monotonic() - started}
        save('validation.json', result)
        return result
    elapsed = time.monotonic() - started
    save('response.json', response)
    try:
        if response.get('refusal') or response.get('finish_reason') != 'stop':
            raise DiagnosisRejected('COMPLETION', 'refused or incomplete completion')
        envelope = validate_diagnosis_response(response.get('raw_response'), request=request)
    except DiagnosisRejected as exc:
        result = {'status': 'REJECTED', 'stage': exc.stage, 'reason': exc.reason,
                  'attempts': 1, 'elapsed_seconds': elapsed, 'usage': response.get('usage')}
        save('validation.json', result)
        return result
    validated = unpack(envelope, 'V17_VALIDATED_DIAGNOSIS')
    save('validated_diagnosis.json', validated)
    result = {'status': 'VALID', 'attempts': 1, 'elapsed_seconds': elapsed,
              'usage': response.get('usage'),
              'addressability': validated['semantic']['skill_addressability']['status'],
              'gap_count': len(validated['semantic']['parent_skill_gaps'])}
    save('validation.json', result)
    return result
