"""Run and resume the frozen LMB campaign, then its separate held-out Test."""
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from scripts.runs import run_v27_2_campaign as engine
from src.skill_evolution.v27_2 import config, diagnosis, editor, evaluation, preconditioner, prompts
from src.skill_evolution.v27_2.campaign import CampaignAdapter

BASE = ROOT / 'experiments/campaigns/v27_3_lmb53_20261113'
TRAIN = ROOT / 'experiments/campaigns' / HERE.name
TEST = ROOT / 'experiments/evaluations' / (HERE.name + '_test')


def read(path):
    return json.loads(path.read_bytes())


def main():
    prompts.DIRECTORY = HERE / 'frozen_prompts'
    for name, digest in read(HERE / 'prompt_sha256.json').items():
        assert hashlib.sha256((prompts.DIRECTORY / name).read_bytes()).hexdigest() == digest
    cfg = read(HERE / 'config.json')
    baseline = read(BASE / 'config.json')
    expected = dict(baseline)
    expected['method'] = {**baseline['method'], 'version':'v27_4_campaign_v1',
        'prompts':{**baseline['method']['prompts'], 'diagnosis':'v27_4_lmb_diagnosis_v1',
                   'preconditioner':'v27_4_lmb_preconditioner_v1','editor':'v27_4_lmb_editor_v1'}}
    assert cfg == expected
    config.METHOD_VERSION = CampaignAdapter.method_version = cfg['method']['version']
    for module in (diagnosis, preconditioner, editor):
        module.PROMPT_VERSION = cfg['method']['prompts'][module.__name__.split('.')[-1]]
    evaluation.FORMAT = 'v27_4_final_test_v1'
    actor = engine.ActorAdapter(engine.load_dataset(ROOT/'data/livemathematicianbench/prepared_v1'))
    adapter = CampaignAdapter(actor)
    with adapter.using():
        config.validate_config(cfg, executable=True)
        snap = adapter.runtime_snapshot(cfg)
        assert {**snap, 'method':baseline['method']['version']} == read(BASE/'runtime.json')
        assert cfg['initial_skill']['text'].encode() == (BASE/'initial_skill.md').read_bytes()
        assert engine.ev.EMPTY_MEMORY == read(BASE/'initial_memory.json') and engine.ev.EMPTY_MEMORY['memory'] == {'rounds':[]}
        reference = read(BASE.parents[1]/'evaluations'/(BASE.name+'_test')/'evaluation.json')
        assert list(actor.dataset.splits['test']) == reference['tasks'] and len(reference['tasks']) == 124
        if sys.argv[1:] == ['--preflight']:
            print('Preflight passed. No model requests.')
            return
        if sys.argv[1:]:
            raise ValueError('Unexpected command-line arguments')
        scheduled = datetime(2026, 11, 13, 12, 0, 0, tzinfo=ZoneInfo('Asia/Shanghai'))
        print('Armed for', scheduled.isoformat(), flush=True)
        while (remaining := scheduled.timestamp() - time.time()) > 0:
            time.sleep(min(remaining, 30))
        started = datetime.now(scheduled.tzinfo)
        assert started >= scheduled
        receipt = HERE/'first_start.json'
        if not receipt.exists():
            receipt.write_text(json.dumps({'scheduled':scheduled.isoformat(),'started':started.isoformat()},indent=2)+'\n')
        creds = engine.read_credentials(ROOT/'.env', cfg)
        actor.transport = engine.ChatTransport(creds['OPENAI_API_KEY'], metadata=engine.protocol.ACTOR)
        print('Training', TRAIN, flush=True)
        if not (TRAIN/'training_summary.json').exists():
            engine.run_training(TRAIN, cfg, generate=engine.HTTPGenerator(creds['OPENAI_API_KEY']),resume=(TRAIN/'state.json').exists())
        print('Training completed. Testing',TEST,flush=True)
        if not (TEST/'summary.json').exists():
            ident=evaluation.prepare_test(TRAIN,TEST)
            ref=read(BASE.parents[1]/'evaluations'/(BASE.name+'_test')/'evaluation.json')
            assert all(ident[key]==ref[key] for key in ('tasks','cases','scorer_profile','actor','workers'))
            evaluation.run_test(TRAIN, TEST, resume=(TEST/'evaluation.json').exists())
        print(read(TEST/'summary.json'), flush=True)


if __name__=='__main__':
    main()
