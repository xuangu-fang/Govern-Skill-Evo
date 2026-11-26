"""Replay only Diagnosis, using archived v2 user messages as parity checks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from scripts.runs.run_v27_2_campaign import (
    ActorAdapter, CampaignAdapter, HTTPGenerator, load_dataset, read_credentials,
)
from src.skill_evolution.v27_2 import config, diagnosis, stages

SOURCE = ROOT / 'experiments/campaigns/v27_2_precond_v3_lmb53_20261105_131046'
FROZEN = ROOT / 'experiments/launches/v27_2_precond_v3_lmb53_20261105_131046/frozen_prompts'


def read(path):
    return json.loads(path.read_bytes())


def replay(round_id, offline=False):
    source = SOURCE / 'rounds' / round_id / 'diagnosis'
    destination = HERE / round_id
    original_input = read(source / 'input.json')
    attempt = source / read(source / 'result.json')['path']
    archived_messages = read(attempt / 'messages.json')
    identity = read(source / 'identity.json')
    adapter = CampaignAdapter(ActorAdapter(load_dataset(ROOT / 'data/livemathematicianbench/prepared_v1')))
    with adapter.using():
        active = config.validate_config(read(config.DEFAULT_CONFIG), executable=True)
        adapter.register_archive(source.parent / 'parent_runs')
        call = diagnosis.diagnosis_call(original_input)
        assert call.prompt_version == 'v27_2_lmb_diagnosis_v3'
        assert identity['prompt'] == 'v27_2_lmb_diagnosis_v2'
        assert call.input == original_input
        assert archived_messages == read(source / 'base_messages.json')
        assert archived_messages[0]['content'] == (FROZEN / 'diagnosis.md').read_text()
        assert archived_messages[1:] == call.messages[1:] and archived_messages[0] != call.messages[0]
        before = archived_messages[0]['content'].split('\n\n')
        after = call.messages[0]['content'].split('\n\n')
        assert len(before) == len(after)
        index, = [i for i in range(len(before)) if before[i] != after[i]]
        assert before[index].startswith('updates contains one or more independently justified')
        assert after[index].startswith('Each Update expresses one complete behavioral correction')
        assert active['method']['prompts']['preconditioner'] == 'v27_2_lmb_preconditioner_v3'
        assert config.render_prompts()['preconditioner'] == (FROZEN / 'preconditioner.md').read_text()
        keys = ('max_attempts', 'max_input_chars', 'max_message_utf8_bytes', 'retry_delay_seconds')
        assert all(active[k] == identity[k] for k in keys)
        assert identity['call_config'] == active['module_calls'][call.name]
        opts = {k: identity[k] for k in keys}
        generate = None
        if not offline:
            credentials = read_credentials(ROOT / '.env', active)
            generate = HTTPGenerator(credentials['OPENAI_API_KEY'])
        stages.run_stage(destination, call, call_config=identity['call_config'], **opts,
                         generate=generate, resume=destination.exists(), read_only=offline)
        assert read(destination / 'input.json') == original_input
        assert read(destination / 'base_messages.json')[1:] == archived_messages[1:]
        print(round_id, read(destination / 'result.json')['path'],
              'user message SHA-256', sha256(call.messages[1]['content'].encode()).hexdigest(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('round', choices=('R02', 'R03'))
    parser.add_argument('--verify-only', action='store_true', help='Verify archived output without network calls.')
    args = parser.parse_args()
    replay(args.round, offline=args.verify_only)
