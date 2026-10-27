"""Fresh R06 Diagnosis followed by a frozen Plan / unchanged Memory handoff."""
from pathlib import Path
import json
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

SHARED = core.HERE
PREVIOUS = SHARED.with_name('semantic_generation_003')
core.HERE = Path(__file__).resolve().parent
SOURCE = core.ROOT / 'artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001'


def prepare():
    previous = core.read(PREVIOUS / 'config/freeze.json')
    for path, digest in previous['sha256'].items():
        assert core.sha(core.ROOT / path) == digest, path
    material = core.read(SOURCE / 'input.json')
    messages = core.diagnosis.messages_for(material)
    facts = core.old_diagnosis.diagnosis_input(material)
    assert facts == json.loads(core.read(SOURCE / 'messages.json')[1]['content'])
    assert json.loads(messages[1]['content']) == facts and 'memory' not in facts
    prior_case = core.read(PREVIOUS / 'config/cases/R06.json')
    assert material['background'] == prior_case['background']
    assert facts['parent'] == prior_case['payload']['parent']
    core.save(core.HERE / 'config/current_grouping.json', material)
    core.save(core.HERE / 'config/diagnosis_messages.json', messages)
    core.save(core.HERE / 'config/memory.json', prior_case['payload']['memory'])
    _, cfg = core.configuration()
    assert cfg == previous['call_config']
    paths = [core.HERE / 'run.py', core.HERE / 'PROTOCOL.md',
             *core.archive_glob(core.HERE / 'config', '*.json'),
             SOURCE / 'input.json', SOURCE / 'messages.json', SOURCE / 'prompt.md',
             PREVIOUS / 'config/freeze.json', PREVIOUS / 'config/cases/R06.json',
             SHARED / 'run.py', SHARED / 'audit.py']
    hashes = dict(previous['sha256'])
    hashes.update({str(p.relative_to(core.ROOT)): core.sha(p) for p in paths})
    core.save(core.HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'max_restarts': 3,
        'max_logical_calls': 2, 'max_http_attempts': 8,
        'scope': ['R06 diagnosis', 'R06 pc'], 'sha256': hashes})
    core.verify()
    print('Frozen identical R06 Diagnosis facts, original Memory, and current production prompts.')


def inputs(label, stage):
    assert label == 'R06' and stage in ('diagnosis', 'pc')
    if stage == 'diagnosis':
        material = core.read(core.HERE / 'config/current_grouping.json')
        messages = core.diagnosis.messages_for(material)
        assert messages == core.read(core.HERE / 'config/diagnosis_messages.json')
        return material, messages
    frozen = core.read(core.HERE / 'handoff/freeze.json')
    for path, digest in frozen['sha256'].items():
        assert core.sha(core.ROOT / path) == digest, path
    selected = core.load('R06', 'diagnosis')['diagnosis']
    assert selected == core.read(core.HERE / 'handoff/diagnosis.json')
    material = core.read(core.HERE / 'handoff/preconditioner_input.json')
    saved = {**core.read(core.HERE / 'config/current_grouping.json'), 'diagnosis': selected,
             'memory': core.read(core.HERE / 'config/memory.json')}
    assert material['payload'] == core.preconditioner_input(saved)
    assert material['background'] == saved['background']
    messages = core.pc_messages(material)
    assert messages == core.read(core.HERE / 'handoff/messages.json')
    return material, messages


core.inputs = inputs


def freeze_plan():
    core.verify()
    selected = core.load('R06', 'diagnosis')['diagnosis']
    if selected['decision'] != 'revise':
        print('Diagnosis has no Plan:', selected['decision'], '; no Preconditioner call.')
        return
    if (core.HERE / 'handoff/freeze.json').exists():
        inputs('R06', 'pc')
        print('Reused verified frozen Plan; no regeneration.')
        return
    saved = {**core.read(core.HERE / 'config/current_grouping.json'), 'diagnosis': selected,
             'memory': core.read(core.HERE / 'config/memory.json')}
    material = {'payload': core.preconditioner_input(saved), 'background': saved['background'],
                'kind': 'fresh_v23_4_diagnosis_on_same_R06_facts'}
    core.save(core.HERE / 'handoff/diagnosis.json', selected)
    core.save(core.HERE / 'handoff/preconditioner_input.json', material)
    core.save(core.HERE / 'handoff/messages.json', core.pc_messages(material))
    paths = [*core.archive_glob(core.HERE / 'handoff', '*.json'),
             *core.archive_glob(core.HERE / 'runs/R06_diagnosis', '*.json', recursive=True), core.HERE / 'config/memory.json']
    core.save(core.HERE / 'handoff/freeze.json', {
        'at': core.now(), 'diagnosis_source': 'runs/R06_diagnosis/selected.json',
        'selected_run_ids': [r['ref'] for r in material['payload']['runs']],
        'sha256': {str(p.relative_to(core.ROOT)): core.sha(p) for p in paths}})
    inputs('R06', 'pc')
    print('Frozen first valid Diagnosis Plan and original R06 Memory.')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'freeze-plan':
        freeze_plan()
    elif sys.argv[1] == 'audit':
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] <= 2 and result['http_attempts'] <= 8
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert sys.argv[1] == 'R06' and sys.argv[2] in ('diagnosis', 'pc')
        core.run(sys.argv[1], sys.argv[2])
