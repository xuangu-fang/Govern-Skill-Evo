"""Production P1 capacity measurements. No API or environment execution.

The 16 generator is imported only for its archived seed data and explicitly
synthetic fixtures. Neither its prototype codec nor its file-writing main is used.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / 'experiments/methods/v22/17_p1_input'
REVISION = HERE / 'revision'
OUT = ROOT / 'artifacts/methods/v22/17_p1_input/offline'
sys.path.insert(0, str(REVISION))
from src.skill_evolution.v22 import p1_input
from src.skill_evolution.v22.contract_alignment import PROFILE as V3
from src.skill_evolution.v22.grouped_update import grouped_messages
from src.skill_evolution.v22.grouped_representation import grouping_messages
from src.adapters.alfworld.skill_runtime import object_digest

PROTOTYPE = ROOT / 'experiments/methods/v22/16_input_scalability/prototype'
sys.path.insert(1, str(PROTOTYPE))
spec = importlib.util.spec_from_file_location('capacity_seed16', PROTOTYPE / 'capacity.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)
# The legacy generator prepends v3 on import. Existing imports are already v4;
# restore the authoritative root explicitly for any later lazy imports.
sys.path.remove(str(REVISION)); sys.path.insert(0, str(REVISION))
STAGES = seed.STAGES
compact = p1_input.compact
read = lambda path: json.loads(path.read_text())


def prepare(stage, payload, profile):
    """Rebind only counterfactual fixture views, never historical files/checkpoints."""
    data = deepcopy(payload)
    if stage != 'classification':
        data['update_profile'] = profile
    if stage == 'post_gate_learning':
        data['update_context']['editor'] = {key: deepcopy(seed.EDITOR[key])
                                          for key in ('decision', 'mappings', 'issues', 'watch')}
        data['sources']['editor'] = {'kind': 'editor'}
        data['binding_sha256'] = object_digest({key: value for key, value in data.items()
                                               if key != 'binding_sha256'})
    return data


def messages(stage, payload, profile):
    data = prepare(stage, payload, profile)
    if stage == 'classification':
        return grouping_messages(data, seed.SYSTEM[stage]['text'], profile=profile)
    name = {'main_editor': 'editor', 'post_gate_learning': 'learn'}.get(stage, stage)
    return grouped_messages(name, data)


def metrics(value):
    content = sum(len(row['content']) for row in value)
    count = len(compact(value))
    return {'message_chars': count, 'content_chars': content,
            'token_estimate_range': [round(content / 4), round(content / 2)],
            'token_estimator': 'offline 2-4 content characters/token sensitivity range, NOT model tokenizer or actual usage',
            'over_300k': count > 300000, 'over_400k': count > 400000,
            'sha256': hashlib.sha256(compact(value).encode()).hexdigest()}


def compare(stage, payload):
    start = time.perf_counter()
    old = messages(stage, payload, V3)
    before_pack = time.perf_counter()
    new = messages(stage, payload, p1_input.PROFILE)
    after_pack = time.perf_counter()
    encoded = json.loads(new[1]['content'])
    restored = p1_input.decode(encoded)
    after_unpack = time.perf_counter()
    expected = json.loads(old[1]['content'])
    # Profile identity is the sole intended decoded data difference.
    if stage != 'classification': expected['update_profile'] = p1_input.PROFILE
    # Learning's program-owned binding includes the profile identity.
    if stage == 'post_gate_learning':
        expected['binding_sha256'] = prepare(stage, payload, p1_input.PROFILE)['binding_sha256']
    assert restored == expected, stage
    assert new[0]['content'] == old[0]['content'].replace('Profile: '+V3, 'Profile: '+p1_input.PROFILE) + '\n' + p1_input.INSTRUCTIONS
    a, b = metrics(old), metrics(new)
    return {'v3': a, 'p1': b, 'ratio_p1_over_v3': b['message_chars'] / a['message_chars'],
            'elapsed_ms': {'v3_message_build': 1000*(before_pack-start),
                           'v4_build_encode_and_guard_decode': 1000*(after_pack-before_pack),
                           'independent_decode': 1000*(after_unpack-after_pack)},
            'coverage': {'exact_consumption_roundtrip': True,
                         'current_event_count': sum(len(run['steps']) for run in restored.get('runs', {}).values()),
                         'classification_event_count': sum(len(row['steps']) for row in restored.get('experiences', [])),
                         'source_count': len(restored.get('sources', {})),
                         'historical_source_count': len(restored.get('historical_sources', {})),
                         'archive_sha256': p1_input.sha(expected)}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [{'kind': '08_REENCODED_COUNTERFACTUAL_NOT_LIVE', 'stage': stage,
             'metrics': compare(stage, seed.BASE[stage])} for stage in STAGES]
    for trajectory in ('observed_mix', 'repeat50', 'diverse50', 'wide50'):
        for history in ('fixed_effects', 'growing_effects'):
            for round_number, n in enumerate((12, 12, 12, 12, 9), 1):
                for stage in STAGES:
                    payload = seed.scenario_payload(stage, n, round_number, trajectory, history)
                    rows.append({'kind': 'SYNTHETIC_CAPACITY_ONLY', 'round': round_number,
                                 'tasks': n, 'trajectory': trajectory, 'history': history,
                                 'stage': stage, 'effects': len(payload.get('memory', [])),
                                 'basis': sum(len(e['basis']) for e in payload.get('memory', [])),
                                 'metrics': compare(stage, payload)})
    output = {'schema': 'v22.p1_capacity_measurement.v1', 'profile': p1_input.PROFILE,
              'consumption_schema': p1_input.VIEW_SCHEMA,
              'scope': 'OFFLINE storage-shaped fixtures; no execution, classification or causal validity claim',
              'generator': str(PROTOTYPE / 'capacity.py'),
              'production_encoder': str(Path(p1_input.__file__).resolve()),
              'production_encoder_sha256': hashlib.sha256(Path(p1_input.__file__).read_bytes()).hexdigest(),
              'round_sizes': [12, 12, 12, 12, 9], 'rows': rows}
    (OUT / 'capacity_results.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print('Production P1:', len(rows), 'cases; exact roundtrip and unchanged behavioral system instructions passed')
    for trajectory in ('observed_mix', 'repeat50', 'diverse50', 'wide50'):
        sample = [r for r in rows if r.get('trajectory') == trajectory and r.get('history') == 'growing_effects']
        print(trajectory, {stage: [(r['round'], r['metrics']['v3']['message_chars'], r['metrics']['p1']['message_chars'])
                                   for r in sample if r['stage'] == stage] for stage in STAGES})


if __name__ == '__main__':
    main()
