"""Verify the frozen control and CLI config loading without executing a campaign."""
from contextlib import ExitStack, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CONTROL = HERE / 'part1'
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from scripts.runs import run_v27_2_campaign as cli
from src.skill_evolution.v27_2 import config


def verify():
    frozen = (CONTROL / 'manifest.json').read_bytes()
    digest = sha256(frozen).hexdigest()
    assert digest == '813b54e967ba546d00b9ae40370478003a4c6ee03d028f67077fc562d3373cab'
    manifest = json.loads(frozen)
    cfg = config.DEFAULT_CONFIG.relative_to(ROOT)
    docs = Path('docs/methods/v27_2')
    modules = Path('src/skill_evolution/v27_2')
    revised = ('diagnosis', 'preconditioner')
    allowed = {cfg, docs / 'README.md', modules / '__init__.py'}
    for name in revised:
        allowed.update((modules / f'{name}.py', docs / 'prompts' / f'{name}.md'))
    for name, checksum in manifest['sha256'].items():
        original = (CONTROL / name).read_bytes()
        assert sha256(original).hexdigest() == checksum, name
        if Path(name) not in allowed:
            assert (ROOT / name).read_bytes() == original, name

    expected = json.loads((CONTROL / cfg).read_bytes())
    ids = expected['method']['prompts']
    assert ids == manifest['prompt_versions']
    for name in revised:
        old_id, ids[name] = ids[name], f'v27_2_lmb_{name}_v2'
        file = modules / f'{name}.py'
        assert (ROOT / file).read_bytes() == (CONTROL / file).read_bytes().replace(
            old_id.encode(), ids[name].encode())
    assert expected == json.loads((ROOT / cfg).read_bytes())
    assert ids == config.prompt_versions()

    rendered = config.render_prompts()
    for name, system in rendered.items():
        file = docs / 'prompts' / f'{name}.md'
        assert system.encode() == (ROOT / file).read_bytes()
        original = (CONTROL / file).read_text()
        assert (system != original) == (name in revised)
        if name in revised:
            boundary = f'\n## {("Exact output contract" if name == "preconditioner" else "Decisions and exact output")}'
            assert system.split(boundary, 1)[1] == original.split(boundary, 1)[1]
    assert rendered['diagnosis'].split('## Construct complete, scoped Updates')[0] == (
        CONTROL / docs / 'prompts/diagnosis.md').read_text().split('## Construct complete, scoped Updates')[0]
    boundary = '## LMB execution and evidence boundary'
    end = '## Frozen proposal and available input'
    def evidence_contract(s):
        return s.split(boundary, 1)[1].split(end, 1)[0]
    assert evidence_contract(rendered['preconditioner']) == evidence_contract(
        (CONTROL / docs / 'prompts/preconditioner.md').read_text())

    with TemporaryDirectory() as tmp, ExitStack() as stack:
        for obj, key in [(socket.socket, 'connect'), (socket.socket, 'connect_ex'),
                         (socket, 'create_connection'), (cli, 'read_credentials'),
                         (cli, 'run_training'), (cli, 'run_test'), (cli, 'prepare_test')]:
            stack.enter_context(patch.object(obj, key, side_effect=AssertionError(f'Unexpected: {key}')))
        campaign = Path(tmp) / 'absent'
        def preflight(path):
            with redirect_stdout(StringIO()) as stdout:
                cli.main(['train', str(campaign), '--config', str(path), '--validate-only'])
            return json.loads(stdout.getvalue())
        result = preflight(ROOT / cfg)
        assert result['status'] == 'valid' and result['method'] == manifest['method']
        assert result['batch_sizes'] == [10, 10, 10, 10, 10, 3]
        try:
            preflight(CONTROL / cfg)
        except ValueError as exc:
            if 'Configuration, method, prompts, contracts or frozen parameters differ' not in str(exc):
                raise
        else:
            raise AssertionError('Part 2 accepted the frozen part 1 config')
        assert not campaign.exists()

    return {'status': 'passed', 'scope': 'static integrity, runtime rendering and CLI validate-only',
            'control_manifest_sha256': digest, 'control_files_verified': len(manifest['sha256']),
            'prompt_ids': ids, 'rendered_sha256': {n: sha256(s.encode()).hexdigest() for n,s in rendered.items()},
            'preflight': result, 'part1_config_rejected_by_part2': True, 'campaign_created': False,
            'model_calls': 0, 'training_runs': 0, 'test_runs': 0, 'behavioral_trials': 0}


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Run offline verification without Python optimization (-O).')
    print(json.dumps(verify(), indent=2))
