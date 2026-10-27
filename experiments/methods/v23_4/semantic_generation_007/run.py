"""Editor-only continuation of the frozen R05 Effective Plan from study 006."""
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

PREVIOUS = core.HERE.with_name('semantic_generation_006')
core.HERE = Path(__file__).resolve().parent
original_load = core.load


def upstream():
    root = PREVIOUS / 'runs/R05_pc'
    n = core.read(root / 'selected.json')['attempt']
    attempt = root / f'attempt_{n:03}'
    response = core.read(attempt / 'response.json')
    assert response['finish_reason'] == 'stop'
    parsed = core.parse_json_response(response['content'])
    assert parsed == core.read(attempt / 'parsed.json')
    material = core.read(root / 'material.json')
    assert material == core.read(PREVIOUS / 'config/cases/R05.json')
    result = core.validate('pc', parsed, material)
    assert result == core.read(attempt / 'result.json')
    assert result['effective_plan'] is not None
    return material, result


def inputs(label, stage):
    assert (label, stage) == ('R05', 'editor')
    source, result = upstream()
    material = {'parent': source['payload']['parent'], 'plan': result['effective_plan'],
                'background': source['background']}
    messages = [
        {'role': 'system', 'content': core.render_prompt(core.old_editor.PROMPT_PATH.read_text(), material['background'])},
        {'role': 'user', 'content': json.dumps({k: material[k] for k in ('parent', 'plan')}, ensure_ascii=False, separators=(',', ':'))}]
    assert material == core.read(core.HERE / 'config/material.json')
    assert messages == core.read(core.HERE / 'config/messages.json')
    assert len(json.dumps(messages, ensure_ascii=False)) <= 200000
    return material, messages


def load(label, stage):
    if (label, stage) == ('R05', 'pc'):
        return upstream()[1]
    assert (label, stage) == ('R05', 'editor')
    return original_load(label, stage)


core.inputs = inputs
core.load = load


def prepare():
    previous = core.read(PREVIOUS / 'config/freeze.json')
    hashes = dict(previous['sha256'])
    hashes.update(core.read(PREVIOUS / 'handoff/freeze.json')['sha256'])
    prompt_path = 'src/skill_evolution/v23/editor_prompt.md'
    preimage = core.HERE / 'baseline_sources' / prompt_path
    for path, digest in hashes.items():
        actual = preimage if path == prompt_path else core.ROOT / path
        assert core.sha(actual) == digest, path
    anchor = 'The resulting Skill must preserve the intended strategies, triggering conditions, scope, strength, dependencies, exceptions, and preservation boundaries of all effective Updates.'
    addition = "A rule's scope depends on both its wording and its placement within the Skill, including section headings and nesting. Preserve each Effective Update's intended scope by choosing an appropriate location or making minimal structural adjustments when necessary."
    before = preimage.read_text()
    assert before.count(anchor) == 1
    assert core.old_editor.PROMPT_PATH.read_text() == before.replace(anchor, anchor + '\n\n' + addition)
    hashes[prompt_path] = core.sha(core.old_editor.PROMPT_PATH)
    source, result = upstream()
    material = {'parent': source['payload']['parent'], 'plan': result['effective_plan'],
                'background': source['background']}
    messages = [
        {'role': 'system', 'content': core.render_prompt(core.old_editor.PROMPT_PATH.read_text(), material['background'])},
        {'role': 'user', 'content': json.dumps({k: material[k] for k in ('parent', 'plan')}, ensure_ascii=False, separators=(',', ':'))}]
    assert material == core.read(PREVIOUS / 'runs/R05_editor/material.json')
    prior_messages = core.read(PREVIOUS / 'runs/R05_editor/messages.json')
    assert messages[1] == prior_messages[1] and messages[0] != prior_messages[0]
    core.save(core.HERE / 'config/material.json', material)
    core.save(core.HERE / 'config/messages.json', messages)
    _, cfg = core.configuration()
    assert cfg == previous['call_config']
    paths = [core.HERE / 'run.py', core.HERE / 'PROTOCOL.md', preimage,
             core.HERE / 'baseline_sources/manifest.json',
             *core.archive_glob(PREVIOUS / 'runs/R05_editor', '*.json', recursive=True),
             *core.archive_glob(core.HERE / 'config', '*.json'),
             PREVIOUS / 'config/freeze.json', PREVIOUS / 'handoff/freeze.json',
             *core.archive_glob(PREVIOUS / 'runs/R05_pc', '*.json', recursive=True)]
    hashes.update({str(p.relative_to(core.ROOT)): core.sha(p) for p in paths})
    core.save(core.HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'max_restarts': 3,
        'max_logical_calls': 1, 'max_http_attempts': 4,
        'scope': ['R05 editor'], 'only_source_change': prompt_path, 'sha256': hashes})
    core.verify()
    inputs('R05', 'editor')
    print('Frozen unchanged Parent, study 006 Effective Plan and production Editor prompt.')


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['audit']:
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] == 1 and result['http_attempts'] <= 4
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1:] == ['R05', 'editor']
        core.run('R05', 'editor')
