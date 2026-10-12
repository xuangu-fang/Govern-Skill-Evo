"""One-shot Diagnosis on the nine fixed refined groups; no new rollout/grouping."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


# Historical pilot target definition, not a general Diagnosis instruction.
PILOT_EXPERIMENT_SCOPE = (
    "The legacy policy forbidding multiple tool calls in one assistant message is "
    "excluded from this pilot's Compliance and Skill optimization targets. "
    "It must not be used as a finding or gap basis; other constraints remain applicable."
)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/methods/v17/archive/legacy/v17_diagnosis_pilot_001')
    parser.add_argument('--groups', nargs='+', metavar='GROUP_ID')
    parser.add_argument('--max-workers', type=int, default=3)
    args = parser.parse_args()
    if args.max_workers < 1 or args.max_workers > 3:
        parser.error('--max-workers must be between 1 and 3')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, level='WARNING')
    from src.skill_evolution.v15.information_boundary_v15 import capture_agent_visible_view, capture_experience, project_oracle_supervision
    from src.skill_evolution.v15.autonomous_gse_v15_benchmark_runtime import normalize_stored_simulation
    from src.skill_evolution.v17.experience_grouping_contract_v17 import GroupingScope, EvolutionExperienceRef
    from src.skill_evolution.v17.experience_cards_v17 import CapturedGroupingExperience, build_experience_cards
    from src.skill_evolution.v17.experience_grouping_v17 import prepare_grouping_request
    from src.skill_evolution.v17.group_diagnosis_input_v17 import build_group_diagnosis_inputs
    from src.skill_evolution.v17.diagnosis_prompt_v17 import build_diagnosis_request
    from src.skill_evolution.v17.diagnosis_v17 import run_group_diagnosis
    import tiktoken

    old = ROOT / 'artifacts/methods/v17/pilot/v17_grouping_pilot_001'
    refined = ROOT / 'artifacts/methods/v17/pilot/v17_grouping_pilot_002'
    manifest = load(old / 'source_manifest.json')
    cards = load(old / 'experience_cards.json')
    scope_data = load(refined / 'grouping/runtime_scope.json')
    scope = GroupingScope(scope_data['round_id'], scope_data['parent_skill_digest'],
                          tuple(EvolutionExperienceRef(**r) for r in scope_data['experience_refs']))
    groups = load(refined / 'grouping/validated_groups.json')
    if len(groups['groups']) != 9:
        raise ValueError('Expected the nine unchanged refined groups')
    results_path = ROOT / 'artifacts/methods/v16/benchmark_v16_one_step_001/step1/evolution_parent/rollout_results.json'
    if hashlib.sha256(results_path.read_bytes()).hexdigest() != manifest['source_results_sha256']:
        raise ValueError('Historical result records changed')
    rows = {r['task_id']: r for r in load(results_path) if r['rollout_index'] == 1}
    if len(rows) != 32 or set(rows) != {m['benchmark_task_id'] for m in manifest['selected']}:
        raise ValueError('Evolution selection mismatch')
    parent_path = ROOT / 'experiments/methods/v14/autonomous_gse_v14/config/skills/S0_empty_skill.md'
    parent = parent_path.read_text()
    if hashlib.sha256(parent.encode()).hexdigest() != manifest['parent_skill_sha256']:
        raise ValueError('Historical Parent changed')
    refs = {ref.task_ref: ref for ref in scope.experiences}
    contexts = {c['context_ref']: c for c in cards['contexts']}
    sources = []
    for item in manifest['selected']:
        row = rows[item['benchmark_task_id']]
        if (row['split'], row['phase'], row['skill_id'], row['rollout_index'], row['rollout_seed']) != ('train', 'evolution_parent', 'S0', 1, 200):
            raise ValueError('Unexpected source lineage')
        ref = refs[item['task_ref']]
        context = contexts[ref.context_ref]
        # Replay only the previously saved public schemas/policy, not canonical policy.
        agent = SimpleNamespace(domain_policy=context['visible_policy'],
                                tools=[SimpleNamespace(openai_schema=s) for s in context['public_tools']])
        domain = {'airline-final-candidate-unified': 'airline',
                  'retail-final-candidate-unified': 'retail'}[row['domain']]
        view = capture_agent_visible_view(agent, domain)
        if hashlib.sha256(view.payload.encode()).hexdigest() != item['visible_context_sha256']:
            raise ValueError('Saved public context mismatch')
        raw_path = ROOT / item['raw_path']
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != item['raw_sha256']:
            raise ValueError('Historical trajectory changed')
        events = normalize_stored_simulation(load(raw_path))
        supervision = project_oracle_supervision(row['evaluation'], row['evaluation'])
        experience = capture_experience(view, events, supervision, 1)
        sources.append(CapturedGroupingExperience(scope.round_id, scope.parent_skill_digest,
                                                  ref, view, experience))
    sources = tuple(sources)
    batch = build_experience_cards(sources, scope=scope)
    if batch.payload != cards:
        raise ValueError('Replayed experience differs from grouping input')
    if prepare_grouping_request(batch, scope=scope)['user_prompt'] != load(refined / 'grouping/grouping_request.json')['user_prompt']:
        raise ValueError('Anonymous grouping input changed')
    requests = build_group_diagnosis_inputs(sources, scope=scope, grouping_result=groups, parent_skill=parent)
    available_group_ids = {request.provenance['group_id'] for request in requests}
    selected_group_ids = set(args.groups or available_group_ids)
    unknown_group_ids = selected_group_ids - available_group_ids
    if unknown_group_ids:
        parser.error(f'unknown group IDs: {sorted(unknown_group_ids)}')
    requests = tuple(request for request in requests
                     if request.provenance['group_id'] in selected_group_ids)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    encoder = tiktoken.get_encoding('cl100k_base')
    preflight = []
    for request in requests:
        prepared = build_diagnosis_request(request, experiment_scope=PILOT_EXPERIMENT_SCOPE)
        preflight.append({'group_id': request.provenance['group_id'],
                          'tasks': len(request.learner_payload['experiences']),
                          'input_sha256': prepared['input_sha256'],
                          'proxy_prompt_tokens': len(encoder.encode(prepared['system_prompt'] + prepared['user_prompt'] + json.dumps(prepared['response_format']), disallowed_special=()))})
    write(output / 'preflight.json', {'source_manifest': str(old.relative_to(ROOT) / 'source_manifest.json'),
          'grouping_result': str(refined.relative_to(ROOT) / 'grouping/validated_groups.json'),
          'grouping_result_sha256': hashlib.sha256((refined / 'grouping/validated_groups.json').read_bytes()).hexdigest(),
          'saved_source_hashes_verified': True, 'saved_cards_exact_match': True,
          'new_rollouts': 0, 'new_grouping_calls': 0, 'max_workers': args.max_workers,
          'token_estimate_note': 'cl100k proxy only; actual counts come from provider.', 'groups': preflight})
    print(json.dumps({'phase': 'preflight_passed', 'groups': preflight}), flush=True)
    results = {}
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        jobs = {pool.submit(run_group_diagnosis, request, artifact_dir=output / request.provenance['group_id'], experiment_scope=PILOT_EXPERIMENT_SCOPE): request.provenance['group_id'] for request in requests}
        for future in as_completed(jobs):
            group_id = jobs[future]
            results[group_id] = future.result()
            write(output / 'progress.json', results)
            print(json.dumps({'group_id': group_id, **results[group_id]}, ensure_ascii=False), flush=True)
    summary = {'groups': len(results), 'valid': sum(r['status'] == 'VALID' for r in results.values()),
               'rejected': sum(r['status'] == 'REJECTED' for r in results.values()),
               'attempts': sum(r['attempts'] for r in results.values()),
               'new_agent_rollouts': 0, 'new_grouping_calls': 0,
               'results': dict(sorted(results.items()))}
    write(output / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}), flush=True)


if __name__ == '__main__':
    main()
