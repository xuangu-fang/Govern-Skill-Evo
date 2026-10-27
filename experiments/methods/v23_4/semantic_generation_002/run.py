"""Explicitly authorized R06 restart under the revised Prompt and validator."""
from pathlib import Path
import json
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

PREVIOUS = core.HERE
core.HERE = Path(__file__).resolve().parent


def prepare():
    core.prepare()
    # Only a newly created, not-yet-used freeze is completed here. Never rewrite
    # the previous study or reuse its failed attempt directories.
    assert core.read(core.HERE / 'config/cases/R06.json') == core.read(PREVIOUS / 'config/cases/R06.json')
    old_messages = core.read(PREVIOUS / 'config/messages/R06.json')
    messages = core.read(core.HERE / 'config/messages/R06.json')
    assert old_messages[1] == messages[1] and old_messages[0] != messages[0]
    frozen = core.read(core.HERE / 'config/freeze.json')
    assert frozen['call_config'] == core.read(PREVIOUS / 'config/freeze.json')['call_config']
    frozen.update(max_logical_calls=2, max_http_attempts=8,
                  scope=['R06 pc', 'R06 editor'], previous_study=str(PREVIOUS.relative_to(core.ROOT)))
    for path in (PREVIOUS / 'run.py', PREVIOUS / 'audit.py', PREVIOUS / 'config/freeze.json',
                 PREVIOUS / 'config/cases/R06.json', PREVIOUS / 'config/messages/R06.json'):
        frozen['sha256'][str(path.relative_to(core.ROOT))] = core.sha(path)
    (core.HERE / 'config/freeze.json').write_text(json.dumps(frozen, ensure_ascii=False, indent=2))
    core.verify()
    print('R06 unchanged; revised system prompt frozen; at most two stages / eight HTTP attempts.')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'audit':
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] <= 2 and result['http_attempts'] <= 8
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1] == 'R06' and sys.argv[2] in ('pc', 'editor')
        core.run(sys.argv[1], sys.argv[2])
