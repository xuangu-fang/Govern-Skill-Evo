"""Lossless shared action menus for frozen Verifier inputs. No model calls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_input_001 import verifier as v

io = v.inputs
DEFAULT_OUTPUT = ROOT/'artifacts/methods/v23_5/verifier_input_002'
PROMPT = Path(__file__).with_name('verifier_prompt.md')
VERSION = 'v23_5_statement_verifier_shared_menus_v2'


def menu_references(value):
    """Inspect only the raw record, including full-run initial/before/after states."""
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'commands_ref':
                io.require(item is None or isinstance(item, str) and bool(item), 'Invalid commands_ref')
                if item is not None:
                    result.add(item)
            else:
                result.update(menu_references(item))
    elif isinstance(value, list):
        for item in value:
            result.update(menu_references(item))
    return result


def check_sources(value, mapping_field):
    evidence = {ref for item in value['targets'] for ref in item['knowledge']['evidence']}
    io.require(evidence == set(value['source_records']), 'Evidence/source coverage differs')
    for ref, source in value['source_records'].items():
        if ref.rsplit('/', 1)[-1] == 'diff':
            io.require(mapping_field not in source and 'record' not in source, 'Unexpected diff menu/record')
            continue
        io.require('record' in source and isinstance(source.get(mapping_field), dict), 'Missing record/menu map')
        io.require(menu_references(source['record']) == set(source[mapping_field]),
                   f'{ref}: missing or unused local menu reference')


def menu_key(menu):
    io.require(isinstance(menu, list) and all(isinstance(action, str) for action in menu),
               'Action menu must be a list of strings')
    # Ordered tuple preserves duplicates and exact text; no hash-only equality.
    return tuple(menu)


def compact(original):
    io.require(set(original) == {'context', 'targets', 'source_records'}, 'Not a v1 input')
    check_sources(original, 'command_sets')
    value = deepcopy(original)
    pool, ids = {}, {}
    for source in value['source_records'].values():
        io.require('command_set_refs' not in source, 'Input already contains shared references')
        if 'command_sets' not in source:
            continue
        local = source.pop('command_sets')
        links = {}
        for old_id, menu in local.items():
            key = menu_key(menu)
            if key not in ids:
                shared_id = f'CS{len(ids) + 1}'
                ids[key] = shared_id
                pool[shared_id] = menu
            links[old_id] = ids[key]
        source['command_set_refs'] = links
    value['command_sets'] = pool
    verify_equivalence(original, value)
    return value


def restore(value):
    io.require(set(value) == {'context', 'targets', 'source_records', 'command_sets'}, 'Not a v2 input')
    check_sources(value, 'command_set_refs')
    pool = value['command_sets']
    io.require(isinstance(pool, dict), 'Shared menus must be an object')
    io.require(all(isinstance(key, str) and key for key in pool), 'Invalid shared ID')
    keys = [menu_key(menu) for menu in pool.values()]
    io.require(len(set(keys)) == len(keys), 'Duplicate shared menu content')
    restored, used = deepcopy(value), set()
    restored.pop('command_sets')
    for source in restored['source_records'].values():
        io.require('command_sets' not in source, 'Unexpected inline menus in v2')
        if 'command_set_refs' not in source:
            continue
        links = source.pop('command_set_refs')
        local = {}
        for old_id, shared_id in links.items():
            io.require(isinstance(shared_id, str) and shared_id in pool, 'Missing shared menu reference')
            local[old_id] = deepcopy(pool[shared_id])
            used.add(shared_id)
        source['command_sets'] = local
    io.require(used == set(pool), 'Unused shared menu')
    return restored


def verify_equivalence(original, value):
    restored = restore(value)
    # Python equality alone considers False == 0 and 1 == 1.0. Preserve JSON types too.
    exact = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    io.require(exact(restored) == exact(original), 'Restored input differs from original')
    return {'valid': True, 'entire_input_equal': True, 'evidence_ids_equal': True,
            'local_menu_references_equal': True, 'raw_records_equal': True}


def statistics(original, value):
    before, after = io.size(original), io.size(value)
    return {'targets': len(original['targets']), 'source_records': len(original['source_records']),
            'original_menu_occurrences': sum(len(s.get('command_sets', {})) for s in original['source_records'].values()),
            'shared_menus': len(value['command_sets']), 'original_size': before, 'shared_size': after,
            'data_chars_reduction_pct': round(100 * (1 - after['chars']/before['chars']), 2),
            'api_prompt_tokens': None}


def prepare(output):
    io.require(not output.exists(), 'Output exists; use verify or a fresh directory')
    v.verify_messages(v.DEFAULT_OUTPUT)
    output.mkdir(parents=True)
    manifest = {'version': VERSION, 'source_contract': str(v.DEFAULT_OUTPUT),
                'source_manifest_sha256': io.digest(v.DEFAULT_OUTPUT/'manifest.json'), 'files': {}, 'cases': []}

    def freeze(path, raw):
        dest = output/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        manifest['files'][path] = io.digest(dest)

    freeze('prepare.py', Path(__file__).read_bytes())
    freeze('prompt.md', PROMPT.read_bytes())
    prompt = PROMPT.read_text(encoding='utf-8')
    rows = []
    for name in io.ROUNDS:
        source = v.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json'
        original = io.read(source)
        value = compact(original)
        prefix = f'cases/{name}'
        freeze(f'{prefix}/original_input.json', source.read_bytes())
        messages = v.messages_for(value, prompt)
        for filename, data in [('verifier_input.json', value), ('messages.json', messages)]:
            freeze(f'{prefix}/{filename}', (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode())
        manifest['cases'].append({'round': name, 'source_sha256': io.digest(source)})
        rows.append({'round': name, **statistics(original, value),
                     'original_messages_size': io.size(io.read(source.with_name('messages.json'))),
                     'shared_messages_size': io.size(messages)})
    summary = {'rounds': rows, 'model_calls': 0, 'actor_calls': 0, 'memory_commits': 0,
               'note': 'JSON value equality; no whitespace-byte equivalence claim. Sizes are characters/bytes, not Tokens.'}
    freeze('summary.json', (json.dumps(summary, ensure_ascii=False, indent=2)+'\n').encode())
    io.save(output/'manifest.json', manifest)
    return verify(output)


def verify(output):
    manifest = io.read(output/'manifest.json')
    io.require(manifest['version'] == VERSION, 'Unsupported version')
    source = Path(manifest['source_contract'])
    v.verify_messages(source)
    io.require(io.digest(source/'manifest.json') == manifest['source_manifest_sha256'], 'Source manifest changed')
    for path, expected in manifest['files'].items():
        io.require(io.digest(output/path) == expected, f'Frozen file changed: {path}')
    io.require(io.digest(__file__) == io.digest(output/'prepare.py'), 'Builder changed')
    io.require(io.digest(PROMPT) == io.digest(output/'prompt.md'), 'Prompt changed')
    io.require([r['round'] for r in manifest['cases']] == list(io.ROUNDS), 'Round list changed')
    for row in manifest['cases']:
        case = output/'cases'/row['round']
        old = source/'cases'/row['round']/'verifier_input.json'
        io.require(io.digest(old) == row['source_sha256'] == io.digest(case/'original_input.json'), 'Original input changed')
        original, value = io.read(old), io.read(case/'verifier_input.json')
        verify_equivalence(original, value)
        io.require(compact(original) == value, 'Noncanonical shared mapping')
        io.require(io.read(case/'messages.json') == v.messages_for(value, PROMPT.read_text(encoding='utf-8')),
                   'Messages differ from shared input/prompt')
    return {'valid': True, 'rounds': list(io.ROUNDS), 'entire_original_inputs_restored': True,
            'source_contract_and_archives_unchanged': True, 'model_calls': 0, 'actor_calls': 0, 'memory_commits': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify', 'restore'))
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--round', choices=io.ROUNDS)
    parser.add_argument('--restored-output', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        report = prepare(args.output.resolve())
    else:
        report = verify(args.output.resolve())
        if args.command == 'restore':
            io.require(args.round and args.restored_output, 'restore needs --round and --restored-output')
            io.require(not args.restored_output.exists(), 'Restore destination already exists')
            value = io.read(args.output/'cases'/args.round/'verifier_input.json')
            io.save(args.restored_output, restore(value))
    if args.command != 'restore':
        io.save(args.output/'validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
