"""Build frozen R01-R03 verification inputs; no model, Actor or Memory writes."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.memory import MULTI_KNOWLEDGE_CONTRACT as CONTRACT
from src.skill_evolution.v23.replay import validate_payload
from src.skill_evolution.v23_4.replay_view import _current_pairs
from src.skill_evolution.v23_5.replay import validate_result
from src.skill_evolution.v23_5.replay_view import model_input

ROUNDS = ('R01', 'R02', 'R03')
DEFAULT_SOURCE = ROOT / 'artifacts/methods/v23_5/alfworld_initial_skill_001/S1'
DEFAULT_OUTPUT = ROOT / 'artifacts/methods/v23_5/verifier_input_001'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def size(value):
    compact = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return {'chars': len(compact), 'utf8_bytes': len(compact.encode('utf-8'))}


def select_targets(candidate, memory):
    """Only exact items in explicitly revised entries qualify as carried over."""
    old = {entry['id']: entry for entry in memory['entries']}
    revised = {mid for entry in candidate['entries'] for mid in entry['revises']}
    targets, inventory = [], []
    for ei, entry in enumerate(candidate['entries']):
        remaining = [(mid, ki, item) for mid in entry['revises']
                     for ki, item in enumerate(old[mid]['knowledge'])]
        for ki, item in enumerate(entry['knowledge']):
            target = {'entry_index': ei, 'knowledge_index': ki}
            match = next((i for i, (_, _, previous) in enumerate(remaining) if item == previous), None)
            row = {'target': target, 'revises': entry['revises']}
            if match is not None:
                mid, old_index, _ = remaining.pop(match)
                row.update(classification='unchanged', previous={'memory_id': mid, 'knowledge_index': old_index})
            else:
                row['classification'] = 'new' if not entry['revises'] else 'changed_or_added_in_revision'
                targets.append({'target': target, 'knowledge': deepcopy(item)})
            inventory.append(row)
    implicit = [{'memory_id': mid, 'knowledge_count': len(entry['knowledge'])}
                for mid, entry in old.items() if mid not in revised]
    return targets, {'candidate_items': inventory, 'untouched_memory_entries': implicit}


def extract(ref, bundle, historical):
    """Fixed reference-granularity extraction; never expand neighbors or claims."""
    if '/' in ref:
        context_id, local = ref.rsplit('/', 1)
        source = historical[context_id]
    else:
        context_id, local, source = None, ref, bundle
    payload = source['payload']
    if local == 'diff':
        return {'parent': deepcopy(payload['parent']), 'diff': payload['diff'],
                'execution_context': deepcopy(source['execution_context'])}
    rid, _, suffix = local.partition(':')
    run = next(r for r in payload['runs'] if r['ref'] == rid)
    _current_pairs(source)  # Includes task IDs and recorded pair audit checks.
    audit = next(a for a in source['pair_audit'] if rid in a['pair'].values())
    role = next(side for side, value in audit['pair'].items() if value == rid)
    result = {'task_id': audit['task']['id'], 'task': run['task'], 'role': role}
    if not suffix:
        record = run
        states = [run['initial'], *[s[side] for s in run['steps'] for side in ('before', 'after')]]
    elif suffix == '0':
        record, states = run['initial'], [run['initial']]
    elif suffix == 'outcome':
        record, states = run['outcome'], []
        result['executed_action_count'] = len(run['steps'])
    else:
        record = next(s for s in run['steps'] if s['step'] == local)
        states = [record['before'], record['after']]
    menus = list(dict.fromkeys(s['commands_ref'] for s in states if s['commands_ref'] is not None))
    result.update(record=deepcopy(record),
                  command_sets={key: deepcopy(payload['command_sets'][key]) for key in menus})
    if context_id:
        # Historical Actor conditions must not be inferred from the current round.
        result['execution_context'] = deepcopy(source['execution_context'])
    return result


def build_input(bundle, candidate, historical=None):
    historical = historical or {}
    payload = validate_payload(bundle['payload'], memory_contract=CONTRACT)
    validate_result(candidate, payload, memory_contract=CONTRACT)
    pairs, _ = _current_pairs(bundle)
    targets, inventory = select_targets(candidate, payload['memory'])
    refs = list(dict.fromkeys(ref for target in targets for ref in target['knowledge']['evidence']))
    for cid in {ref.rsplit('/', 1)[0] for ref in refs if '/' in ref}:
        prior = historical[cid]
        validate_payload(prior['payload'], memory_contract=CONTRACT)
        _current_pairs(prior)
        # Check retrieved originals against the actual frozen Memory sources.
        for key, original in payload['memory']['sources'].items():
            if key.rsplit('/', 1)[0] != cid:
                continue
            local = key.rsplit('/', 1)[1]
            if local == 'diff':
                require(original == {k: prior['payload'][k] for k in ('parent', 'diff')} |
                        {'execution_context': prior['execution_context']}, 'Historical edit differs')
            else:
                run = next(r for r in prior['payload']['runs'] if r['ref'] == local)
                require(original['run'] == run, 'Historical run differs')
                require(all(prior['payload']['command_sets'].get(k) == v
                            for k, v in original['command_sets'].items()), 'Historical menus differ')
    cited_runs = {ref.split(':')[0] for ref in refs if '/' not in ref and ref != 'diff'}
    # Only identities of cited current pairs; no all-task catalog or extra outcomes.
    related_pairs = [{k: pair[k] for k in ('task_id', 'parent', 'candidate')}
                     for pair in pairs if pair['parent'] in cited_runs or pair['candidate'] in cited_runs]
    value = {'context': {'parent': payload['parent'], 'diff': payload['diff'],
                         'execution_context': deepcopy(bundle['execution_context']), 'pairs': related_pairs},
             'targets': targets, 'source_records': {ref: extract(ref, bundle, historical) for ref in refs}}
    return value, inventory


def summarize(bundle, candidate, value, inventory, replay_input, messages):
    labels = [row['classification'] for row in inventory['candidate_items']]
    refs = list(value['source_records'])
    occurrences = sum(len(t['knowledge']['evidence']) for t in value['targets'])
    current_steps = sum(len(r['steps']) for r in bundle['payload']['runs'])
    verifier_size, replay_size = size(value), size(replay_input)
    return {
        'candidate_knowledge': len(labels), 'targets': len(value['targets']),
        'new': labels.count('new'), 'changed_or_added_in_revision': labels.count('changed_or_added_in_revision'),
        'unchanged_in_candidate': labels.count('unchanged'),
        'unchanged_in_untouched_entries': sum(e['knowledge_count'] for e in inventory['untouched_memory_entries']),
        'evidence_occurrences': occurrences, 'unique_evidence': len(refs),
        'duplicate_references_removed': occurrences - len(refs),
        'historical_references': sum('/' in ref for ref in refs),
        'step_records': sum(':' in ref and ref.rsplit(':', 1)[1].isdigit() and not ref.endswith(':0') for ref in refs),
        'total_current_execution_steps': current_steps,
        'verifier_input': verifier_size, 'replay_model_input': replay_size,
        'verifier_chars_reduction_vs_replay_model_input_pct': round(100 * (1 - verifier_size['chars'] / replay_size['chars']), 2),
        'original_replay_messages': size(messages),
        'component_sizes': {key: size(part) for key, part in value.items()},
        'api_prompt_tokens': None,
        'token_note': 'No tokenizer estimate or API call. Character comparison uses compact JSON data, excludes a future Verifier system prompt.',
    }


def prepare(source, output):
    require(not output.exists(), 'Output exists; use verify or a fresh output directory')
    output.mkdir(parents=True)
    manifest, rows = {'source': str(source.resolve()), 'files': [], 'rounds': list(ROUNDS)}, []

    def freeze(original, relative):
        original = original.resolve()
        raw = original.read_bytes()
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        manifest['files'].append({'source': str(original), 'copy': relative,
                                  'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
        return read(destination)

    # Python source is frozen as bytes separately, not parsed as JSON.
    raw_script = Path(__file__).read_bytes()
    (output/'prepare.py').write_bytes(raw_script)
    manifest['builder_sha256'] = hashlib.sha256(raw_script).hexdigest()
    for name in ROUNDS:
        rd, case = source/'rounds'/name, f'cases/{name}'
        selector = freeze(rd/'replay/result.json', f'{case}/frozen/replay_selection.json')
        attempt = (rd/'replay'/selector['path']).resolve()
        require(attempt.is_relative_to((rd/'replay/attempts').resolve()), 'Invalid Replay attempt path')
        bundle = freeze(rd/'pairs/input.json', f'{case}/frozen/bundle.json')
        candidate = freeze(attempt/'replay.json', f'{case}/candidate.json')
        prior = freeze(rd/'round_input.json', f'{case}/frozen/round_input.json')
        archive = freeze(rd/'memory/archive'/f'S1_{name}.json', f'{case}/frozen/commit.json')
        require(prior['memory'] == bundle['payload']['memory'], 'Round-before Memory differs')
        require(prior['parent'] == bundle['payload']['parent'], 'Round Parent differs')
        require(archive['context'] == bundle and archive['result'] == candidate, 'Committed Replay differs')
        replay_files = {}
        for filename in ('input.json', 'model_input.json', 'messages.json', 'run.json', 'response.json', 'parsed.json', 'validation.json'):
            replay_files[filename] = freeze(attempt/filename, f'{case}/frozen/replay/{filename}')
        require(replay_files['input.json'] == bundle, 'Replay input differs from pairs')
        require(replay_files['run.json']['status'] == 'valid' and replay_files['validation.json']['valid'] is True,
                'Selected Replay is not valid')
        require(replay_files['response.json']['finish_reason'] == 'stop', 'Incomplete Replay output')
        from src.skill_evolution.v22.diagnosis_editor import parse_json_response
        require(parse_json_response(replay_files['response.json']['content']) == candidate == replay_files['parsed.json'],
                'Candidate differs from actual Replay response')
        require(replay_files['model_input.json'] == model_input(bundle), 'Frozen Replay model input differs')
        historical = {}
        targets, _ = select_targets(candidate, bundle['payload']['memory'])
        contexts = sorted({ref.rsplit('/', 1)[0] for t in targets for ref in t['knowledge']['evidence'] if '/' in ref})
        for cid in contexts:
            require(cid in {k.rsplit('/', 1)[0] for k in bundle['payload']['memory']['sources']}, 'Unknown historical context')
            saved = freeze(rd/'memory/archive'/f'{cid}.json', f'{case}/frozen/history/{cid}.json')
            require(saved['context_id'] == cid, 'Historical context identity differs')
            historical[cid] = saved['context']
        value, inventory = build_input(bundle, candidate, historical)
        stats = summarize(bundle, candidate, value, inventory, replay_files['model_input.json'], replay_files['messages.json'])
        save(output/case/'memory_before.json', bundle['payload']['memory'])
        save(output/case/'inventory.json', inventory)
        save(output/case/'verifier_input.json', value)
        save(output/case/'stats.json', stats)
        rows.append({'round': name, **stats})
    save(output/'manifest.json', manifest)
    save(output/'summary.json', {'rounds': rows, 'model_calls': 0, 'actor_calls': 0, 'memory_commits': 0})
    return verify(output)


def verify(output):
    manifest = read(output/'manifest.json')
    for entry in manifest['files']:
        require(digest(output/entry['copy']) == entry['sha256'], f"Frozen source changed: {entry['copy']}")
        require(digest(entry['source']) == entry['sha256'], f"Original source changed: {entry['source']}")
    require(digest(output/'prepare.py') == manifest['builder_sha256'], 'Frozen builder changed')
    rows = []
    for name in manifest['rounds']:
        case = output/'cases'/name
        bundle, candidate = read(case/'frozen/bundle.json'), read(case/'candidate.json')
        historical = {p.stem: read(p)['context'] for p in (case/'frozen/history').glob('*.json')}
        value, inventory = build_input(bundle, candidate, historical)
        require(read(case/'verifier_input.json') == value, f'{name}: extracted input differs')
        require(read(case/'memory_before.json') == bundle['payload']['memory'], f'{name}: Memory differs')
        require(read(case/'inventory.json') == inventory, f'{name}: inventory differs')
        stats = summarize(bundle, candidate, value, inventory, read(case/'frozen/replay/model_input.json'),
                          read(case/'frozen/replay/messages.json'))
        require(read(case/'stats.json') == stats, f'{name}: statistics differ')
        rows.append({'round': name, **stats})
    require(read(output/'summary.json') == {'rounds': rows, 'model_calls': 0, 'actor_calls': 0, 'memory_commits': 0},
            'Summary differs')
    return {'valid': True, 'rounds': list(manifest['rounds']), 'targets': sum(r['targets'] for r in rows),
            'source_files_unchanged': len(manifest['files']), 'frozen_inputs_reconstructed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = prepare(args.source.resolve(), args.output.resolve()) if args.command == 'prepare' else verify(args.output.resolve())
    save(args.output/'validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
