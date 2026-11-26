"""Frozen inputs and an isolated, pinned SkillOpt source tree."""
from __future__ import annotations

import difflib
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

from src.skill_evolution.shared.experiment_paths import resolve_experiment_path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '7da46ae693ee0329b80225c0128a37d65db10e9e'
SOURCE = ROOT / 'external/SkillOpt'
DEFAULT = ROOT / 'experiments/baselines/skillopt_alfworld_native_best_only_20261030_001'
ADAM = ROOT / 'experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config'
ADAM_TEST = ROOT / 'artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134'
V24 = ROOT / 'experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/campaign.json'
SPLITS = ROOT / 'benchmarks/alfworld/editions/skillopt_39_18_134'
PYTHON = '/Users/didi/miniforge3/envs/skillopt/bin/python'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def best_only_trainer(source):
    """Only change evaluation policy; optimization and final Selection stay native."""
    def guard(text, first, last, expression):
        start, end = text.index(first), text.index(last)
        block = text[start:end]
        return text[:start] + '            if ' + expression + ':\n' + ''.join(
            '    ' + line if line.strip() else line for line in block.splitlines(True)) + text[end:]

    text = guard(source, '            # Baseline: S_0 on test set',
                 '            # Best skill on test set', 'cfg.get("eval_initial_skill", True)')
    text = guard(text, '            # Final skill (last skill in trajectory)',
                 '            # Comparison', 'cfg.get("eval_final_skill", True)')
    text = guard(text, '            # Comparison',
                 '        # ── Global summary', 'baseline_test_hard is not None')
    text = text.replace('if test_hard is not None\n',
                        'if test_hard is not None and baseline_test_hard is not None\n')
    text = text.replace('if final_test_hard is not None\n',
                        'if final_test_hard is not None and baseline_test_hard is not None\n')
    marker = '                print(f"\\n  [final skill val FAILED: {_e!r}]")\n'
    require(text.count(marker) == 1, 'Pinned final Selection branch changed')
    text = text.replace(marker, marker + '                if cfg.get("require_final_selection", False):\n                    raise\n')
    marker = '            "baseline_test_hard": baseline_test_hard,\n'
    require(text.count(marker) == 1, 'Pinned summary changed')
    text = text.replace(marker, '            "test_roles": ["best"] if not cfg.get("eval_initial_skill", True) and not cfg.get("eval_final_skill", True) else ["native"],\n' + marker)
    return text


def select_upstream(root):
    upstream = Path(root).resolve() / 'upstream'
    for name, module in list(sys.modules.items()):
        if name == 'skillopt' or name.startswith('skillopt.'):
            path = getattr(module, '__file__', None)
            require(path is None or Path(path).resolve().is_relative_to(upstream),
                    'Another SkillOpt source is already imported; use a fresh process')
    sys.path.insert(0, str(upstream))


def native_config(root):
    select_upstream(root)
    from skillopt.config import flatten_config, load_config
    root = Path(root).resolve()
    cfg = flatten_config(load_config(str(root / 'upstream/configs/alfworld/default.yaml')))
    cfg.update(model_backend='openai_compatible', optimizer_backend='openai_compatible',
               target_backend='openai_compatible', optimizer_model='deepseek-flash',
               target_model='deepseek-flash', workers=10, max_api_workers=10,
               slow_update_gate_with_selection=True, skill_init=str(root / 'initial_skill.md'),
               split_dir=str(root / 'splits'), out_root=str(root / 'campaign'),
               eval_test=True, eval_initial_skill=False, eval_final_skill=False,
               require_final_selection=True)
    return cfg


def actor_runtime(python):
    return json.loads(subprocess.check_output([python, '-B', '-c',
        'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"packages":'
        '{d.metadata["Name"]:d.version for d in m.distributions()}}))'], text=True))


def optimizer_runtime():
    return {'python': sys.version, 'executable': sys.executable,
            'packages': {n: importlib.metadata.version(n) for n in ('openai', 'httpx', 'PyYAML')}}


