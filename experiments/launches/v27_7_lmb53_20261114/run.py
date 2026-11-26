"""Validate the frozen v27.7 launch, or explicitly run its train or test stage."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs import run_v27_2_campaign as engine
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_2 import config, diagnosis, editor, evaluation, preconditioner, prompts
from src.skill_evolution.v27_2.campaign import CampaignAdapter

BASE = ROOT / 'experiments/campaigns/v27_5_lmb53_20261113'
TRAIN = ROOT / 'experiments/campaigns' / HERE.name
TEST = ROOT / 'experiments/evaluations' / (HERE.name + '_test')


class V277Campaign(CampaignAdapter):
    method_version = 'v27_7_campaign_v1'
    batch_sizes = (11, 11, 11, 10, 10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', nargs='?', default='preflight', choices=('preflight', 'train', 'test'))
    stage = parser.parse_args().stage

    config.METHOD_VERSION = V277Campaign.method_version
    prompts.DIRECTORY = HERE / 'frozen_prompts'
    evaluation.FORMAT = 'v27_7_final_test_v1'
    diagnosis.PROMPT_VERSION = 'v27_6_lmb_diagnosis_v1'
    preconditioner.PROMPT_VERSION = 'v27_7_lmb_preconditioner_v1'
    editor.PROMPT_VERSION = 'v27_5_lmb_editor_v1'
    hashes = {f'{name}.md': hashlib.sha256((prompts.DIRECTORY / f'{name}.md').read_bytes()).hexdigest()
              for name in config.MODEL_MODULES}
    require(hashes == engine.ev.read(HERE / 'prompt_sha256.json'), 'Frozen prompt digest mismatch')

    cfg = engine.ev.read(HERE / 'config.json')
    actor = engine.ActorAdapter(engine.load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    adapter = V277Campaign(actor)
    with adapter.using():
        config.validate_config(cfg, executable=True)
        baseline = engine.ev.read(BASE / 'config.json')
        train_ids = [task for batch in cfg['batches'] for task in batch]
        require(cfg['batches'] == baseline['batches'],
                'Optimization order differs from v27.5')
        snapshot = adapter.runtime_snapshot(cfg)
        require({**snapshot, 'method': baseline['method']['version']} == engine.ev.read(BASE / 'runtime.json'),
                'Actor, dataset, scorer context or training cases differ from v27.4')
        require(engine.ev.EMPTY_MEMORY == engine.ev.read(BASE / 'initial_memory.json') and
                cfg['initial_skill'] == baseline['initial_skill'], 'Initial Skill or Memory differs')
        reference = engine.ev.read(ROOT / 'experiments/evaluations' / (BASE.name + '_test') / 'evaluation.json')
        require(actor.dataset.splits['test'] == reference['tasks'] and len(set(reference['tasks'])) == 124,
                'Held-out task IDs or order differ')
        if stage == 'preflight':
            print(json.dumps({'status': 'valid', 'method': adapter.method_version,
                              'batch_sizes': list(map(len, cfg['batches'])),
                              'train_count': len(train_ids), 'test_count': len(reference['tasks'])}))
            return

        if stage == 'test':
            identity = evaluation.prepare_test(TRAIN, TEST)
            require(all(identity[key] == reference[key] for key in
                        ('tasks', 'cases', 'scorer_profile', 'actor', 'workers')), 'Test protocol differs')
        key = engine.read_credentials(ROOT / '.env', cfg)['OPENAI_API_KEY']
        actor.transport = engine.ChatTransport(key, metadata=engine.protocol.ACTOR)
        if stage == 'train':
            result = engine.run_training(TRAIN, cfg, generate=engine.HTTPGenerator(key),
                                         resume=(TRAIN / 'state.json').exists())
        else:
            result = evaluation.run_test(TRAIN, TEST, resume=(TEST / 'evaluation.json').exists())
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
