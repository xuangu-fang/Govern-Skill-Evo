from hashlib import sha256

import pytest

from scripts.runs.v24.read_archived_test import archive_path
from scripts.runs.v24_2.run_v24_2_test import checkpoint_bundle, prepare_test
from src.skill_evolution.v24_2 import campaign
from src.skill_evolution.v24_2.storage import read, save, same_contract


@pytest.mark.parametrize('label, skill', [('R00', 'initial'), ('R01', 'published')])
def test_checkpoint_uses_the_published_skill_and_reference_test(tmp_path, label, skill):
    root = tmp_path / 'training'
    config = root / 'config.json'
    save(config, dict(batches=[['task']], initial_skill=dict(text='initial')))
    directory = root / 'rounds/R01'
    save(directory / 'publication.json', dict(selected='published'))
    selected = directory / 'selected.md'
    selected.write_text('published')
    bundle = dict(campaign=str(root), skill_text='final')
    reference = tmp_path / 'reference'
    save(reference / 'input.json', bundle)
    output = tmp_path / 'checkpoints' / label
    checkpoint = dict(round=label, source=str(config if label == 'R00' else selected),
                      skill_sha256=sha256(skill.encode()).hexdigest(), reference_evaluation=str(reference))
    assert checkpoint_bundle(root, output, bundle, checkpoint) == dict(bundle, skill_text=skill, checkpoint=checkpoint)
    with pytest.raises(ValueError, match='digest'):
        checkpoint_bundle(root, output, bundle, dict(checkpoint, skill_sha256='wrong'))
    with pytest.raises(ValueError, match='reference Test'):
        checkpoint_bundle(root, output, dict(bundle, campaign=str(tmp_path)), checkpoint)
    if label == 'R01':
        selected.write_text('unpublished candidate')
        with pytest.raises(ValueError, match='export differs'):
            checkpoint_bundle(root, output, bundle, checkpoint)


def test_read_archived_paths_from_another_checkout(tmp_path):
    run = 'v24_2_alfworld_20261106_195800'
    archive = campaign.ROOT / 'artifacts/methods/v24_2' / run
    previous = tmp_path / 'original-checkout'
    assert archive_path(previous / 'experiments/campaigns' / run) == archive
    assert archive_path(previous / 'artifacts/methods/v24_2' / run) == archive
    assert archive_path(archive) == archive
    assert archive_path(tmp_path / 'unrelated.json') == tmp_path / 'unrelated.json'


def test_layout_migration_keeps_contract_bound_to_training_inputs():
    layout = read(campaign.ROOT / 'experiments/methods/v24_2/layout-change.json')
    module = 'src/skill_evolution/v24_2/__init__.py'
    revision = layout['source_revisions'][module]
    saved = {'files': {module: revision['before'], 'docs/methods/v24_2/prompts/editor.md': 'original'}}
    current = {'files': {module: revision['after'], 'src/skill_evolution/v24_2/prompts/editor.md': 'original'}}
    assert same_contract(saved, current)
    changed_files = dict(current['files'])
    changed_files['src/skill_evolution/v24_2/prompts/editor.md'] = 'different revision'
    assert not same_contract(saved, dict(current, files=changed_files))
    assert not same_contract(dict(saved, unexpected_field=True), current)


def test_only_completed_official_publications_can_feed_test(tmp_path):
    config = campaign.configuration()
    campaign.prepare(tmp_path, config)
    adapter = campaign.ALFWorldAdapter()
    with pytest.raises(ValueError, match='incomplete'):
        prepare_test(tmp_path, adapter)

    for number, batch in enumerate(config['batches'], 1):
        head, previous = campaign.current(tmp_path)
        state = dict(previous, previous=head, next_round=number + 1,
                     selected=f'Selected Skill after round {number}', selected_execution_source=None)
        rd = tmp_path / 'rounds' / f'R{number:02}'
        save(rd / 'round_input.json', {'previous': head, 'tasks': batch})
        save(rd / 'publication.json', state)
        campaign.publish(tmp_path, head, state)
    exported = tmp_path / 'final_skill.md'
    exported.write_text('unpublished Candidate')
    with pytest.raises(ValueError, match='export differs'):
        prepare_test(tmp_path, adapter)
    exported.unlink()
    last_round = tmp_path / 'rounds' / f'R{len(config["batches"]):02}'
    save(last_round / 'publication.json', dict(state, selected='different Skill'))
    with pytest.raises(ValueError, match='publication differs'):
        prepare_test(tmp_path, adapter)