def reference_actor():
    old = read(ADAM / 'actor.json')
    # Extract Actor fields only. In particular, never inherit optimizer_request_attempts.
    keys = ('python', 'environment_root', 'model', 'base_url', 'max_steps', 'workers',
            'history_length', 'environment_seed', 'request_attempts', 'strict_response',
            'retry_invalid_actions', 'action_feedback', 'skill_injection', 'output_format', 'call_config')
    return {k: old[k] for k in keys}


def validate_alignment(actor, campaign):
    fields = {'python': 'actor_python', 'environment_root': 'environment_root',
              'model': 'actor_model', 'base_url': 'actor_base_url', 'max_steps': 'max_steps',
              'workers': 'actor_max_workers', 'request_attempts': 'actor_request_attempts',
              'retry_invalid_actions': 'actor_retry_invalid_actions', 'action_feedback': 'actor_action_feedback',
              'skill_injection': 'actor_skill_injection', 'output_format': 'actor_output_format',
              'call_config': 'call_config'}
    for key, reference in fields.items():
        require(actor[key] == campaign[reference], 'Completed Actor mismatch: ' + key)
    require(actor['strict_response'] and actor['history_length'] == 2 and actor['environment_seed'] == 42,
            'Actor execution protocol changed')
    require(actor['request_attempts'] == 6 and actor['workers'] == 10 and actor['max_steps'] == 50,
            'Actor budgets changed')
    # Validate against the completed experiment, not merely today's working tree.
    frozen = read(ADAM / 'manifest.json')['files']
    for path, expected in frozen.items():
        if '/src/adapters/alfworld/' in path:
            require(sha(path) == expected, 'Completed Actor source drift: ' + path)
    require((ADAM / 'initial_skill.md').read_text() == campaign['initial_skill']['text'], 'Initial Skills differ')


