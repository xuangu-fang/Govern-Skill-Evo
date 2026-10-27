"""V23.4 Replay prompt and archive boundary; shared paired facts and Memory schema."""
from datetime import datetime, timezone
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import replay as original
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.memory import validate_entries, LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v23.prompts import render_prompt, execution_context
from src.skill_evolution.v23_3.memory_view import FORMAT_PATH as MEMORY_FORMAT_PATH, MULTI_FORMAT_PATH
from .editor import load_editor
from .replay_view import (FORMAT as INPUT_VIEW, LEGACY as LEGACY_INPUT_VIEW,
                          FORMAT_PATH as VIEW_FORMAT_PATH, model_input, history_pair_sources)

PROMPT_VERSION = "v23_4_replay_v1"
PROMPT_PATH = Path(__file__).with_name("replay_prompt.md")
# P3 schema-only adapter; P4's learning prompt gets its own version.
MULTI_PROMPT_VERSION = "v23_4_replay_multi_knowledge_contract_v1"
MULTI_PROMPT_PATH = Path(__file__).with_name("replay_multi_knowledge_contract_prompt.md")
MULTI_VIEW_PATH = Path(__file__).with_name("replay_multi_knowledge_view_prompt.md")
LEARNING_PROMPT_VERSION = "v23_4_replay_multi_knowledge_v1"
LEARNING_PROMPT_PATH = Path(__file__).with_name("replay_multi_knowledge_learning_prompt_v1.md")


def _prompt(memory_contract, prompt_version=None):
    require(memory_contract in (LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT), "Unsupported Memory contract")
    if prompt_version is None:
        prompt_version = PROMPT_VERSION if memory_contract == LEGACY_CONTRACT else MULTI_PROMPT_VERSION
    registry = {
        PROMPT_VERSION: (LEGACY_CONTRACT, PROMPT_PATH),
        MULTI_PROMPT_VERSION: (MULTI_KNOWLEDGE_CONTRACT, MULTI_PROMPT_PATH),
        LEARNING_PROMPT_VERSION: (MULTI_KNOWLEDGE_CONTRACT, LEARNING_PROMPT_PATH),
    }
    require(isinstance(prompt_version, str) and prompt_version in registry, 'Unsupported Replay prompt version')
    contract, path = registry[prompt_version]
    require(contract == memory_contract, 'Replay prompt/Memory contract mismatch')
    return prompt_version, path


def build_replay(editor_directory, parent_records, candidate_records, *, memory=None, implementation_review=None,
                 memory_contract=LEGACY_CONTRACT):
    return original.build_replay_from_editor(
        load_editor(editor_directory), editor_directory, parent_records, candidate_records,
        memory=memory, implementation_review=implementation_review, memory_contract=memory_contract)


def validate_bundle(bundle, *, memory_contract=LEGACY_CONTRACT):
    """Recheck versioned lineage; behavioral truth still comes from supplied records."""
    original.validate_payload(bundle['payload'], memory_contract=memory_contract)
    saved = load_editor(bundle['editor_directory'])
    payload = bundle['payload']
    require(saved['editor_status'] == 'candidate', 'Replay requires a Candidate')
    require(bundle['candidate'] == saved['candidate_text'] and payload['diff'] == saved['actual_diff'],
            'Replay actual edit differs from Editor')
    require(payload['parent'] == saved['facts']['parent'] and bundle['background'] == saved['background'],
            'Replay Parent/background differs from Editor')
    plan = saved['effective_plan']
    expected = {'goal': plan['goal'], 'updates': [{k: u[k] for k in ('id', 'text')} for u in plan['updates']],
                'checks': plan['checks']}
    require(payload['plan'] == expected, 'Replay Plan differs from Editor')
    parents = [r for r in payload['runs'] if r['ref'].startswith('P')]
    require(parents == saved['facts']['runs'], 'Replay Parent executions differ from frozen lineage')
    require(all(payload['command_sets'].get(cid) == commands
                for cid, commands in saved['facts']['command_sets'].items()), 'Parent command sources differ')
    require(bundle['execution_context']['background'] == saved['background'], 'Replay execution context differs')
    return bundle


