"""Check the v29.9 bindings and replay saved v29.8 adjustments without model calls."""
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

from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29_9 import config, editor, preconditioner, stages
from src.skill_evolution.v29_9.campaign import CampaignAdapter, DEFAULT_CONFIG


def verify_archive(root):
    saved_config = stages.read(root / 'config.json')
    target = stages.read(DEFAULT_CONFIG)
    saved_config['method']['version'] = target['method']['version']
    saved_config['method']['prompts']['preconditioner'] = target['method']['prompts']['preconditioner']
    if saved_config != target:
        raise ValueError('Experiment configuration differs from the archived baseline')
    archived_prompts = stages.read(root / 'implementation.json')['prompts']
    rendered = config.render_prompts()
    if rendered.keys() != archived_prompts.keys() or [
            name for name in rendered if rendered[name] != archived_prompts[name]] != ['preconditioner']:
        raise ValueError('Unexpected prompt differences from the archived baseline')

    actor = DocVQAActorAdapter(DocVQADataset())
    actor.workers = stages.read(root / 'runtime.json')['workers']
    adapter = CampaignAdapter(actor)
    verified_rounds = []
    with adapter.using():
        config.validate_config(target, executable=True)
        for index in range(1, len(target['batches']) + 1):
            round_dir = root / 'rounds' / f'R{index:02}'
            diagnosis_stage = round_dir / 'diagnosis'
            attempt = diagnosis_stage / stages.read(diagnosis_stage / 'result.json')['path']
            if stages.read(attempt / 'parsed.json')['decision'] == 'no_change':
                continue
            stage = round_dir / 'preconditioner'
            saved = stages.read(stage / 'input.json')
            adapter.begin_round()
            with adapter.memory_operation():
                adapter.register_archive(round_dir / 'parent_runs')
                call = stages._verified_call(preconditioner.preconditioner_call(saved, saved['memory']))
                if call.messages[0]['content'] != rendered['preconditioner'] or (
                        call.messages[1:] != stages.read(stage / 'base_messages.json')[1:]):
                    raise ValueError(f'{round_dir.name}: unexpected request difference')
                attempt = stage / stages.read(stage / 'result.json')['path']
                result = call.complete(stages.read(attempt / 'parsed.json'))
                if result != stages.read(attempt / 'result.json'):
                    raise ValueError(f'{round_dir.name}: adjustment compilation differs')
                if result['effective_plan'] is not None:
                    messages = editor.editor_call(result).messages
                    if messages != stages.read(round_dir / 'editor/base_messages.json'):
                        raise ValueError(f'{round_dir.name}: Editor handoff differs')
            verified_rounds.append(round_dir.name)
    if not verified_rounds:
        raise ValueError('No archived Preconditioner calls to verify')
    return verified_rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-campaign', type=Path, default=ROOT /
                        'experiments/campaigns/v29_8_docvqa160_20261112_125216')
    args = parser.parse_args()
    with ExitStack() as guard:
        for obj, name in ((socket.socket, 'connect'), (socket.socket, 'connect_ex'),
                          (socket, 'create_connection'), (subprocess, 'Popen')):
            guard.enter_context(patch.object(obj, name, side_effect=AssertionError('Offline verification only')))
        suite = unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v29_9.test_binding')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if result.skipped or not result.wasSuccessful():
            return 1
        rounds = verify_archive(args.baseline_campaign)
    print(json.dumps({'status': 'passed', 'tests_run': result.testsRun, 'verified_rounds': rounds,
                      'changed_prompts': ['preconditioner'], 'training_started': False}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