def prepare(root):
    root = Path(root).resolve()
    require(sys.executable == PYTHON, 'Use the pinned SkillOpt Python')
    require(not root.exists(), 'Preparation requires a new directory')
    actor, campaign = reference_actor(), read(V24)
    validate_alignment(actor, campaign)
    require(actor_runtime(actor['python']) == read(ADAM / 'actor_runtime.json'), 'Completed Actor runtime drift')
    root.mkdir(parents=True)
    raw = subprocess.check_output(['git', '-C', str(SOURCE), 'archive', COMMIT,
                                   'skillopt', 'configs', 'LICENSE', 'data/alfworld_path_split'])
    original = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            require(member.isfile() and '..' not in Path(member.name).parts and not Path(member.name).is_absolute(), 'Unsafe archive member')
            content = archive.extractfile(member).read()
            path = root / 'upstream' / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            original[member.name] = hashlib.sha256(content).hexdigest()
    trainer = root / 'upstream/skillopt/engine/trainer.py'
    before = trainer.read_text()
    after = best_only_trainer(before)
    trainer.write_text(after)
    (root / 'best_only.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile='a/skillopt/engine/trainer.py', tofile='b/skillopt/engine/trainer.py')))
    write(root / 'upstream_source.json', {'repository': 'https://github.com/microsoft/SkillOpt',
          'commit': COMMIT, 'original_files': original, 'modified_files': ['skillopt/engine/trainer.py']})
    write(root / 'actor.json', actor)
    write(root / 'actor_runtime.json', read(ADAM / 'actor_runtime.json'))
    (root / 'initial_skill.md').write_bytes((ADAM / 'initial_skill.md').read_bytes())
    for split in ('train', 'val', 'test'):
        content = (ADAM / f'splits/{split}/items.json').read_bytes()
        require(json.loads(content) == read(root / f'upstream/data/alfworld_path_split/{split}/items.json') == read(SPLITS / split / 'items.json'), 'Split mismatch')
        target = root / f'splits/{split}/items.json'
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
    cfg = native_config(root)
    write(root / 'skillopt.json', cfg)
    write(root / 'optimizer.json', {'model': 'deepseek-flash', 'base_url': 'https://api.deepseek.com',
          'temperature': 1, 'thinking': {'type': 'enabled'}, 'reasoning_effort': 'medium', 'stream': False,
          'timeout_seconds': 300, 'max_tokens': 64000, 'retry_policy': 'upstream_callsite_and_sdk_defaults',
          'api_key_env': 'OPENAI_API_KEY'})
    write(root / 'test_plan.json', {'roles': ['best'], 'task_count': 134,
          'initial_test': False, 'final_test': False, 'final_selection': True,
          'selection_used_for_best': True, 'test_used_for_selection': False})
    inputs = [V24, ADAM / 'actor.json', ADAM / 'actor_runtime.json', ADAM / 'initial_skill.md', ADAM / 'manifest.json']
    inputs += [ADAM / f'splits/{s}/items.json' for s in ('train', 'val', 'test')]
    inputs += [p for base in (ROOT / 'src/adapters/alfworld', ROOT / 'src/skill_evolution/v24_1/benchmarks/alfworld', SPLITS,
                             ROOT / 'src/skillopt_alfworld_native') for p in base.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts]
    inputs += [ROOT / 'scripts/runs/run_skillopt_alfworld_native.py',
               ROOT / 'tests/adapters/alfworld/test_skillopt_native.py']
    env_files = {}
    for path, text in campaign['environment_files'].items():
        require(Path(path).read_text() == text, 'Completed environment drift: ' + path)
        env_files[path] = sha(path)
    inputs += [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    write(root / 'manifest.json', {'canonical_layout': True, 'files': {str(p): sha(p) for p in sorted(set(inputs))},
          'environment_files': env_files, 'optimizer_runtime': optimizer_runtime()})
    report = check(root)
    write(root / 'preflight.json', report)
    return report


def check(root):
    root = Path(root).resolve()
    manifest = read(root / 'manifest.json')
    for section in ('files', 'environment_files'):
        for p, expected in manifest[section].items():
            source = resolve_experiment_path(p)
            if not manifest.get('canonical_layout') and source in (
                Path(__file__).resolve(), ROOT / 'tests/adapters/alfworld/test_skillopt_native.py'
            ):
                source = DEFAULT / 'configuration_revisions/before_native_retry_layout' / source.relative_to(ROOT)
            require(source.is_file() and sha(source) == expected, 'Frozen input changed: ' + p)
    require(optimizer_runtime() == manifest['optimizer_runtime'], 'Optimizer runtime drift')
    actor = read(root / 'actor.json')
    require(actor == reference_actor(), 'Actor config drift')
    validate_alignment(actor, read(V24))
    require(actor_runtime(actor['python']) == read(root / 'actor_runtime.json'), 'Actor runtime drift')
    cfg = read(root / 'skillopt.json')
    require(cfg == native_config(root), 'Unexpected native optimizer override')
    from .actor import build_adapter
    adapter = build_adapter(root)
    adapter.setup(cfg)
    loader = adapter.get_dataloader()
    counts = {s: len(loader.get_split_items(s)) for s in ('train', 'val', 'test')}
    require(counts == {'train': 39, 'val': 18, 'test': 134}, 'Split size drift')
    schedule = [loader.plan_train_epoch(epoch=e, steps_per_epoch=1, accumulation=1,
                batch_size=40, seed=42) for e in range(1, 5)]
    require(all(len(b) == 1 and b[0].batch_size == 39 for b in schedule), 'Native schedule drift')
    for kind in ('error', 'success'):
        actual = getattr(adapter, f'get_{kind}_minibatch_prompt')()
        expected = (root / f'upstream/skillopt/envs/alfworld/prompts/analyst_{kind}.md').read_text()
        require(actual == expected, 'ALFWorld prompt fallback detected')
    return {'status': 'offline_checks_passed', 'upstream_commit': COMMIT, 'split_counts': counts,
            'ordinary_updates': 4, 'test_roles': ['best'], 'actor_request_attempts': 6,
            'optimizer_retry_policy': 'upstream_callsite_and_sdk_defaults',
            'slow_update_gate_with_selection': True, 'model_requests': 0, 'environment_episodes': 0,
            'campaign_exists': (root / 'campaign').exists()}
