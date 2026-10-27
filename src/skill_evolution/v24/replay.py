from src.skill_evolution.v24.benchmark import current as benchmark_current
from src.skill_evolution.v24.resources import resource
"""V23.5 Replay with explicitly paired, versioned history views and prompts."""
from datetime import datetime, timezone
from . import output_feedback as feedback
import json
from pathlib import Path

from src.skill_evolution.v24.storage import write_record
from src.skill_evolution.v24.json_response import parse_json_response
from src.skill_evolution.v24.contracts import replay as original
from src.skill_evolution.v24.contracts.editor import _read_text, _write_text
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import validate_entries, run_references, LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v24.prompts import render_prompt, execution_context
from src.skill_evolution.v24.contracts.memory_view import FORMAT_PATH as MEMORY_FORMAT_PATH, MULTI_FORMAT_PATH
from .editor import load_editor
from .memory_view import (knowledge_only, historical_references, check_historical_prose,
                          PROMPT_PATH as KNOWLEDGE_VIEW_PATH)
from .replay_view import FORMAT as KNOWLEDGE_INPUT_VIEW, model_input as knowledge_model_input
from src.skill_evolution.v24.contracts.replay_view import FORMAT as INPUT_VIEW, LEGACY as LEGACY_INPUT_VIEW, FORMAT_PATH as VIEW_FORMAT_PATH, model_input

ADAPTER_VERSION = "v23_5_replay_boundary_v1"

PROMPT_VERSION = "v23_4_replay_v1"
PROMPT_PATH = resource("v23_4/replay_prompt.md")
# P3 schema-only adapter; P4's learning prompt gets its own version.
MULTI_PROMPT_VERSION = "v23_4_replay_multi_knowledge_contract_v1"
MULTI_PROMPT_PATH = resource("v23_4/replay_multi_knowledge_contract_prompt.md")
MULTI_VIEW_PATH = resource("v23_4/replay_multi_knowledge_view_prompt.md")
LEARNING_PROMPT_VERSION = "v23_4_replay_multi_knowledge_v1"
LEARNING_PROMPT_PATH = resource("v23_4/replay_multi_knowledge_learning_prompt_v1.md")

KNOWLEDGE_PROMPT_VERSION = "v23_5_replay_knowledge_only_v1"
KNOWLEDGE_PROMPT_PATH = resource("v23_5/replay_knowledge_only_prompt.md")


def _prompt(memory_contract, prompt_version=None):
    require(memory_contract in (LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT), "Unsupported Memory contract")
    if prompt_version is None:
        prompt_version = LEARNING_PROMPT_VERSION
    registry = {
        PROMPT_VERSION: (LEGACY_CONTRACT, PROMPT_PATH),
        MULTI_PROMPT_VERSION: (MULTI_KNOWLEDGE_CONTRACT, MULTI_PROMPT_PATH),
        LEARNING_PROMPT_VERSION: (MULTI_KNOWLEDGE_CONTRACT, LEARNING_PROMPT_PATH),
        KNOWLEDGE_PROMPT_VERSION: (MULTI_KNOWLEDGE_CONTRACT, KNOWLEDGE_PROMPT_PATH),
    }
    require(isinstance(prompt_version, str) and prompt_version in registry, 'Unsupported Replay prompt version')
    contract, path = registry[prompt_version]
    require(contract == memory_contract, 'Replay prompt/Memory contract mismatch')
    return prompt_version, path


def _view_prompt(input_view, memory_contract, prompt_version):
    require(input_view in (INPUT_VIEW, LEGACY_INPUT_VIEW, KNOWLEDGE_INPUT_VIEW),
            'Unsupported Replay input view')
    if prompt_version is None and input_view == KNOWLEDGE_INPUT_VIEW:
        prompt_version = KNOWLEDGE_PROMPT_VERSION
    version, path = _prompt(memory_contract, prompt_version)
    require((input_view == KNOWLEDGE_INPUT_VIEW) == (version == KNOWLEDGE_PROMPT_VERSION),
            'Replay Knowledge Only view/prompt mismatch')
    return version, path


