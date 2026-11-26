"""Prepare/check the common OfficeQA environment; network and models forbidden.

python -m scripts.benchmarks.officeqa.align [--check]
Only input construction and local document tools run on real tasks. Synthetic
Actor loops are tested separately in tests/adapters/officeqa/test_aligned.py.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from .prepare import deny_network, NETWORK_ATTEMPTS, digest, write_or_check


def run(root, *, check=False):
    sys.addaudithook(deny_network)
    import openai
    def forbidden(*args, **kwargs):
        raise RuntimeError('No provider client may be initialized during offline acceptance')
    openai.OpenAI = openai.AzureOpenAI = forbidden
    from skilladam.benchmarks.officeqa import tool_runtime as adam_tools
    from skilladam.benchmarks.officeqa.rollout import build_messages
    from src.adapters.officeqa.data import Dataset, PROFILE, materialize_rows
    from src.adapters.officeqa.runtime import Runtime
    from src.adapters.officeqa.execution import EXECUTION_CONFIG
    from src.adapters.officeqa.bridges import SkillAdamAdapter, SkillOptAdapter, GovernActor
    from skillopt.envs.officeqa import rollout as opt_rollout
    opt_rollout.chat_target_messages = opt_rollout.run_target_exec = forbidden

    base = root / 'data/officeqa'
    prepared = base / 'prepared_v2'
    artifact = root / 'artifacts/benchmarks/officeqa/offline_v2'
    downloaded = json.loads((base / 'download_manifest.json').read_text())
    for entry in downloaded['files']:
        path = base / entry['path']
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Original download changed: {entry["path"]}')
    profile = json.loads((root / 'external/SkillAdam/skilladam/data/profiles/officeqa_main_results.json').read_text())
    if profile['source_revision'] != downloaded['revision']:
        raise ValueError('Dataset revision differs')
    rows, changes, originals = materialize_rows(base / 'raw/officeqa_full.csv', profile)
    if {c['task_id'] for c in changes} != {'UID0057', 'UID0077', 'UID0124', 'UID0215'}:
        raise ValueError('Unexpected source mapping changes')
    def store(path, value):
        write_or_check(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n', check)
    for split, items in rows.items():
        if len(items) != {'train': 50, 'val': 24, 'test': 172}[split]:
            raise ValueError('Split counts differ')
        previous = json.loads((base / f'prepared_v1/source_aligned/{split}/items.json').read_text())
        for old, new in zip(previous, items):
            for key in ('id', 'question', 'ground_truth', 'answers', 'source_files', 'source_docs'):
                if old[key] != new[key]:
                    raise ValueError(f'Audited mapping or task changed: {new["id"]}/{key}')
        store(prepared / split / 'items.json', items)
    store(prepared / 'source_rows.json', originals)
    store(prepared / 'mapping_changes.json', changes)
    manifest = {'profile': PROFILE, 'dataset_revision': downloaded['revision'], 'splits': profile['splits'],
                'parsed_root': str(base / 'raw/treasury_bulletins_parsed'),
                'source_csv_sha256': digest(base / 'raw/officeqa_full.csv')}
    store(prepared / 'manifest.json', manifest)
    dataset, runtime = Dataset(prepared), Runtime(manifest['parsed_root'])
    adam = SkillAdamAdapter(dataset)
    class NoTransport:
        def metadata(self):
            # Synthetic construction value, never persisted as a method budget.
            return {'max_completion_tokens': 1, 'model': 'offline-input-check'}
        __call__ = staticmethod(forbidden)
    opt = SkillOptAdapter(dataset, runtime, NoTransport())
    govern = GovernActor(dataset, runtime, NoTransport())
    opt.setup({})
    audits = []
    for split, disk in [('train', 'train'), ('validation', 'val'), ('test', 'test')]:
        cases = adam.load_cases(split)
        opt_items = opt.get_dataloader().load_split_items(str(prepared / disk))
        if [i['id'] for i in opt_items] != [c.case_id for c in cases]:
            raise ValueError('Method loader IDs differ')
        for case, opt_item in zip(cases, opt_items):
            # Exercise each method's own task loading boundary, without rollout.
            govern_case = govern.dataset.case(case.case_id)
            opt_case = opt.dataset.case(opt_item['id'])
            if case != govern_case or case != opt_case:
                raise ValueError('Method case views differ')
            for key in ('question', 'source_files', 'source_docs'):
                if opt_item[key] != case.payload[key]:
                    raise ValueError('SkillOpt loaded task differs')
            messages, allowed = runtime.prepare(case, None)
            if '## Skill' in messages[0]['content']:
                raise ValueError('Unexpected initial Skill or Stage0 output')
            adam_request = adam.build_rollout_request(case, method='skilladam', split=split, skill=None, seed=42)
            expected = adam_tools.build_oracle_parsed_pages_context(case.payload['source_files'],
                case.payload['source_docs'], runtime.roots)
            if messages[-1]['content'] != adam_request.metadata['messages'][-1]['content'] + '\n\n## Oracle Parsed Pages\n' + expected:
                raise ValueError('Input layout differs from SkillAdam')
            refs = adam_tools._iter_oracle_refs(case.payload['source_files'], case.payload['source_docs'])
            for name, page, _ in refs:
                path = adam_tools._locate_parsed_json(name, runtime.roots)
                if not adam_tools._render_parsed_page(str(path), page):
                    raise ValueError('Missing page')
            _, files = adam_tools.run_tool('glob', {'pattern': '*.txt'}, allowed_roots=runtime.roots, allowed_files=allowed)
            if set(Path(p).name for p in files.splitlines()) != set(allowed):
                raise ValueError('Tool scope differs')
            for filename in files.splitlines():
                text = Path(filename).read_text()
                _, excerpt = adam_tools.run_tool('read', {'path': filename}, allowed_roots=runtime.roots, allowed_files=allowed)
                if excerpt != ''.join(text.splitlines(keepends=True)[:80])[:4000]:
                    raise ValueError('Read limits differ')
                needle = next(line.strip() for line in text.splitlines() if line.strip())[:24]
                _, found = adam_tools.run_tool('grep', {'path': filename, 'pattern': needle.swapcase()},
                                              allowed_roots=runtime.roots, allowed_files=allowed)
                if found == '[no matches]':
                    raise ValueError('Literal/case-insensitive search differs')
            _, denied = adam_tools.run_tool('read', {'path': str(base/'raw/officeqa_full.csv')},
                                           allowed_roots=runtime.roots, allowed_files=allowed)
            if 'path not allowed' not in denied:
                raise ValueError('Answers accessible through tools')
            audits.append({'id': case.case_id, 'split': split, 'page_refs': len(refs),
                'user_sha256': hashlib.sha256(messages[-1]['content'].encode()).hexdigest(),
                'system_sha256': hashlib.sha256(messages[0]['content'].encode()).hexdigest(),
                'oracle_characters': len(expected), 'visible_page_headers': expected.count('### '),
                'truncated': '[... oracle context truncated ...]' in expected})
    # Pin only consumed upstream modules; do not claim the entire checkout is pristine.
    installed = {}
    for name, module in sorted(sys.modules.copy().items()):
        if not (name.startswith('skilladam.') or name.startswith('skillopt.')) or not getattr(module, '__file__', None):
            continue
        local = root / 'external' / ('SkillAdam' if name.startswith('skilladam.') else 'SkillOpt')
        relative = Path(*name.split('.'))
        relative = relative/'__init__.py' if Path(module.__file__).name == '__init__.py' else relative.with_suffix('.py')
        if not (local / relative).is_file() or digest(Path(module.__file__)) != digest(local / relative):
            raise ValueError(f'Installed upstream source drift: {name}')
        installed[name] = digest(Path(module.__file__))
    configuration = {'profile': PROFILE, 'prepared_root': str(prepared), 'parsed_root': manifest['parsed_root'],
        **EXECUTION_CONFIG,
        'base_runtime': 'SkillAdam b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1',
        'url_splitting': 'independent_urls', 'source_mapping': 'source_aligned',
        'max_model_rounds': 24, 'max_tool_calls_per_turn': None, 'max_total_tool_calls': None,
        'max_completion_tokens': 'required_per_method_no_shared_default',
        'stage0_enabled': False, 'initial_skill': 'explicit_caller_text_or_none',
        'methods': {owner: {'entrypoint': f'src.adapters.officeqa.bridges:{entry}', 'max_completion_tokens': None}
            for owner, entry in [('govern', 'GovernActor'), ('skillopt', 'SkillOptAdapter'), ('skilladam', 'SkillAdamBackend')]},
        'training_enabled': False, 'model_calls_authorized': False}
    store(prepared / 'execution.json', configuration)
    implementation = {str(p.relative_to(root)): digest(p)
        for folder in ('src/adapters/officeqa', 'scripts/benchmarks/officeqa')
        for p in sorted((root/folder).glob('*.py'))}
    report = {'status': 'passed', 'profile': PROFILE,
        'scope': 'all real-task input/tool checks; no real-task rollout, model, or optimization execution',
        'environment': sys.prefix, 'python': sys.version.split()[0],
        'packages': {d.metadata['Name']: d.version for d in sorted(importlib.metadata.distributions(), key=lambda d:d.metadata['Name'].lower())},
        'verified_original_files': len(downloaded['files']),
        'counts': {s: len(items) for s, items in rows.items()},
        'page_refs': sum(a['page_refs'] for a in audits), 'mapping_changes': changes,
        'configuration': configuration, 'page_audits': audits,
        'upstream_source_sha256': installed, 'implementation_sha256': implementation,
        'generated_sha256': {str(p.relative_to(prepared)): digest(p) for p in sorted(prepared.rglob('*.json'))},
        'network_attempts': NETWORK_ATTEMPTS, 'model_calls': 0, 'real_task_rollouts': 0,
        'stage0_calls': 0, 'optimization_runs': 0,
        'known_issues': ['UID0057 retains the original October link despite January-only question wording.',
            'UID0077 asks CY but source annual rows are labeled fiscal year.',
            'UID0057 oracle context is still truncated at the common native 80000-character limit.',
            'Govern Actor boundary is ready; V25 diagnosis/facts/Gate and experiment launchers are not changed.',
            'Live model transport and method-specific output budgets are not configured or tested.']}
    store(artifact / 'report.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'counts', 'page_refs', 'model_calls', 'real_task_rollouts', 'stage0_calls')}))
    print('Report:', artifact/'report.json')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[3], check=args.check)
