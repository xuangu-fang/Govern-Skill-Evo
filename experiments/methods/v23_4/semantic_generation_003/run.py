"""One R06 Preconditioner generation after the user-specified consistency wording."""
from pathlib import Path
import json
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

SHARED = core.HERE
PREVIOUS = SHARED.with_name('semantic_generation_002')
core.HERE = Path(__file__).resolve().parent


def prepare():
    core.prepare()
    assert core.read(core.HERE / 'config/cases/R06.json') == core.read(PREVIOUS / 'config/cases/R06.json')
    old_messages = core.read(PREVIOUS / 'config/messages/R06.json')
    messages = core.read(core.HERE / 'config/messages/R06.json')
    assert old_messages[1] == messages[1] and old_messages[0] != messages[0]
    frozen = core.read(core.HERE / 'config/freeze.json')
    previous = core.read(PREVIOUS / 'config/freeze.json')
    assert frozen['call_config'] == previous['call_config']
    changed = [p for p, h in previous['sha256'].items() if core.sha(core.ROOT / p) != h]
    assert changed == ['src/skill_evolution/v23_4/preconditioner_prompt.md'], changed
    frozen.update(max_logical_calls=1, max_http_attempts=4, scope=['R06 pc'],
                  previous_study=str(PREVIOUS.relative_to(core.ROOT)), changed_source_paths=changed)
    for path in (SHARED / 'run.py', SHARED / 'audit.py', PREVIOUS / 'config/freeze.json',
                 PREVIOUS / 'config/cases/R06.json', PREVIOUS / 'config/messages/R06.json'):
        frozen['sha256'][str(path.relative_to(core.ROOT))] = core.sha(path)
    (core.HERE / 'config/freeze.json').write_text(json.dumps(frozen, ensure_ascii=False, indent=2))
    core.verify()
    print('Same R06 input and call configuration; only the consistency Prompt changed.')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'audit':
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] <= 1 and result['http_attempts'] <= 4
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1:] == ['R06', 'pc']
        core.run('R06', 'pc')
