"""Local Diagnosis/Preconditioner calls, without Editor or environment execution."""

from copy import deepcopy
import json
from pathlib import Path
import time

from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import diagnosis, preconditioner, evolution
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.prompts import actor_fields, render_prompt


MODULES = {'diagnosis': diagnosis, 'preconditioner': preconditioner}
# Future development inherits V23. Archived experiments require explicit paths.
PROMPTS = {name: module.PROMPT_PATH for name, module in MODULES.items()}


def messages_for(name, saved, *, prompt_path=None, context_path=None):
    """Replace only the system template; V23 owns the complete input assembly."""
    messages = MODULES[name].messages_for(saved)
    template = PROMPTS[name] if prompt_path is None else Path(prompt_path)
    text = template.read_text()
    messages[0]['content'] = render_prompt(text, saved['background'])
    if context_path is not None:
        context = actor_fields(Path(context_path).read_text(), saved['background']).rstrip()
        messages[0]['content'] = text.replace('{{execution_context}}', context)
    return messages


def validate(name, value, saved):
    if name == 'diagnosis':
        diagnosis.validate_diagnosis(value, diagnosis.diagnosis_input(saved))
        return {**deepcopy(saved), 'diagnosis': value}
    effective = preconditioner.compile_effective_plan(value, preconditioner.preconditioner_input(saved))
    return {**deepcopy(saved), 'preconditioner': value, 'effective_plan': effective}


def load_attempt(directory, *, prompt_path=None, context_path=None):
    """Validate archives; pass historical prompt/context paths for experiments."""
    directory = Path(directory)
    meta = evolution.read(directory/'run.json')
    require(meta['version'] == 'V23.2' and meta['status'] == 'valid', 'Not a valid V23.2 attempt')
    saved = evolution.read(directory/'input.json')
    messages = messages_for(meta['module'], saved, prompt_path=prompt_path, context_path=context_path)
    require(evolution.read(directory/'messages.json') == messages, 'Saved messages differ')
    require((directory/'prompt.md').read_text() == messages[0]['content'], 'Saved Prompt differs')
    require(evolution.read(directory/'validation.json')['valid'] is True, 'Invalid saved validation')
    response = evolution.read(directory/'response.json')
    require(response.get('finish_reason') == 'stop', 'Incomplete response')
    value = parse_json_response(response['content'])
    require(value == evolution.read(directory/'parsed.json') == evolution.read(directory/f"{meta['module']}.json"),
            'Saved output differs from raw response')
    result = validate(meta['module'], value, saved)
    if meta['module'] == 'preconditioner':
        require(result['effective_plan'] == evolution.read(directory/'effective_plan.json'), 'Compiled Plan differs')
    return result


def run_stage(name, saved, directory, config, *, generate=None, prompt_path=None, context_path=None):
    """One logical call, at most the existing V23 technical-attempt budget.

    A legal semantic result always ends the stage. Existing directories are never
    rerun; interrupted calls require investigation, not another sampling budget.
    """
    require(name in MODULES and config['max_attempts'] == 3, 'Unsupported stage or retry budget')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    if generate is None:
        config = evolution.configuration_from_environment(config)
    messages = messages_for(name, saved, prompt_path=prompt_path, context_path=context_path)
    encoded = json.dumps(messages, ensure_ascii=False)
    cfg = config.get('stage_configs', {}).get(name, config['call_config'])
    limits = {'input_chars': len(encoded), 'input_utf8_bytes': len(encoded.encode('utf-8')),
              'max_input_chars': config['max_input_chars'],
              'max_message_utf8_bytes': evolution.message_byte_limit(config)}
    evolution.save(directory/'capacity.json', limits)
    if limits['input_chars'] > limits['max_input_chars'] or limits['input_utf8_bytes'] > limits['max_message_utf8_bytes']:
        evolution.save(directory/'stop.json', {'kind': 'capacity', 'requests': 0, **limits})
        raise evolution.Stopped('Input exceeds inherited capacity; no request or compression')
    if generate is None:
        generate = evolution._generator({**config, 'call_config': cfg})
    require(getattr(generate, 'call_config', cfg) == cfg, 'Generator configuration differs')
    for number in range(1, config['max_attempts'] + 1):
        attempt = directory/'attempts'/f'{number:03}'
        attempt.mkdir(parents=True)
        evolution.save(attempt/'input.json', saved)
        evolution.save(attempt/'messages.json', messages)
        (attempt/'prompt.md').write_text(messages[0]['content'])
        meta = {'version': 'V23.2', 'module': name, 'started_at': evolution.now(),
                'call_config': cfg, 'status': 'requesting', **limits}
        evolution.save(attempt/'run.json', meta)
        started = time.monotonic()
        try:
            response = generate(messages, attempt)
            evolution.save(attempt/'response.json', response)
            (attempt/'raw_output.txt').write_text(response.get('content') or '')
            require(response.get('finish_reason') == 'stop', 'Model response did not finish normally')
            value = parse_json_response(response['content'])
            evolution.save(attempt/'parsed.json', value)
            result = validate(name, value, saved)
            evolution.save(attempt/f'{name}.json', value)
            if name == 'preconditioner':
                evolution.save(attempt/'effective_plan.json', result['effective_plan'])
            evolution.save(attempt/'validation.json', {'valid': True, 'error': None})
            meta['status'] = 'valid'
        except Exception as exc:
            retry = evolution._retryable(exc, attempt)
            error = {'type': type(exc).__name__, 'error': str(exc), 'retryable': retry}
            evolution.save(attempt/'error.json', error)
            evolution.save(attempt/'validation.json', {'valid': False, **error})
            meta['status'] = 'invalid'
            if not retry or number == config['max_attempts']:
                evolution.save(directory/'stop.json', {'kind': 'technical', 'attempt': number, **error})
                raise evolution.Stopped(f'{name}: {type(exc).__name__}: {exc}') from exc
        finally:
            meta.update(finished_at=evolution.now(), elapsed_seconds=time.monotonic()-started)
            evolution.save(attempt/'run.json', meta)
        if meta['status'] == 'valid':
            loaded = load_attempt(attempt, prompt_path=prompt_path, context_path=context_path)
            evolution.save(directory/'result.json', {'path': str(attempt.relative_to(directory)),
                                                    'decision': value['decision']})
            return loaded
        time.sleep(config.get('retry_delay_seconds', 0) * number)
