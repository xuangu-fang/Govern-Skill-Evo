"""Current-version R05 continuation with exact archived Original inputs."""
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

PREVIOUS = core.HERE
core.HERE = Path(__file__).resolve().parent
ORIGINAL_INPUTS = core.inputs
CHANGED = {
    'src/skill_evolution/v23/facts.py',
    'src/skill_evolution/v23/memory.py',
    'src/skill_evolution/v23_4/update_patch.py',
    'src/skill_evolution/v23_4/preconditioner_prompt.md',
}
BUDGET = {'pc': 1_200_000, 'editor': 200_000}


def inputs(label, stage):
    assert label == 'R05' and stage in BUDGET
    material, messages = ORIGINAL_INPUTS(label, stage)
    assert len(json.dumps(messages, ensure_ascii=False)) <= BUDGET[stage]
    if stage == 'pc':
        assert messages == core.read(core.HERE / 'config/messages/R05.json')
    return material, messages


core.inputs = inputs


def prepare():
    old = core.read(PREVIOUS / 'config/freeze.json')
    changed = {p: {'before': h, 'after': core.sha(core.ROOT / p)}
               for p, h in old['sha256'].items() if core.sha(core.ROOT / p) != h}
    assert set(changed) == CHANGED, changed
    source = core.ROOT / 'experiments/methods/v23_3/p3a_first_live_comparison_001/runs/diagnosis'
    saved = core.load_saved(core.d233.load_diagnosis, source)
    memory_path = core.resolve(source.parents[1] / 'config/memory.json')
    saved['memory'] = core.read(memory_path)
    material = {'kind': 'real_development_archive', 'payload': core.preconditioner_input(saved),
                'background': saved['background'], 'source': str(source.relative_to(core.ROOT))}
    assert material == core.read(PREVIOUS / 'config/cases/R05.json')
    core.old_diagnosis.validate_diagnosis(saved['diagnosis'], material['payload'])
    messages = core.pc_messages(material)
    assert messages[1] == core.read(PREVIOUS / 'config/messages/R05.json')[1]
    assert messages[0] != core.read(PREVIOUS / 'config/messages/R05.json')[0]
    ids = [e['id'] for e in saved['memory']['entries']]
    assert ids == ['M1', 'M2', 'M3', 'M6', 'M7', 'M8', 'M9']
    core.save(core.HERE / 'config/cases/R05.json', material)
    core.save(core.HERE / 'config/messages/R05.json', messages)
    core.save(core.HERE / 'config/provenance.json', {
        'original_diagnosis_source': str(source.relative_to(core.ROOT)),
        'original_diagnosis_reloaded': True, 'exact_study_001_material_match': True,
        'user_message_unchanged': True, 'original_plan_reused': True,
        'selected_current_runs': [r['ref'] for r in material['payload']['runs']],
        'memory_ids': ids, 'changed_sources_since_study_001': changed,
        'input_chars': len(json.dumps(messages, ensure_ascii=False)),
        'max_input_chars': BUDGET, 'production_pc_default_input_chars': 100000,
        'adapter': 'independent experiment; not full production persisted lineage'})
    hashes = dict(old['sha256'])
    hashes.update({p: value['after'] for p, value in changed.items()})
    paths = [core.HERE / 'run.py', core.HERE / 'PROTOCOL.md', core.HERE / 'INPUT_REVIEW.md',
             *core.archive_glob(core.HERE / 'config', '*.json', recursive=True), PREVIOUS / 'config/freeze.json',
             PREVIOUS / 'audit.py', PREVIOUS / 'run.py', memory_path,
             *[p for p in core.archive_glob(source, '*', recursive=True) if p.is_file()]]
    hashes.update({str(p.relative_to(core.ROOT)): core.sha(p) for p in paths})
    _, cfg = core.configuration()
    assert cfg == old['call_config']
    core.save(core.HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'max_restarts': 3,
        'max_logical_calls': 2, 'max_http_attempts': 8,
        'scope': ['R05 pc', 'R05 editor'], 'sha256': hashes})
    core.verify(); inputs('R05', 'pc')
    print(json.dumps(core.read(core.HERE / 'config/provenance.json'), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['audit']:
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] <= 2 and result['http_attempts'] <= 8
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert len(sys.argv) == 3 and sys.argv[1] == 'R05' and sys.argv[2] in BUDGET
        core.run(sys.argv[1], sys.argv[2])
