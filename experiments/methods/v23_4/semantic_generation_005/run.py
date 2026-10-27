"""Editor-only continuation of the frozen R06 Effective Plan from study 004."""
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

PREVIOUS = core.HERE.with_name('semantic_generation_004')
core.HERE = Path(__file__).resolve().parent
original_load = core.load


def upstream():
    root = PREVIOUS / 'runs/R06_pc'
    n = core.read(root / 'selected.json')['attempt']
    attempt = root / f'attempt_{n:03}'
    response = core.read(attempt / 'response.json')
    assert response['finish_reason'] == 'stop'
    parsed = core.parse_json_response(response['content'])
    assert parsed == core.read(attempt / 'parsed.json')
    material = core.read(root / 'material.json')
    assert material == core.read(PREVIOUS / 'handoff/preconditioner_input.json')
    result = core.validate('pc', parsed, material)
    assert result == core.read(attempt / 'result.json')
    assert result['effective_plan'] is not None
    return material, result


def inputs(label, stage):
    assert (label, stage) == ('R06', 'editor')
    source, result = upstream()
    material = {'parent': source['payload']['parent'], 'plan': result['effective_plan'],
                'background': source['background']}
    messages = [
        {'role': 'system', 'content': core.render_prompt(core.old_editor.PROMPT_PATH.read_text(), material['background'])},
        {'role': 'user', 'content': json.dumps({k: material[k] for k in ('parent', 'plan')}, ensure_ascii=False, separators=(',', ':'))}]
    assert material == core.read(core.HERE / 'config/material.json')
    assert messages == core.read(core.HERE / 'config/messages.json')
    return material, messages


def load(label, stage):
    if (label, stage) == ('R06', 'pc'):
        return upstream()[1]
    assert (label, stage) == ('R06', 'editor')
    return original_load(label, stage)


core.inputs = inputs
core.load = load


def prepare():
    previous = core.read(PREVIOUS / 'config/freeze.json')
    hashes = dict(previous['sha256'])
    hashes.update(core.read(PREVIOUS / 'handoff/freeze.json')['sha256'])
    for path, digest in hashes.items():
        assert core.sha(core.ROOT / path) == digest, path
    source, result = upstream()
    material = {'parent': source['payload']['parent'], 'plan': result['effective_plan'],
                'background': source['background']}
    messages = [
        {'role': 'system', 'content': core.render_prompt(core.old_editor.PROMPT_PATH.read_text(), material['background'])},
        {'role': 'user', 'content': json.dumps({k: material[k] for k in ('parent', 'plan')}, ensure_ascii=False, separators=(',', ':'))}]
    core.save(core.HERE / 'config/material.json', material)
    core.save(core.HERE / 'config/messages.json', messages)
    _, cfg = core.configuration()
    assert cfg == previous['call_config']
    paths = [core.HERE / 'run.py', core.HERE / 'PROTOCOL.md',
             *core.archive_glob(core.HERE / 'config', '*.json'),
             PREVIOUS / 'config/freeze.json', PREVIOUS / 'handoff/freeze.json',
             *core.archive_glob(PREVIOUS / 'runs/R06_pc', '*.json', recursive=True)]
    hashes.update({str(p.relative_to(core.ROOT)): core.sha(p) for p in paths})
    core.save(core.HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'max_restarts': 3,
        'max_logical_calls': 1, 'max_http_attempts': 4,
        'scope': ['R06 editor'], 'sha256': hashes})
    core.verify()
    inputs('R06', 'editor')
    print('Frozen unchanged Parent, study 004 Effective Plan and production Editor prompt.')


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['audit']:
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] == 1 and result['http_attempts'] <= 4
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1:] == ['R06', 'editor']
        core.run('R06', 'editor')