def validate_result(result, payload, *, input_view=KNOWLEDGE_INPUT_VIEW, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    # Full archive validation checks existence and the unchanged output schema first.
    if input_view == KNOWLEDGE_INPUT_VIEW:
        require(memory_contract == MULTI_KNOWLEDGE_CONTRACT, 'Knowledge Only Replay requires multi-Knowledge output')
    validate_entries(result, payload, memory_contract=memory_contract)
    require(input_view in (INPUT_VIEW, LEGACY_INPUT_VIEW, KNOWLEDGE_INPUT_VIEW),
            'Unsupported Replay input view')
    if input_view == KNOWLEDGE_INPUT_VIEW:
        view = knowledge_only(payload['memory'], memory_contract=memory_contract)
        allowed = historical_references(view)
        current = {ref for run in payload['runs'] for ref in run_references(run)}
        contexts = {ref.rsplit('/', 1)[0] for ref in payload['memory']['sources']}
        for entry_index, entry in enumerate(result['entries']):
            for item_index, item in enumerate(entry['knowledge']):
                history = {ref for ref in item['evidence'] if '/' in ref}
                require(history <= allowed, 'Unavailable historical reference in Knowledge evidence')
                check_historical_prose(item['text'], allowed, current=current, historical_contexts=contexts,
                                       location=f'entries[{entry_index}].knowledge[{item_index}].text')
    return result


def build_replay(editor_directory, parent_records, candidate_records, *, memory=None, implementation_review=None,
                 memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    return original.build_replay_from_editor(
        load_editor(editor_directory), editor_directory, parent_records, candidate_records,
        memory=memory, implementation_review=implementation_review, memory_contract=memory_contract)


def validate_bundle(*args, **kwargs):
    return benchmark_current().evidence("replay.validate_bundle", *args, **kwargs)


def messages_for(bundle, *, input_view=KNOWLEDGE_INPUT_VIEW, history_sources=None, memory_contract=MULTI_KNOWLEDGE_CONTRACT,
                 prompt_version=None, retry_policy=feedback.LEGACY):
    original.validate_payload(bundle['payload'], memory_contract=memory_contract)
    version, path = _view_prompt(input_view, memory_contract, prompt_version)
    if version in (LEARNING_PROMPT_VERSION, KNOWLEDGE_PROMPT_VERSION):
        require(input_view in (INPUT_VIEW, KNOWLEDGE_INPUT_VIEW), 'Learning Prompt requires the paired Replay input view')
        template = feedback.prompt_text(path, retry_policy)
        require('{{' not in template and '}}' not in template, 'Learning Prompt must not embed context placeholders')
        system = template.rstrip() + '\n\n' + execution_context(bundle['background'])
    else:
        system = render_prompt(feedback.prompt_text(path, retry_policy), bundle['background'])
    if input_view == KNOWLEDGE_INPUT_VIEW:
        require(not history_sources, 'Knowledge Only does not accept historical pairing sources')
        payload = knowledge_model_input(bundle, memory_contract=memory_contract)
        system += '\n\n' + KNOWLEDGE_VIEW_PATH.read_text()
    elif input_view == INPUT_VIEW:
        payload = model_input(bundle, history_sources=history_sources, memory_contract=memory_contract)
        view_path = VIEW_FORMAT_PATH if memory_contract == LEGACY_CONTRACT else MULTI_VIEW_PATH
        system += '\n\n' + MEMORY_FORMAT_PATH.read_text() + '\n\n' + view_path.read_text()
    else:
        require(not history_sources, 'Legacy Replay has no pairing provenance extension')
        payload = bundle['payload']
    if memory_contract == MULTI_KNOWLEDGE_CONTRACT and input_view != KNOWLEDGE_INPUT_VIEW:
        system += '\n\n' + MULTI_FORMAT_PATH.read_text()
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]


def load_replay(directory, *, expected_bundle=None, expected_call_config=...,
                expected_input_view=..., expected_history_sources=..., expected_memory_contract=...,
                expected_prompt_version=...):
    directory = Path(directory)
    request_context = feedback.saved_context(directory)
    read = lambda name: json.loads((directory/name).read_text())
    meta = read('run.json')
    require(meta.get('adapter_version') == ADAPTER_VERSION, 'Unsupported Replay boundary')
    memory_contract = meta.get('memory_contract', LEGACY_CONTRACT)
    require(isinstance(meta.get('prompt_version'), str), 'Missing Replay prompt version')
    version, _ = _prompt(memory_contract, meta['prompt_version'])
    if expected_prompt_version is not ...:
        require(version == expected_prompt_version, 'Replay prompt version differs')
    if expected_memory_contract is not ...:
        require(memory_contract == expected_memory_contract, 'Replay Memory contract differs')
    bundle = validate_bundle(read('input.json'), memory_contract=memory_contract)
    if expected_bundle is not None:
        require(bundle == expected_bundle, 'Replay input/source differs')
    input_view = meta.get('input_view', LEGACY_INPUT_VIEW)
    if expected_input_view is not ...:
        require(input_view == expected_input_view, 'Replay input view differs')
    sources = read('history_pair_sources.json') if 'input_view' in meta else {}
    if expected_history_sources is not ...:
        require(sources == expected_history_sources, 'Historical pairing provenance differs')
    messages = messages_for(bundle, input_view=input_view, history_sources=sources,
                            memory_contract=memory_contract, prompt_version=version,
                            retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
    if 'input_view' in meta:
        require(read('model_input.json') == json.loads(messages[1]['content']), 'Replay model view differs')
    require(read('messages.json') == messages and _read_text(directory/'prompt.md') == messages[0]['content'],
            'Replay prompt differs')
    if expected_call_config is not ...:
        require(meta['call_config'] == expected_call_config, 'Replay configuration differs')
    require(meta['status'] == 'valid' and read('validation.json')['valid'] is True, 'Replay is not valid')
    response = read('response.json')
    require(response.get('finish_reason') == 'stop', 'Replay did not finish normally')
    require(_read_text(directory/'raw_output.txt') == response['content'], 'Replay raw output differs')
    result = validate_result(parse_json_response(response['content']), bundle['payload'],
                             input_view=input_view, memory_contract=memory_contract)
    require(result == read('parsed.json') == read('replay.json'), 'Replay result differs from response')
    return {**bundle, 'replay': result}


def run_replay(bundle, directory, *, generate, call_config=None, max_input_chars=400000,
               input_view=KNOWLEDGE_INPUT_VIEW, history_sources=None, memory_contract=MULTI_KNOWLEDGE_CONTRACT, prompt_version=None):
    request_context = (feedback.saved_context(directory) if Path(directory).exists()
                       else feedback.generation_context(generate))
    validate_bundle(bundle, memory_contract=memory_contract)
    sources = {} if history_sources is None else history_sources
    version, _ = _view_prompt(input_view, memory_contract, prompt_version)
    messages = messages_for(bundle, input_view=input_view, history_sources=sources,
                            memory_contract=memory_contract, prompt_version=version,
                            retry_policy=feedback.policy(request_context))
    messages = feedback.request_messages(messages, request_context)
    config = getattr(generate, 'call_config', None)
    require(call_config is None or config is None or call_config == config, 'Generator configuration differs')
    config = call_config if call_config is not None else config
    directory = Path(directory)
    if directory.exists():
        return load_replay(directory, expected_bundle=bundle, expected_call_config=config,
                           expected_input_view=input_view, expected_history_sources=sources,
                           expected_memory_contract=memory_contract, expected_prompt_version=version)
    directory.mkdir(parents=True, exist_ok=False)
    feedback.save_context(directory, request_context)
    write_record(directory/'input.json', bundle)
    write_record(directory/'history_pair_sources.json', sources)
    write_record(directory/'model_input.json', json.loads(messages[1]['content']))
    write_record(directory/'messages.json', messages)
    _write_text(directory/'prompt.md', messages[0]['content'])
    meta = {'adapter_version': ADAPTER_VERSION, 'prompt_version': version, 'input_view': input_view,
            'started_at': datetime.now(timezone.utc).isoformat(), 'call_config': config,
            'input_chars': len(json.dumps(messages, ensure_ascii=False)), 'max_input_chars': max_input_chars,
            'status': 'requesting'}
    if memory_contract == MULTI_KNOWLEDGE_CONTRACT:
        meta['memory_contract'] = memory_contract
    write_record(directory/'run.json', meta)
    try:
        require(meta['input_chars'] <= max_input_chars, 'Replay input exceeds frozen budget')
        response = generate(messages, directory)
        write_record(directory/'response.json', response)
        _write_text(directory/'raw_output.txt', response.get('content') or '')
        require(response.get('finish_reason') == 'stop', 'Model response did not finish normally')
        parsed = feedback.output_call('response', parse_json_response, response['content'])
        write_record(directory/'parsed.json', parsed)
        feedback.output_call('Replay output', validate_result, parsed, bundle['payload'], input_view=input_view, memory_contract=memory_contract)
        meta['output_validated'] = True
        write_record(directory/'replay.json', parsed)
        write_record(directory/'validation.json', {'valid': True, 'error': None})
        meta['status'] = 'valid'
    except (Exception, KeyboardInterrupt) as exc:
        write_record(directory/'validation.json', {'valid': False, 'error_type': type(exc).__name__,
            'error': str(exc) if isinstance(exc, ValueError) else 'Call failed; inspect raw response.'})
        meta['status'] = 'invalid'
        raise
    finally:
        meta['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_record(directory/'run.json', meta)
    return load_replay(directory, expected_bundle=bundle, expected_call_config=config,
                       expected_input_view=input_view, expected_history_sources=sources,
                       expected_memory_contract=memory_contract, expected_prompt_version=version)
