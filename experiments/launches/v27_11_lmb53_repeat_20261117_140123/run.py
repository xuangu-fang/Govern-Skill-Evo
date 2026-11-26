"""Validate or train the frozen five-round v27.11 LMB campaign."""
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
from src.skill_evolution.v27_2 import config, prompts
from src.skill_evolution.v27_2.campaign import CampaignAdapter

BASE = ROOT / 'experiments/campaigns/v27_10_lmb53_20261115'
TRAIN = BASE.parent / HERE.name
protocol = engine.protocol
legacy_context = protocol.execution_context


def project_context(background):
    # Keep the full inherited runtime validation and update its frozen prose.
    return legacy_context(background).replace('uses deepseek-flash with', 'uses deepseek-v4.1-flash with')


class V2711Campaign(CampaignAdapter):
    method_version = 'v27_11_campaign_v1'
    batch_sizes = (11, 11, 11, 10, 10)
    execution_context = staticmethod(project_context)

    def validation_sources(self):
        return super().validation_sources() | {Path(__file__).resolve()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('train', 'preflight'))
    args = parser.parse_args()
    cfg = engine.ev.read(HERE / 'config.json')
    baseline = engine.ev.read(BASE / 'config.json')
    profile = cfg['actor']
    require(profile['model'] == 'deepseek-v4.1-flash' and
            baseline['actor'] == profile,
            'Unexpected project Actor settings')
    config.METHOD_VERSION = V2711Campaign.method_version
    protocol.ACTOR = profile
    protocol.execution_context = project_context
    prompts.DIRECTORY = HERE / 'frozen_prompts'
    for name, module in config.MODULES.items():
        module.PROMPT_VERSION = (f'v27_11_lmb_{name}_v1' if name in ('diagnosis', 'preconditioner')
                                 else baseline['method']['prompts'][name])
    hashes = {f'{name}.md': hashlib.sha256((prompts.DIRECTORY / f'{name}.md').read_bytes()).hexdigest()
              for name in config.MODULES}
    require(hashes == engine.ev.read(HERE / 'prompt_sha256.json'), 'Frozen prompt digest mismatch')
    actor = engine.ActorAdapter(engine.load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    adapter = V2711Campaign(actor)
    with adapter.using():
        config.validate_config(cfg, executable=True)
        require(cfg['batches'] == baseline['batches'] and cfg['initial_skill'] == baseline['initial_skill']
                and engine.ev.EMPTY_MEMORY == engine.ev.read(BASE / 'initial_memory.json'),
                'Batch order, initial Skill or Memory differs from v27.10')
        snapshot = adapter.runtime_snapshot(cfg)
        require(dict(snapshot, method=baseline['method']['version'])
                == engine.ev.read(BASE / 'runtime.json'), 'Training data or runtime differs from v27.10')
        key = engine.read_credentials(ROOT / '.env', cfg)['OPENAI_API_KEY']
        print(json.dumps({'stage': args.stage, 'model': profile['model'],
                          'batch_sizes': list(map(len, cfg['batches'])), 'test_scheduled': False}), flush=True)
        if args.stage == 'train':
            actor.transport = engine.ChatTransport(key, metadata=profile)
            result = engine.run_training(TRAIN, cfg, generate=engine.HTTPGenerator(key),
                                         resume=(TRAIN / 'state.json').exists())
            print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
