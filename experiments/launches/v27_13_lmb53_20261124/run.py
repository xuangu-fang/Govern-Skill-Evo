"""Validate, train or evaluate the frozen five-round v27.13 LMB campaign."""
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
from experiments.launches.v27_13_lmb53_20261124 import recovery

BASE = ROOT / 'experiments/campaigns/v27_12_lmb53_20261118'
TRAIN = BASE.parent / HERE.name
TEST = ROOT / 'experiments/evaluations' / (HERE.name + '_test_deepseek_flash')
CREDENTIALS = ROOT / '.env.v27_12'
protocol = engine.protocol
legacy_context = protocol.execution_context


def project_context(background):
    # Keep the full inherited runtime validation and update its frozen prose.
    return legacy_context(background).replace('uses deepseek-flash with', f"uses {background['model']} with")


class V2713Campaign(CampaignAdapter):
    method_version = 'v27_13_campaign_v1'
    batch_sizes = (11, 11, 11, 10, 10)
    execution_context = staticmethod(project_context)

    def validation_sources(self):
        return super().validation_sources() | {Path(__file__).resolve(), Path(recovery.__file__).resolve()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('train', 'test', 'preflight'))
    args = parser.parse_args()
    cfg = engine.ev.read(HERE / 'config.json')
    baseline = engine.ev.read(BASE / 'config.json')
    profile = cfg['actor']
    expected_actor = dict(baseline['actor'], model='deepseek-flash',
                          endpoint='https://api.deepseek.com/chat/completions')
    require(profile == expected_actor, 'Unexpected DeepSeek Actor settings')
    config.METHOD_VERSION = V2713Campaign.method_version
    protocol.ACTOR = profile
    protocol.execution_context = project_context
    prompts.DIRECTORY = HERE / 'frozen_prompts'
    for name, module in config.MODULES.items():
        module.PROMPT_VERSION = cfg['method']['prompts'][name]
    hashes = {f'{name}.md': hashlib.sha256(prompt.encode('utf-8')).hexdigest()
              for name, prompt in config.render_prompts().items()}
    require(hashes == engine.ev.read(HERE / 'prompt_sha256.json'), 'Frozen prompt digest mismatch')
    actor_type = engine.ActorAdapter
    if (recovery.EXTRA / 'result.json').is_file():
        actor_type = recovery.AuthorizedActor
        for name in ('diagnosis', 'preconditioner', 'replay'):
            module = config.MODULES[name]
            factory = name + '_call'
            setattr(module, factory, recovery.annotate_request(getattr(module, factory)))
    actor = actor_type(engine.load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    adapter = V2713Campaign(actor)
    with adapter.using():
        config.validate_config(cfg, executable=True)
        require(cfg['batches'] == baseline['batches'] and cfg['initial_skill'] == baseline['initial_skill']
                and engine.ev.EMPTY_MEMORY == engine.ev.read(BASE / 'initial_memory.json'),
                'Batch order, initial Skill or Memory differs from v27.12')
        snapshot = adapter.runtime_snapshot(cfg)
        expected_runtime = dict(engine.ev.read(BASE / 'runtime.json'),
                                method=cfg['method']['version'], actor=expected_actor)
        require(snapshot == expected_runtime, 'Unexpected training data or runtime')
        print(json.dumps({'stage': args.stage, 'model': profile['model'],
                          'batch_sizes': list(map(len, cfg['batches'])), 'endpoint': profile['endpoint'],
                          'prompts': config.prompt_versions(), 'prompt_sha256': hashes}), flush=True)
        if args.stage == 'preflight':
            return
        key = engine.read_credentials(CREDENTIALS, cfg)['OPENAI_API_KEY']
        actor.transport = engine.ChatTransport(key, metadata=profile)
        if args.stage == 'train':
            result = engine.run_training(TRAIN, cfg, generate=engine.HTTPGenerator(key),
                                         resume=(TRAIN / 'state.json').exists())
        else:
            require((TRAIN / 'state.json').is_file(), 'Test requires a completed v27.13 campaign')
            result = engine.run_test(TRAIN, TEST, resume=(TEST / 'evaluation.json').exists())
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
