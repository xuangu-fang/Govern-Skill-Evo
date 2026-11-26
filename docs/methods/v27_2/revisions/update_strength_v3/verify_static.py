"""Read-only control integrity, one-paragraph diff, and prompt binding check."""
import json
import sys
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CONTROL = HERE / 'control'
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from src.skill_evolution.v27_2 import config


def verify():
    manifest_bytes = (CONTROL / 'manifest.json').read_bytes()
    assert sha256(manifest_bytes).hexdigest() == '97c12ea80a05d01c75084270fd1f1fae57d8419ba1aa45cd9155d66f1e7b9cbf'
    manifest = json.loads(manifest_bytes)
    docs = Path('docs/methods/v27_2')
    prompt = docs / 'prompts/preconditioner.md'
    binding = Path('src/skill_evolution/v27_2/preconditioner.py')
    cfg = config.DEFAULT_CONFIG.relative_to(ROOT)
    old, new = b'v27_2_lmb_preconditioner_v2', b'v27_2_lmb_preconditioner_v3'
    for name, digest in manifest['sha256'].items():
        path = Path(name)
        before = (CONTROL / path).read_bytes()
        after = (ROOT / path).read_bytes()
        assert sha256(before).hexdigest() == digest, name
        if path == prompt:
            a, b = before.split(b'\n\n'), after.split(b'\n\n')
            assert len(a) == len(b)
            (index,) = [i for i in range(len(a)) if a[i] != b[i]]
            assert a[index].startswith(b'Match the proposed procedure and its degree of obligation')
            assert sha256(b[index]).hexdigest() == '742f5fe8bfe6e919ada921cf4ce09ff212600c01bbaf7421c2d2a4a98212a229'
        elif path in (binding, cfg):
            assert before.count(old) == 1 and after == before.replace(old, new), name
        elif path != docs / 'README.md':
            assert after == before, name
    ids = {**manifest['prompt_versions'], 'preconditioner': new.decode()}
    active = json.loads(config.DEFAULT_CONFIG.read_bytes())
    assert active['method'] == config.method_config() and config.prompt_versions() == ids
    rendered = config.render_prompts()
    assert set(rendered) == set(ids)
    for module, text in rendered.items():
        assert text.encode() == (ROOT / docs / 'prompts' / f'{module}.md').read_bytes()
    return {'status': 'passed', 'scope': 'static checks only',
            'verified_control_files': len(manifest['sha256']), 'control_manifest_sha256': sha256(manifest_bytes).hexdigest(),
            'changed_prompt_paragraphs': 1, 'approved_paragraph_sha256': '742f5fe8bfe6e919ada921cf4ce09ff212600c01bbaf7421c2d2a4a98212a229',
            'prompt_versions': ids, 'rendered_preconditioner_sha256': sha256(rendered['preconditioner'].encode()).hexdigest()}


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Run static verification without -O')
    print(json.dumps(verify(), indent=2))
