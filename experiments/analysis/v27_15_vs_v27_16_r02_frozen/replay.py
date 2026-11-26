"""Replay only Diagnosis on the v27.14 R02 Parent executions."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

import requests
from experiments.launches.v27_14_lmb53_20261124 import run as source
from src.skill_evolution.v27_2 import diagnosis, stages


def direct_session():
    session = requests.Session()
    session.trust_env = False
    return session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=('v27_15', 'v27_16'))
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    read = source.engine.ev.read
    archive = source.TRAIN / 'rounds/R02/diagnosis'
    old = read(archive / 'identity.json')
    cfg = read(source.HERE / 'config.json')
    source.engine.protocol.ACTOR = cfg['actor']
    source.prompts.DIRECTORY = ROOT / 'experiments/launches' / f'{args.version}_lmb53_20261125' / 'frozen_prompts'
    diagnosis.PROMPT_VERSION = f'{args.version}_lmb_diagnosis_v1'
    actor = source.engine.ActorAdapter(source.engine.load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1'))
    adapter = source.Campaign(actor)
    journal = HERE / args.version / 'diagnosis'
    with adapter.using():
        adapter.register_archive(archive.parent / 'parent_runs')
        call = diagnosis.diagnosis_call(read(archive / 'input.json'))
        assert call.messages[1:] == read(archive / 'base_messages.json')[1:]
        assert cfg['module_calls']['diagnosis'] == old['call_config']
        generate = None
        if not args.verify_only:
            key = source.engine.read_credentials(ROOT / '.env', cfg)['OPENAI_API_KEY']
            generate = source.engine.HTTPGenerator(key, session_factory=direct_session)
        limits = {k: old[k] for k in ('max_attempts', 'max_input_chars', 'max_message_utf8_bytes', 'retry_delay_seconds')}
        path, result = stages.run_stage(journal, call, call_config=old['call_config'], generate=generate,
                                       resume=journal.exists(), read_only=args.verify_only, **limits)
        print(path, result['diagnosis']['decision'])


if __name__ == '__main__':
    main()
