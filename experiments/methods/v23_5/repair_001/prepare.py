"""Build/verify real Repair inputs, or validate a saved response. No API transport."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.repair_001 import repair
from experiments.methods.v23_5.verifier_fact_screen_001 import prepare as policy

shared, io, v = policy.shared, policy.io, policy.v
HERE = Path(__file__).parent
VERSION = 'v23_5_targeted_repair_v1'
OUTPUT = ROOT/'artifacts/methods/v23_5/repair_001'
LIVE = ROOT/'artifacts/methods/v23_5/verifier_fact_screen_run_001'
FILES = ('prepare.py', 'repair.py', 'repair_prompt.md', 'README.md', 'test_repair.py')


def verify_sources():
    policy.verify(policy.DEFAULT_OUTPUT)
    manifest = io.read(LIVE/'manifest.json')
    for item in manifest['files']:
        io.require(io.digest(item['path']) == item['sha256'], f'Verifier run changed: {item["path"]}')


def load_case(name):
    original = io.DEFAULT_OUTPUT/'cases'/name
    run = LIVE/'runs'/name/'attempts/001'
    model_input = io.read(policy.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json')
    response = v.parse_output((run/'response.json').read_text(encoding='utf-8'))
    verdicts = v.validate_response(response, model_input)
    io.require(repair.exact(verdicts) == repair.exact(io.read(run/'verifier_output.json')), 'Verifier result mismatch')
    candidate = io.read(original/'candidate.json')
    payload = io.read(original/'frozen/bundle.json')['payload']
    io.require(repair.exact(io.read(original/'memory_before.json')) == repair.exact(payload['memory']), 'Memory snapshot mismatch')
    repair.validate_candidate(candidate, payload)
    return model_input, verdicts, candidate, payload


def build_input(verifier_input, verdicts, candidate):
    v.validate_result(verdicts, verifier_input)
    originals = {v.position(t['target'], 'target'): t for t in verifier_input['targets']}
    targets, refs = [], set()
    for row in verdicts['results']:
        if row['verdict'] != 'CONFLICT':
            continue
        ei, ki = key = v.position(row['target'], 'target')
        target = deepcopy(originals[key])
        io.require(repair.exact(target['knowledge']) == repair.exact(candidate['entries'][ei]['knowledge'][ki]),
                   'Verifier target differs from candidate')
        target['issues'] = deepcopy(row['issues'])
        targets.append(target)
        refs.update(target['knowledge']['evidence'])
        refs.update(ref for issue in row['issues'] for ref in issue['evidence'])
    sources = {ref: deepcopy(source) for ref, source in verifier_input['source_records'].items() if ref in refs}
    io.require(set(sources) == refs, 'Missing requested source')
    menu_ids = {cid for s in sources.values() for cid in s.get('command_set_refs', {}).values()}
    menus = {cid: deepcopy(menu) for cid, menu in verifier_input['command_sets'].items() if cid in menu_ids}
    context = deepcopy(verifier_input['context'])
    runs = {ref.split(':')[0] for ref in refs if '/' not in ref and ref != 'diff'}
    context['pairs'] = [p for p in context['pairs'] if p['parent'] in runs or p['candidate'] in runs]
    result = {'context': context, 'targets': targets, 'source_records': sources, 'command_sets': menus}
    # Include issue-only citations in the restoration check, without adding synthetic
    # Knowledge to actual model messages. Preserve source-local IDs and shared IDs.
    view = {**result, 'targets': [{'knowledge': {'evidence': list(sources)}}]}
    restored = shared.restore(view)
    original = shared.restore(verifier_input)
    for ref in sources:
        io.require(repair.exact(restored['source_records'][ref]) == repair.exact(original['source_records'][ref]),
                   f'Raw record/menu mismatch: {ref}')
    return result


def row_stats(name, value, original):
    return {'round': name, 'allowed_targets': [t['target'] for t in value['targets']],
            'source_records': len(value['source_records']), 'shared_menus': len(value['command_sets']),
            'input_size': io.size(value), 'verifier_input_size': io.size(original), 'api_prompt_tokens': None}


def prepare(output):
    io.require(not output.exists(), 'Output exists; use verify or a fresh directory')
    verify_sources()
    manifest = {'version': VERSION, 'created_at': datetime.now(timezone.utc).isoformat(),
                'policy_manifest_sha256': io.digest(policy.DEFAULT_OUTPUT/'manifest.json'),
                'live_manifest_sha256': io.digest(LIVE/'manifest.json'), 'files': {}, 'dependencies': {}}
    # Freeze the actual deterministic validators used by this prototype, by digest.
    for module in ('src/skill_evolution/v23_5/replay.py', 'src/skill_evolution/v23/memory.py',
                   'src/skill_evolution/v23/diagnosis.py', 'src/skill_evolution/v23_5/memory_view.py'):
        manifest['dependencies'][module] = io.digest(ROOT/module)
    output.mkdir(parents=True)

    def freeze(path, raw):
        dest = output/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        manifest['files'][path] = io.digest(dest)

    def freeze_json(path, value):
        freeze(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())

    for filename in FILES:
        freeze(filename, (HERE/filename).read_bytes())
    prompt = (HERE/'repair_prompt.md').read_text(encoding='utf-8')
    rows = []
    for name in io.ROUNDS:
        original, verdicts, candidate, _ = load_case(name)
        value = build_input(original, verdicts, candidate)
        for filename, obj in [('repair_input.json', value), ('candidate.json', candidate),
                              ('verifier_output.json', verdicts), ('messages.json', v.messages_for(value, prompt))]:
            freeze_json(f'cases/{name}/{filename}', obj)
        rows.append(row_stats(name, value, original))
    freeze_json('summary.json', {'rounds': rows, 'model_calls': 0, 'memory_commits': 0,
                                'semantic_repair_evaluation_available': False})
    io.save(output/'manifest.json', manifest)
    return verify(output)


def verify(output):
    manifest = io.read(output/'manifest.json')
    io.require(manifest['version'] == VERSION, 'Repair version mismatch')
    verify_sources()
    io.require(io.digest(policy.DEFAULT_OUTPUT/'manifest.json') == manifest['policy_manifest_sha256'], 'Policy changed')
    io.require(io.digest(LIVE/'manifest.json') == manifest['live_manifest_sha256'], 'Verifier run manifest changed')
    for path, digest in manifest['files'].items():
        io.require(io.digest(output/path) == digest, f'Frozen Repair file changed: {path}')
    for path, digest in manifest['dependencies'].items():
        io.require(io.digest(ROOT/path) == digest, f'Formal validator changed: {path}')
    for filename in FILES:
        io.require(io.digest(HERE/filename) == io.digest(output/filename), f'Repair source changed: {filename}')
    rows = []
    for name in io.ROUNDS:
        original, verdicts, candidate, _ = load_case(name)
        value = build_input(original, verdicts, candidate)
        case = output/'cases'/name
        for filename, expected in [('repair_input.json', value), ('candidate.json', candidate),
                                   ('verifier_output.json', verdicts),
                                   ('messages.json', v.messages_for(value, (output/'repair_prompt.md').read_text()))]:
            io.require(repair.exact(io.read(case/filename)) == repair.exact(expected), f'Construction differs: {name}/{filename}')
        rows.append(row_stats(name, value, original))
    io.require(io.read(output/'summary.json')['rounds'] == rows, 'Statistics changed')
    return {'valid': True, 'version': VERSION, 'rounds': rows, 'only_actual_conflicts': True,
            'selected_original_records_and_menus_equal': True, 'source_archives_unchanged': True,
            'baseline_excluded_from_messages': True, 'model_calls': 0, 'memory_commits': 0,
            'semantic_repair_evaluation_available': False}


def validate_saved(output, name, response_path, result_dir):
    """Save success/failure separately. Never emit a merged candidate on failure."""
    io.require(not result_dir.exists(), 'Result directory exists; choose a fresh directory')
    result_dir.mkdir(parents=True)
    try:
        verify(output)
        raw = response_path.read_text(encoding='utf-8')
        (result_dir/'response.json').write_text(raw, encoding='utf-8')
        value = io.read(output/'cases'/name/'repair_input.json')
        result = repair.validate_response(v.parse_output(raw), value)
        candidate = io.read(output/'cases'/name/'candidate.json')
        _, _, _, payload = load_case(name)
        merged = repair.merge(result, value, candidate, payload)
        io.save(result_dir/'repair_output.json', result)
        io.save(result_dir/'merged_candidate.json', merged)
        report = {'valid': True, 'semantic_truth_verified': False, 'memory_commits': 0}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report = {'valid': False, 'error_type': type(exc).__name__, 'error': str(exc),
                  'semantic_truth_verified': False, 'memory_commits': 0}
    io.save(result_dir/'validation.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify', 'validate'))
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--round', choices=io.ROUNDS)
    parser.add_argument('--response', type=Path)
    parser.add_argument('--result-dir', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        report = prepare(args.output.resolve())
        io.save(args.output/'validation.json', report)
    elif args.command == 'verify':
        report = verify(args.output.resolve())
    else:
        if not all((args.round, args.response, args.result_dir)):
            parser.error('validate requires --round, --response, --result-dir')
        report = validate_saved(args.output.resolve(), args.round, args.response.resolve(), args.result_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['valid'] else 1)