def messages_for(bundle, *, input_view=INPUT_VIEW, history_sources=None, memory_contract=LEGACY_CONTRACT,
                 prompt_version=None):
    original.validate_payload(bundle['payload'], memory_contract=memory_contract)
    require(input_view in (INPUT_VIEW, LEGACY_INPUT_VIEW), 'Unsupported Replay input view')
    version, path = _prompt(memory_contract, prompt_version)
    if version == LEARNING_PROMPT_VERSION:
        require(input_view == INPUT_VIEW, 'Learning Prompt requires the paired Replay input view')
        template = path.read_text()
        require('{{' not in template and '}}' not in template, 'Learning Prompt must not embed context placeholders')
        system = template.rstrip() + '\n\n' + execution_context(bundle['background'])
    else:
        system = render_prompt(path.read_text(), bundle['background'])
    if input_view == INPUT_VIEW:
        payload = model_input(bundle, history_sources=history_sources, memory_contract=memory_contract)
        view_path = VIEW_FORMAT_PATH if memory_contract == LEGACY_CONTRACT else MULTI_VIEW_PATH
        system += '\n\n' + MEMORY_FORMAT_PATH.read_text() + '\n\n' + view_path.read_text()
    else:
        require(not history_sources, 'Legacy Replay has no pairing provenance extension')
        payload = bundle['payload']
    if memory_contract == MULTI_KNOWLEDGE_CONTRACT:
        system += '\n\n' + MULTI_FORMAT_PATH.read_text()
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]


def load_replay(directory, *, expected_bundle=None, expected_call_config=...,
                expected_input_view=..., expected_history_sources=..., expected_memory_contract=...,
                expected_prompt_version=...):
    directory = Path(directory)
    read = lambda name: json.loads((directory/name).read_text())
    meta = read('run.json')
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
                            memory_contract=memory_contract, prompt_version=version)
    if 'input_view' in meta:
        require(read('model_input.json') == json.loads(messages[1]['content']), 'Replay model view differs')
    require(read('messages.json') == messages and (directory/'prompt.md').read_text() == messages[0]['content'],
            'Replay prompt differs')
    if expected_call_config is not ...:
        require(meta['call_config'] == expected_call_config, 'Replay configuration differs')
    require(meta['status'] == 'valid' and read('validation.json')['valid'] is True, 'Replay is not valid')
    response = read('response.json')
    require(response.get('finish_reason') == 'stop', 'Replay did not finish normally')
    require((directory/'raw_output.txt').read_text() == response['content'], 'Replay raw output differs')
    result = validate_entries(parse_json_response(response['content']), bundle['payload'], memory_contract=memory_contract)
    require(result == read('parsed.json') == read('replay.json'), 'Replay result differs from response')
    return {**bundle, 'replay': result}


def run_replay(bundle, directory, *, generate, call_config=None, max_input_chars=400000,
               input_view=INPUT_VIEW, history_sources=None, memory_contract=LEGACY_CONTRACT, prompt_version=None):
    validate_bundle(bundle, memory_contract=memory_contract)
    sources = {} if history_sources is None else history_sources
    version, _ = _prompt(memory_contract, prompt_version)
    messages = messages_for(bundle, input_view=input_view, history_sources=sources,
                            memory_contract=memory_contract, prompt_version=version)
    config = getattr(generate, 'call_config', None)
    require(call_config is None or config is None or call_config == config, 'Generator configuration differs')
    config = call_config if call_config is not None else config
    directory = Path(directory)
    if directory.exists():
        return load_replay(directory, expected_bundle=bundle, expected_call_config=config,
                           expected_input_view=input_view, expected_history_sources=sources,
                           expected_memory_contract=memory_contract, expected_prompt_version=version)
    directory.mkdir(parents=True, exist_ok=False)
    write_record(directory/'input.json', bundle)
    write_record(directory/'history_pair_sources.json', sources)
    write_record(directory/'model_input.json', json.loads(messages[1]['content']))
    write_record(directory/'messages.json', messages)
    (directory/'prompt.md').write_text(messages[0]['content'])
    meta = {'prompt_version': version, 'input_view': input_view,
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
        (directory/'raw_output.txt').write_text(response.get('content') or '')
        require(response.get('finish_reason') == 'stop', 'Model response did not finish normally')
        parsed = parse_json_response(response['content'])
        write_record(directory/'parsed.json', parsed)
        validate_entries(parsed, bundle['payload'], memory_contract=memory_contract)
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
