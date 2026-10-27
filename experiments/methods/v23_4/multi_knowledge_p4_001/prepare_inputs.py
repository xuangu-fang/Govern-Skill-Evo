"""Offline P4 candidate assembly and integrity checks. No generator or network calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
BASELINE = HERE.with_name('replay_prompt_candidate_001')
from experiments.methods.v23_4.archive_io import archive_glob, resolve
from src.skill_evolution.v23 import memory, editor as base_editor, replay as base_replay
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23_4 import replay
from src.skill_evolution.v23.prompts import execution_context

NEW = memory.MULTI_KNOWLEDGE_CONTRACT


def read(path):
    return json.loads(resolve(path).read_text())


def sha(path):
    return hashlib.sha256(resolve(path).read_bytes()).hexdigest()


def save(path, value):
    path = resolve(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    if path.exists():
        assert path.read_bytes() == encoded, f'Frozen artifact differs: {path}'
    else:
        path.write_bytes(encoded)


def verify_experiment_editor(bundle):
    """The frozen evaluations use their original attempt archive, not production run.json."""
    attempt = Path(bundle['editor_directory'])
    material_path = attempt.parents[2] / 'config/material.json'
    material = read(material_path)
    response = read(attempt / 'response.json')
    assert response['finish_reason'] == 'stop'
    parsed = parse_json_response(response['content'])
    assert parsed == read(attempt / 'parsed.json')
    status, candidate = base_editor.validate_editor(parsed, material['parent'])
    diff = base_editor.actual_diff(material['parent'], candidate)
    result = {'editor': parsed, 'editor_status': status, 'candidate_text': candidate, 'actual_diff': diff}
    assert status == 'candidate' and result == read(attempt / 'result.json')
    assert candidate == bundle['candidate'] == (attempt / 'candidate.md').read_text()
    assert diff == bundle['payload']['diff'] == (attempt / 'actual.diff').read_text()
    assert material['parent'] == bundle['payload']['parent'] and material['background'] == bundle['background']
    expected_plan = {'goal': material['plan']['goal'], 'checks': material['plan']['checks'],
                     'updates': [{k: u[k] for k in ('id', 'text')} for u in material['plan']['updates']]}
    assert expected_plan == bundle['payload']['plan']
    base_replay.validate_payload(bundle['payload'], memory_contract=NEW)
    return [material_path, *[attempt / name for name in
        ('response.json', 'parsed.json', 'result.json', 'candidate.md', 'actual.diff')]]


def prepare():
    baseline = read(BASELINE / 'config/freeze.json')
    assert replay.LEARNING_PROMPT_PATH.read_bytes() == (HERE / 'candidate_prompt.md').read_bytes()
    checks = {}
    sources_to_freeze = [BASELINE / 'config/freeze.json', HERE / 'original_prompt.md', HERE / 'candidate_prompt.md',
                         HERE / 'prompt_changes.diff', Path(__file__), replay.LEARNING_PROMPT_PATH,
                         replay.PROMPT_PATH, replay.MULTI_PROMPT_PATH, replay.MULTI_VIEW_PATH,
                         replay.MEMORY_FORMAT_PATH, replay.MULTI_FORMAT_PATH]
    sources_to_freeze += [ROOT / f'src/skill_evolution/{name}' for name in (
        'v23_4/replay.py', 'v23_4/replay_view.py', 'v23_4/preconditioner.py', 'v23_4/update_patch.py',
        'v23_4/editor.py', 'v23/editor.py', 'v23/memory.py', 'v23/replay.py', 'v23/preconditioner.py',
        'v23/prompts.py', 'v23/execution_context.md', 'v23_3/memory_view.py')]
    for case, historical_round in [('R05', 'R04'), ('R06', 'R05')]:
        old_root = BASELINE / 'config' / case
        old = read(old_root / 'replay_bundle.json')
        old_sources = read(old_root / 'history_pair_sources.json')
        original_memory = ROOT / f'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/{historical_round}/memory'
        assert memory.load_memory(original_memory) == old['payload']['memory']
        bundle = deepcopy(old)
        bundle['payload']['memory'] = memory.load_memory(original_memory, memory_contract=NEW)
        assert bundle['payload']['memory'] == memory.normalize_memory(old['payload']['memory'], source_contract=memory.LEGACY_CONTRACT)
        sources_to_freeze += verify_experiment_editor(bundle)
        sources = replay.history_pair_sources(original_memory, bundle['payload']['memory'], memory_contract=NEW)
        assert sources == old_sources
        messages = replay.messages_for(bundle, memory_contract=NEW, prompt_version=replay.LEARNING_PROMPT_VERSION,
                                       history_sources=sources)
        p3 = replay.messages_for(bundle, memory_contract=NEW, prompt_version=replay.MULTI_PROMPT_VERSION,
                                 history_sources=sources)
        assert messages[1] == p3[1]
        model_input = json.loads(messages[1]['content'])
        expected = read(old_root / 'model_input.json')
        expected['memory']['entries'] = bundle['payload']['memory']['entries']
        assert model_input == expected
        unchanged = deepcopy(bundle); unchanged['payload']['memory'] = old['payload']['memory']
        assert unchanged == old
        system = messages[0]['content']
        headings = ['## Execution Context', '## Historical Memory evidence view v3',
                    '## Replay paired-input view v1', '## Multi-Knowledge Memory representation v1']
        assert all(system.count(h) == 1 for h in headings)
        assert system.count(execution_context(bundle['background'])) == 1
        chars = len(json.dumps(messages, ensure_ascii=False))
        assert chars <= baseline['max_input_chars']
        out = HERE / 'cases' / case
        save(out / 'replay_bundle.json', bundle)
        save(out / 'model_input.json', model_input)
        save(out / 'history_pair_sources.json', sources)
        save(out / 'messages.json', messages)
        save(out / 'call_config.json', baseline['call_config'])
        prompt_path = out / 'system_prompt.md'
        if prompt_path.exists(): assert prompt_path.read_bytes() == system.encode()
        else: prompt_path.write_bytes(system.encode())
        checks[case] = {'full_facts_unchanged': True, 'original_memory_normalization_exact': True,
            'user_view_only_entry_representation_changed_vs_single_knowledge': True,
            'user_message_identical_to_p3': True, 'historical_pairs_and_sources_unchanged': True,
            'experiment_editor_patch_and_plan_verified': True,
            'production_editor_lineage_loader_applicable': False, 'context_and_views_appended_once': True,
            'call_config_identical_to_baseline': True, 'request_chars': chars,
            'current_pairs': len(model_input['pairs']), 'current_runs': len(model_input['runs']),
            'active_entries': len(model_input['memory']['entries']),
            'knowledge_items': sum(len(e['knowledge']) for e in model_input['memory']['entries']),
            'input_tokens': None, 'token_note': 'No actual model call; no token saving claim.'}
        sources_to_freeze += [old_root / n for n in ('replay_bundle.json', 'model_input.json', 'history_pair_sources.json')]
        sources_to_freeze += [Path(source['path']) for source in sources.values() if source is not None]
    save(HERE / 'INPUT_CHECKS.json', checks)
    sources_to_freeze += list(archive_glob(HERE / 'cases', '*', recursive=True)) + [HERE / 'INPUT_CHECKS.json']
    manifest = {'prompt_version': replay.LEARNING_PROMPT_VERSION, 'memory_contract': NEW,
        'input_view': replay.INPUT_VIEW, 'call_config': baseline['call_config'],
        'max_input_chars': baseline['max_input_chars'],
        'max_restarts_per_stage': baseline['max_restarts_per_stage'],
        'max_logical_calls': baseline['max_logical_calls'], 'max_http_attempts': baseline['max_http_attempts'],
        'status': 'offline_prepared_no_model_calls',
        'source_prompt': '/Users/didi/Downloads/replay_multi_knowledge_learning_prompt_v1.md',
        'original_prompt_sha256': sha(HERE / 'original_prompt.md'),
        'candidate_prompt_sha256': sha(HERE / 'candidate_prompt.md'),
        'sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(sources_to_freeze)) if resolve(p).is_file()}}
    save(HERE / 'freeze.json', manifest)
    return checks


def verify():
    manifest = read(HERE / 'freeze.json')
    for name, digest in manifest['sha256'].items():
        assert sha(ROOT / name) == digest, name
    for case in ('R05', 'R06'):
        path = HERE / 'cases' / case
        bundle = read(path / 'replay_bundle.json')
        verify_experiment_editor(bundle)
        messages = replay.messages_for(bundle, memory_contract=NEW, prompt_version=replay.LEARNING_PROMPT_VERSION,
                                       history_sources=read(path / 'history_pair_sources.json'))
        assert messages == read(path / 'messages.json')
        assert read(path / 'call_config.json') == manifest['call_config']
    return {'frozen_files_checked': len(manifest['sha256']), 'cases': ['R05', 'R06'], 'model_calls': 0}


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        print(json.dumps(prepare(), ensure_ascii=False, indent=2))
    elif sys.argv[1:] == ['verify']:
        print(json.dumps(verify()))
    else:
        raise SystemExit('Use prepare or verify; this script does not call models.')
