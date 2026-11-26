"""Preflight or train the five-round v27.16 LMB campaign."""
import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs import run_v27_2_campaign as engine
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_2 import config, prompts
from src.skill_evolution.v27_2.campaign import CampaignAdapter

TRAIN = ROOT / 'experiments/campaigns' / HERE.name
REFERENCE = TRAIN.parent / 'v27_15_lmb53_20261125'


class Campaign(CampaignAdapter):
    method_version = 'v27_16_campaign_v1'
    batch_sizes = (11, 11, 11, 10, 10)

    def validation_sources(self):
        return super().validation_sources() | {Path(__file__).resolve()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('preflight', 'train'))
    args = parser.parse_args()
    read = engine.ev.read
    cfg = read(HERE / 'config.json')
    reference = read(REFERENCE / 'config.json')
    require(dict(cfg, method=reference['method']) == reference, 'Training settings differ')
    engine.protocol.ACTOR = cfg['actor']
    config.METHOD_VERSION = Campaign.method_version
    prompts.DIRECTORY = HERE / 'frozen_prompts'
    for name, module in config.MODULES.items():
        module.PROMPT_VERSION = cfg['method']['prompts'][name]
    actor = engine.ActorAdapter(engine.load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    adapter = Campaign(actor)
    with adapter.using():
        config.validate_config(cfg, executable=True)
        hashes = {f'{name}.md': hashlib.sha256(value.encode()).hexdigest()
                  for name, value in config.render_prompts().items()}
        require(hashes == read(HERE / 'prompt_sha256.json'), 'Frozen prompts changed')
        require(adapter.runtime_snapshot(cfg) == dict(read(REFERENCE / 'runtime.json'),
                method=Campaign.method_version), 'Dataset or runtime differs')
        print('Preflight passed:', HERE.name, cfg['actor']['model'], Campaign.batch_sizes, flush=True)
        if args.stage == 'train':
            key = engine.read_credentials(ROOT / '.env', cfg)['OPENAI_API_KEY']
            actor.transport = engine.ChatTransport(key, metadata=cfg['actor'])
            result = engine.run_training(TRAIN, cfg, generate=engine.HTTPGenerator(key),
                                         resume=(TRAIN / 'state.json').is_file())
            print(result, flush=True)


if __name__ == '__main__':
    main()
