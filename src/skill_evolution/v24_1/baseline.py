"""Prepare V24.1 from the approved, unstarted V24 no-review/workers-10 profile."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from .facts import require
from .storage import write_record

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001'
DRAFT = ROOT/'docs/methods/v24_1/draft_20261030_001'
PROMPTS = {'diagnosis': 'diagnosis_prompt', 'preconditioner': 'preconditioner_knowledge_only_prompt',
           'editor': 'editor_prompt', 'replay': 'replay_knowledge_only_prompt'}
ALLOWED_CHANGES = {'method.version', 'method.diagnosis_version', 'method.preconditioner_prompt',
                   'method.editor', 'method.replay_prompt_version',
                   'benchmark.adapter_version', 'benchmark.prompt_profile'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def differences(old, new, prefix=''):
    if isinstance(old, dict) and isinstance(new, dict):
        rows = []
        for key in sorted(set(old) | set(new)):
            path = f'{prefix}.{key}' if prefix else key
            if key not in old or key not in new:
                rows.append({'path': path, 'before': old.get(key), 'after': new.get(key)})
            else:
                rows.extend(differences(old[key], new[key], path))
        return rows
    return [] if old == new else [{'path': prefix, 'before': old, 'after': new}]


def audit():
    manifest = read(DRAFT/'source_manifest.json')
    review = read(DRAFT/'review_checks.json')
    require(manifest.get('revision') == 'review_02' and review['passed'], 'Approved draft review is missing')
    for name in ('campaign.json', 'source_contract.json'):
        path = SOURCE/'config'/name
        require(digest(path) == manifest['source_sha256'][str(path.relative_to(ROOT))],
                'Approved V24 baseline changed')
    config = read(SOURCE/'config/campaign.json')
    require(config['actor_max_workers'] == 10 and config['method']['knowledge_review'] == 'disabled_v1',
            'Expected workers-10/no-review baseline')
    installed = Path(__file__).parent/'benchmarks/alfworld/prompts/v23_5'
    for module, stem in PROMPTS.items():
        draft = DRAFT/'prompts'/f'{module}.md'
        require(digest(draft) == review['artifact_sha256'][f'prompts/{module}.md'], 'Reviewed draft changed')
        for suffix in ('', '_feedback'):
            require((installed/f'{stem}{suffix}.md').read_bytes() == draft.read_bytes(),
                    'Installed Prompt differs from approved draft')
    evidence = {'baseline': str(SOURCE.relative_to(ROOT)), 'version': 'v24.1',
                'source_files': manifest['source_sha256'], 'approved_prompts': {
                    m: digest(DRAFT/'prompts'/f'{m}.md') for m in PROMPTS}}
    return evidence, config


def resolved_config():
    from .benchmarks.alfworld.adapter import ALFWorldAdapter
    from .benchmark import using_benchmark
    from .config import method_config
    from .evolution import validate_config
    _, original = audit()
    value = deepcopy(original)
    value['method'] = method_config()
    adapter = ALFWorldAdapter()
    value['benchmark'] = deepcopy(adapter.identity)
    with using_benchmark(adapter):
        validate_config(value)
    rows = differences(original, value)
    require({row['path'] for row in rows} == ALLOWED_CHANGES, 'Unexpected V24.1 configuration change')
    return value, rows


def prepare(output):
    """Save configuration and snapshots only. Never initialize or execute a campaign."""
    from .benchmark import using_benchmark
    from .benchmarks.alfworld.adapter import ALFWorldAdapter
    from . import evolution
    evidence, original = audit()
    value, rows = resolved_config()
    # Validate frozen environment bytes without loading the environment or running tasks.
    for name, text in value['environment_files'].items():
        require(Path(name).read_bytes() == text.encode('utf-8'), 'Baseline environment file changed')
    with using_benchmark(ALFWorldAdapter()):
        source_contract = evolution.frozen_contract()
        runtime = evolution.runtime_snapshot(value)
        require(runtime == read(SOURCE/'config/runtime.json'), 'Installed runtime differs from baseline')
    output = Path(output).resolve()
    require(not output.exists(), 'Preparation requires a new directory')
    (output/'config').mkdir(parents=True)
    shutil.copytree(SOURCE/'data', output/'data')
    for name in ('budget.json', 'initial_baseline_reference.json'):
        shutil.copyfile(SOURCE/'config'/name, output/'config'/name)
    shutil.copyfile(SOURCE/'config/campaign.json', output/'config/source_config.json')
    write_record(output/'config/campaign.json', value)
    write_record(output/'config/source_contract.json', source_contract)
    write_record(output/'config/runtime.json', runtime)
    write_record(output/'alignment.json', {'baseline': evidence['baseline'], 'changes': rows,
        'all_other_config_fields_identical': True, 'initial_skill_and_memory': 'Initial Skill unchanged; start with empty Memory',
        'data_sha256': {str(p.relative_to(output)): digest(p) for p in sorted((output/'data').rglob('*')) if p.is_file()},
        'approved_prompts': evidence['approved_prompts']})
    preflight = {'status': 'passed', 'workers': value['actor_max_workers'],
        'knowledge_review': value['method']['knowledge_review'], 'enabled_modules': list(evolution.enabled_modules(value)),
        'batch_sizes': [len(batch) for batch in value['batches']],
        'environment_files_checked': len(value['environment_files']), 'runtime_matches_baseline': True,
        'model_requests': 0, 'environment_episodes': 0, 'campaign_present': False, 'automatic_test': False}
    write_record(output/'preflight.json', preflight)
    return {'experiment': str(output), **preflight}
