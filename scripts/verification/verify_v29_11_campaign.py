"""Offline v29.11 preflight using frozen v29.10 requests and responses."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from experiments.docvqa_image_refs.read_archive import DocVQAArchive
from src.skill_evolution.v29 import storage
from src.skill_evolution.v29.benchmarks.docvqa import actor as actor_runtime, adapter as actor_adapter, protocol
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29_10.campaign import DEFAULT_CONFIG as BASELINE_CONFIG
from src.skill_evolution.v29_11 import config, diagnosis, editor, preconditioner, stages
from src.skill_evolution.v29_11.campaign import CampaignAdapter, DEFAULT_CONFIG


def check_stage(folder, call, prompt):
    verified = stages._verified_call(call)
    expected = stages.read(folder / 'base_messages.json')
    expected[0] = {**expected[0], 'content': prompt}
    if verified.messages != expected:
        raise ValueError(f'{folder}: request differs beyond the system prompt')
    attempt = folder / stages.read(folder / 'result.json')['path']
    compiled = verified.complete(stages.read(attempt / 'parsed.json'))
    if compiled != stages.read(attempt / 'result.json'):
        raise ValueError(f'{folder}: archived response compiled differently')
    return compiled


def verify_archive(root):
    if stages.read(root / 'config.json') != stages.read(BASELINE_CONFIG):
        raise ValueError('Expected the v29.10 formal configuration')
    target = stages.read(DEFAULT_CONFIG)
    archived = stages.read(root / 'implementation.json')['prompts']
    prompts = config.render_prompts()
    endpoint = target['actor']['endpoint']
    if prompts.keys() != archived.keys() or any(endpoint in prompt for prompt in prompts.values()):
        raise ValueError('Expected the same stage names and no API address in the v29.11 prompts')
    for name in ('editor', 'replay'):
        if prompts[name] != archived[name].replace(f' through {endpoint}', ''):
            raise ValueError(f'{name}: unexpected change beyond the API address removal')
    for name in ('diagnosis', 'preconditioner'):
        if prompts[name] == archived[name]:
            raise ValueError(f'{name}: expected a revised prompt')

    actor = DocVQAActorAdapter(DocVQADataset())
    actor.workers = stages.read(root / 'runtime.json')['workers']
    adapter = CampaignAdapter(actor)
    checked = {'diagnosis': [], 'preconditioner': [], 'editor_handoff': []}
    with adapter.using():
        config.validate_config(target, executable=True)
        for index in range(1, len(target['batches']) + 1):
            rd = root / 'rounds' / f'R{index:02}'
            adapter.begin_round()
            with adapter.memory_operation():
                adapter.register_archive(rd / 'parent_runs')
                saved = stages.read(rd / 'diagnosis/input.json')
                diagnosed = check_stage(rd / 'diagnosis', diagnosis.diagnosis_call(saved), prompts['diagnosis'])
                checked['diagnosis'].append(rd.name)
                if diagnosed['diagnosis']['decision'] == 'no_change':
                    continue
                memory = stages.read(rd / 'preconditioner/input.json')['memory']
                call = preconditioner.preconditioner_call(diagnosed, memory)
                adjusted = check_stage(rd / 'preconditioner', call, prompts['preconditioner'])
                checked['preconditioner'].append(rd.name)
                if adjusted['effective_plan'] is not None:
                    expected = stages.read(rd / 'editor/base_messages.json')
                    expected[0]['content'] = expected[0]['content'].replace(f' through {endpoint}', '')
                    if editor.editor_call(adjusted).messages != expected:
                        raise ValueError(f'{rd.name}: Editor received different messages')
                    checked['editor_handoff'].append(rd.name)
    return checked


def archived_reader(archive, campaign):
    first = campaign / 'rounds/R01/parent_runs/actor/0001/signature.json'
    archived_root = Path(archive.read_json(first)['metadata']['image_root'])
    local_root = protocol.DEFAULT_DATA_ROOT.resolve()
    release_path = protocol.DEFAULT_DATA_ROOT.relative_to(ROOT).parts
    if not archived_root.is_absolute() or archived_root.parts[-len(release_path):] != release_path:
        raise ValueError(f'{first}: expected the archived DocVQA release path')

    def read(path):
        record = archive.read_json(path)
        path = Path(path)
        if path.name == 'signature.json' and path.resolve().is_relative_to(campaign):
            # Compare the signature after verifying the original archived bytes.
            metadata = record['metadata']
            if Path(metadata['image_root']) != archived_root:
                raise ValueError(f'{path}: archived image root differs')
            metadata['image_root'] = str(local_root)
        return record

    return read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-campaign', type=Path, default=ROOT /
                        'experiments/campaigns/v29_10_docvqa160_20261117_131315')
    args = parser.parse_args()
    with ExitStack() as guard:
        for obj, name in ((socket.socket, 'connect'), (socket.socket, 'connect_ex'),
                          (socket, 'create_connection'), (subprocess, 'Popen')):
            guard.enter_context(patch.object(obj, name, side_effect=AssertionError('Offline verification only')))
        suite = unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29_11.test_binding')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if result.skipped or not result.wasSuccessful():
            return 1
        campaign = args.baseline_campaign.resolve()
        archive = guard.enter_context(DocVQAArchive())
        read = archived_reader(archive, campaign)
        for module in (storage, actor_runtime, actor_adapter):
            guard.enter_context(patch.object(module, 'read', read))
        checked = verify_archive(campaign)
    print(json.dumps({'status': 'passed', 'tests_run': result.testsRun, 'verified_rounds': checked,
                      'changed_prompts': list(config.MODEL_MODULES), 'training_started': False}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
