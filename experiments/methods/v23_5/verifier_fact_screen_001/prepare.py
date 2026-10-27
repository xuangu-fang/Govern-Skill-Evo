"""Freeze the obvious-fact-screen prompt, boundary and pre-run reference. Offline only."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_input_002 import prepare as shared

io, v = shared.io, shared.v
HERE = Path(__file__).parent
VERSION = 'v23_5_obvious_fact_screen_v1'
DEFAULT_OUTPUT = ROOT/'artifacts/methods/v23_5/verifier_fact_screen_001'
FILES = ('prepare.py', 'verifier_prompt.md', 'BOUNDARY.md', 'reference_review.json')


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def validate_reference(reference, inputs):
    io.require(reference['policy_version'] == VERSION, 'Reference policy mismatch')
    io.require(reference['human_reviewed'] is False and reference['new_policy_model_calls'] == 0,
               'Reference provenance mismatch')
    io.require(reference['prior_verifier_outputs_seen'] is True and
               reference['blind_to_prior_verifier_outputs'] is False, 'Prior exposure must be disclosed')
    expected = {(name, *v.position(t['target'], 'input.target')): t['knowledge']
                for name, value in inputs.items() for t in value['targets']}
    seen, fixture_results, finding_ids = set(), {name: [] for name in inputs}, set()
    for item in reference['items']:
        key = item['round'], *v.position(item['target'], 'reference.target')
        io.require(key in expected and key not in seen, 'Unknown or duplicate reference target')
        seen.add(key)
        io.require(exact(item['knowledge']) == exact(expected[key]), 'Reference Knowledge changed')
        io.require(item['scoring_group'] in ('primary', 'review_only'), 'Invalid scoring group')
        sources = inputs[item['round']]['source_records']
        refs = item['checked_evidence']
        io.require(len(refs) == len(set(refs)) and set(refs) <= set(sources), 'Invalid checked references')
        for field in ('review_note', 'accepted_limits', 'change_reason'):
            v.nonempty(item[field], f'reference.{field}')
        findings = item['required_findings']
        io.require(bool(findings) == (item['expected_verdict'] == 'CONFLICT'), 'Reference verdict/findings mismatch')
        issues = []
        for finding in findings:
            v.nonempty(finding['id'], 'finding.id')
            io.require(finding['id'] not in finding_ids, 'Duplicate finding ID')
            finding_ids.add(finding['id'])
            for field in ('materiality', 'detection_criterion'):
                v.nonempty(finding[field], f'finding.{field}')
            io.require(bool(finding['anchors']), 'Missing original evidence anchors')
            for anchor in finding['anchors']:
                ref = anchor['evidence']
                io.require(ref in finding['evidence'] and ref in sources, 'Unprovided anchor reference')
                value = sources[ref]
                for part in anchor['path']:
                    value = value[part]
                io.require(exact(value) == exact(anchor['value']), 'Original anchor value changed')
            issues.append({k: finding[k] for k in ('statement', 'reason', 'evidence')})
        fixture_results[item['round']].append({'target': item['target'], 'verdict': item['expected_verdict'], 'issues': issues})
    io.require(seen == set(expected), 'Reference target coverage incomplete')
    for name, rows in fixture_results.items():
        # Structural check only; these reference labels are never actual model outputs.
        v.validate_result({'results': rows}, inputs[name])
    return {'targets': len(seen), 'expected_verdict_counts': dict(Counter(x['expected_verdict'] for x in reference['items'])),
            'primary_verdict_counts': dict(Counter(x['expected_verdict'] for x in reference['items'] if x['scoring_group'] == 'primary')),
            'review_only': sum(x['scoring_group'] == 'review_only' for x in reference['items']),
            'required_findings': len(finding_ids)}


def prepare(output):
    io.require(not output.exists(), 'Output exists; choose a fresh directory')
    shared.verify(shared.DEFAULT_OUTPUT)
    inputs = {name: io.read(shared.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json') for name in io.ROUNDS}
    reference = io.read(HERE/'reference_review.json')
    summary = validate_reference(reference, inputs)
    output.mkdir(parents=True)
    manifest = {'policy_version': VERSION, 'input_root': str(shared.DEFAULT_OUTPUT),
                'input_manifest_sha256': io.digest(shared.DEFAULT_OUTPUT/'manifest.json'),
                'validator_sha256': io.digest(v.__file__), 'files': {}, 'cases': []}

    def freeze(path, raw):
        dest = output/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        manifest['files'][path] = io.digest(dest)

    for name in FILES:
        freeze(name, (HERE/name).read_bytes())
    prompt = (HERE/'verifier_prompt.md').read_text(encoding='utf-8')
    for name, value in inputs.items():
        source = shared.DEFAULT_OUTPUT/'cases'/name/'verifier_input.json'
        freeze(f'cases/{name}/verifier_input.json', source.read_bytes())
        messages = v.messages_for(value, prompt)  # No reference labels, boundary examples or review notes.
        freeze(f'cases/{name}/messages.json', (json.dumps(messages, ensure_ascii=False, indent=2)+'\n').encode())
        manifest['cases'].append({'round': name, 'input_sha256': io.digest(source), 'targets': len(value['targets'])})
    summary.update(policy_version=VERSION, human_reviewed=False, prior_outputs_seen=True,
                   model_calls=0, actor_calls=0, repair_calls=0, memory_commits=0,
                   model_metrics_available=False, input_root=str(shared.DEFAULT_OUTPUT))
    freeze('summary.json', (json.dumps(summary, ensure_ascii=False, indent=2)+'\n').encode())
    io.save(output/'manifest.json', manifest)
    return verify(output)


def verify(output):
    manifest = io.read(output/'manifest.json')
    io.require(manifest['policy_version'] == VERSION, 'Policy version mismatch')
    source = Path(manifest['input_root'])
    shared.verify(source)
    io.require(io.digest(source/'manifest.json') == manifest['input_manifest_sha256'], 'Input manifest changed')
    io.require(io.digest(v.__file__) == manifest['validator_sha256'], 'Output validator changed')
    for name, digest in manifest['files'].items():
        io.require(io.digest(output/name) == digest, f'Frozen file changed: {name}')
    for name in FILES:
        io.require(io.digest(output/name) == io.digest(HERE/name), f'Source version changed: {name}')
    io.require([c['round'] for c in manifest['cases']] == list(io.ROUNDS), 'Case list changed')
    prompt = (output/'verifier_prompt.md').read_text(encoding='utf-8')
    inputs = {}
    for case in manifest['cases']:
        name = case['round']
        path = output/'cases'/name/'verifier_input.json'
        io.require(io.digest(path) == case['input_sha256'] == io.digest(source/'cases'/name/'verifier_input.json'), 'Input changed')
        inputs[name] = io.read(path)
        io.require(len(inputs[name]['targets']) == case['targets'], 'Target count changed')
        io.require(io.read(path.with_name('messages.json')) == v.messages_for(inputs[name], prompt), 'Messages changed or reference leaked')
    reference = io.read(output/'reference_review.json')
    io.require(reference['input_manifest_sha256'] == manifest['input_manifest_sha256'], 'Reference bound to different input')
    old_ref = HERE.parent/'verifier_input_001/results/reference_review.json'
    io.require(io.digest(old_ref) == reference['previous_reference_sha256'], 'Previous reference changed')
    summary = validate_reference(reference, inputs)
    for key, value in summary.items():
        io.require(io.read(output/'summary.json')[key] == value, 'Summary mismatch')
    return {'valid': True, 'policy_version': VERSION, **summary, 'reference_frozen': True,
            'input_unchanged': True, 'reference_excluded_from_messages': True,
            'human_reviewed': False, 'prior_outputs_seen': True,
            'model_calls': 0, 'actor_calls': 0, 'repair_calls': 0, 'memory_commits': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = prepare(args.output.resolve()) if args.command == 'prepare' else verify(args.output.resolve())
    io.save(args.output/'validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
