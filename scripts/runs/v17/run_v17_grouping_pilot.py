"""Replay fixed rollout 1 of v16 S0 Evolution; call only the v17 Grouper."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/methods/v17/pilot/v17_grouping_pilot_001')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, level='WARNING')
    from scripts.benchmarks.v3.final.experiments.benchmark_v16_one_step_001.run_v16 import OneStepCampaign, RUN
    from src.skill_evolution.shared.experiment_paths import resolve_artifact_path
    from src.skill_evolution.v15.autonomous_gse_v15_benchmark_runtime import normalize_stored_simulation
    from src.skill_evolution.v15.information_boundary_v15 import capture_experience, project_oracle_supervision, unpack
    from src.skill_evolution.v17.experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingScope
    from src.skill_evolution.v17.experience_cards_v17 import CapturedGroupingExperience, build_experience_cards
    from src.skill_evolution.v17.experience_grouping_v17 import prepare_grouping_request, run_experience_grouping
    from src.skill_evolution.v17.group_diagnosis_input_v17 import build_group_diagnosis_inputs
    from src.skill_evolution.v15.skill_text_v15 import parse_skill

    campaign = OneStepCampaign()
    parent = campaign.initial_skill_path.read_text(encoding='utf-8')
    sections = parse_skill(parent)
    if any(sections.values()):
        raise ValueError('Expected S0 with empty Skill sections')
    digest = hashlib.sha256(parent.encode()).hexdigest()
    results_path = RUN / 'step1/evolution_parent/rollout_results.json'
    rows = json.loads(results_path.read_text())
    selected = sorted((row for row in rows if row['rollout_index'] == 1), key=lambda row: row['task_id'])
    task_ids = campaign.registry.task_ids('train')
    if len(selected) != 32 or {r['task_id'] for r in selected} != set(task_ids):
        raise ValueError('Expected exactly one rollout 1 for each of the 32 Evolution tasks')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources, contexts, manifest = [], {}, []
    for i, row in enumerate(selected, 1):
        if (row['phase'], row['split'], row['skill_id'], row['rollout_seed']) != ('evolution_parent', 'train', 'S0', campaign.seeds[0]):
            raise ValueError('Unexpected source lineage')
        if resolve_artifact_path(row['skill_path']).resolve() != campaign.initial_skill_path.resolve():
            raise ValueError('Unexpected source Skill path')
        _, view = campaign.adapter.build_orchestrator(
            row['task_id'], base_config=campaign.base_config, seed=campaign.seeds[0],
            skill_path=campaign.initial_skill_path, initial_skill_path=campaign.initial_skill_path)
        context_ref = contexts.setdefault(view.payload, f'C{len(contexts)+1:03d}')
        ref = EvolutionExperienceRef(f'T{i:03d}', context_ref, f'R{i:03d}')
        raw_path = RUN / 'step1/evolution_parent/trajectories' / f"{row['task_id']}_rollout_01_raw.json"
        raw = json.loads(raw_path.read_text())
        events = normalize_stored_simulation(raw)
        labels = project_oracle_supervision(row['evaluation'], row['evaluation'])
        experience = capture_experience(view, events, labels, 1)
        sources.append(CapturedGroupingExperience('v17-pilot-round-1', digest, ref, view, experience))
        manifest.append({'task_ref': ref.task_ref, 'benchmark_task_id': row['task_id'],
                         'rollout_index': 1, 'rollout_seed': row['rollout_seed'],
                         'raw_path': str(raw_path.relative_to(ROOT)),
                         'raw_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                         'visible_context_sha256': hashlib.sha256(view.payload.encode()).hexdigest()})
    sources = tuple(sources)
    scope = GroupingScope('v17-pilot-round-1', digest, tuple(s.ref for s in sources))
    batch = build_experience_cards(sources, scope=scope, max_input_chars=400_000)
    for card, source in zip(batch.payload['cards'], sources):
        if card['events'] != unpack(source.experience, 'TRAJECTORY_DERIVED')['trajectory']:
            raise ValueError('Lossy card projection')
    request = prepare_grouping_request(batch, scope=scope)
    import tiktoken
    encoder = tiktoken.get_encoding('cl100k_base')
    estimate = len(encoder.encode(request['system_prompt'] + request['user_prompt'] + json.dumps(request['response_format']), disallowed_special=()))
    write(output / 'source_manifest.json', {
        'selection': 'rollout_index == 1, fixed before examining outcomes',
        'source_results_sha256': hashlib.sha256(results_path.read_bytes()).hexdigest(),
        'parent_skill_sha256': digest, 'parent_is_empty_sections': True,
        'context_replay_limitation': 'Reconstructed deployed public context; historical context equality not independently proven.',
        'selected': manifest})
    write(output / 'experience_cards.json', batch.payload)
    write(output / 'input_statistics.json', {**batch.statistics,
          'cl100k_proxy_prompt_tokens': estimate,
          'token_estimate_note': 'Proxy only, not DeepSeek tokenizer or verified endpoint context capacity.',
          'reserved_completion_tokens': request['max_completion_tokens']})
    print(json.dumps({'phase': 'calling_grouper', 'tasks': 32,
                      'input_chars': batch.statistics['input_chars'], 'proxy_tokens': estimate}), flush=True)
    result = run_experience_grouping(batch, scope=scope, artifact_dir=output / 'grouping')
    requests = build_group_diagnosis_inputs(sources, scope=scope, grouping_result=result, parent_skill=parent)
    diagnosis_dir = output / 'diagnosis_inputs'
    diagnosis_dir.mkdir()
    for i, item in enumerate(requests, 1):
        write(diagnosis_dir / f'group_{i:03d}.json', item.learner_payload)
        write(diagnosis_dir / f'group_{i:03d}_provenance.json', item.provenance)
    attempts = json.loads((output / 'grouping/grouping_attempts.json').read_text())
    summary = {'tasks': 32, 'groups': len(result['groups']),
               'group_sizes': [len(g['members']) for g in result['groups']],
               'singleton_count': sum(len(g['members']) == 1 for g in result['groups']),
               'model_calls': len(attempts), 'new_agent_rollouts': 0, 'diagnosis_model_calls': 0,
               'elapsed_model_seconds': sum(a['elapsed_seconds'] for a in attempts),
               'usage': [a.get('usage') for a in attempts]}
    write(output / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
