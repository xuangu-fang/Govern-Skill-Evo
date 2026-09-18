"""Frozen v17 campaign. Private benchmark artifacts stay outside learner inputs."""
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / 'experiments/configs/v17_formal_001'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def load(path):
    return json.loads(path.read_text())


def runtime():
    from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001 import benchmark_runtime
    return benchmark_runtime


def clean_policy(text):
    prefixes = (
        'You should only make one tool call at a time, and if you make a tool call,',
        'You should at most make one tool call at a time, and if you take a tool call,',
    )
    matches = [prefix for prefix in prefixes if prefix in text]
    if len(matches) != 1 or text.count(matches[0]) != 1:
        raise ValueError('Expected exactly one legacy single-tool restriction')
    # Retain the separate tool-call/user-message constraint.
    return text.replace(matches[0], 'If you make a tool call,')


@contextmanager
def frozen_policies(config):
    from tau2.environment.environment import Environment
    original = Environment.get_policy
    policies = config['policies']
    def get_policy(environment):
        current = original(environment)
        key = digest(current.encode())
        if key not in policies:
            raise ValueError('Unfrozen environment policy')
        return (FREEZE / policies[key]).read_text()
    # Scoped to this single-process campaign, before agent construction.
    with patch.object(Environment, 'get_policy', get_policy):
        yield


def verify_freeze():
    manifest = load(FREEZE / 'manifest.json')
    for name, expected in manifest['files'].items():
        path = ROOT / name
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f'Frozen input changed: {name}')
    # Environment versions in the manifest are audit metadata, not launch constraints.
    return load(FREEZE / 'config.json')


def preflight(config):
    from .information_boundary_v15 import unpack
    r = runtime(); registry = r.BenchmarkRegistry(); adapter = r.UnifiedEnvironmentAdapter(registry)
    for split in ('train', 'monitor'):
        if registry.task_ids(split) != config['tasks'][split]:
            raise ValueError('Frozen task split mismatch')
    with frozen_policies(config):
        contexts = {t: unpack(adapter.visible_view_without_models(t), 'AGENT_VISIBLE_VIEW')
                    for t in config['tasks']['train'] + config['tasks']['monitor']}
    if contexts != load(FREEZE / 'contexts.json'):
        raise ValueError('Frozen visible context mismatch')
    return {'status': 'PREFLIGHT', 'rounds': config['rounds'], 'evolution_tasks': 32,
            'monitor_tasks': 41, 'rollouts_per_task_per_role': 1,
            'max_agent_rollouts': config['rounds'] * (32 + 2 * 41)}


def evolve_round(config, root, round_id, parent):
    from .information_boundary_v15 import capture_experience, project_oracle_supervision
    from .autonomous_gse_v15_benchmark_runtime import normalize_stored_simulation
    from .experience_cards_v17 import CapturedGroupingExperience, build_experience_cards
    from .experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingScope
    from .experience_grouping_v17 import run_experience_grouping
    from .group_diagnosis_input_v17 import build_group_diagnosis_inputs
    from .diagnosis_v17 import run_group_diagnosis
    from .diagnosis_validation_v17 import validate_diagnosis_response
    from .compiler_contract_v17 import CompilerDiagnosisSource, CompilerInput
    from .compiler_audit_v17 import run_compiler
    from .compiler_v17 import compile_edit_plan
    from .editor_contract_v17 import EditorInput
    from .editor_v17 import run_editor
    r = runtime(); registry = r.BenchmarkRegistry(); adapter = r.UnifiedEnvironmentAdapter(registry)
    evaluator = r.DeterministicEvaluatorDispatcher(registry)
    parent_path = root / 'parent_skill.md'; parent_path.write_text(parent)
    initial_path = FREEZE / 'S0.md'
    skill_path = initial_path if parent == initial_path.read_text() else parent_path
    parent_digest = digest(parent.encode()); sources = []; contexts = {}; lineage = []
    for index, task_id in enumerate(config['tasks']['train'], 1):
        print(f'{round_id} Evolution {index}/32 {task_id}', flush=True)
        orchestrator, view = adapter.build_orchestrator(task_id, base_config=config['base_config'],
            seed=config['seed'], skill_path=skill_path, initial_skill_path=initial_path)
        initial = orchestrator.environment.tools.db.model_dump(mode='json')
        simulation = orchestrator.run().model_dump(mode='json')
        final = orchestrator.environment.tools.db.model_dump(mode='json')
        directory = root / 'evolution_private' / f'T{index:03d}'
        for name, data in [('initial_db', initial), ('simulation', simulation), ('final_db', final)]:
            save(directory / f'{name}.json', data)
        evaluation = evaluator.evaluate(task_id, initial_db=initial, final_db=final, simulation=simulation)
        save(directory / 'evaluation.json', evaluation)
        context = contexts.setdefault(view.payload, f'C{len(contexts)+1:03d}')
        ref = EvolutionExperienceRef(f'T{index:03d}', context, f'R{index:03d}')
        experience = capture_experience(view, normalize_stored_simulation(simulation),
            project_oracle_supervision(evaluation, evaluation), 1)
        sources.append(CapturedGroupingExperience(round_id, parent_digest, ref, view, experience))
        lineage.append({'task_id': task_id, 'task_ref': ref.task_ref, 'rollout_index': 1, 'seed': config['seed']})
    save(root / 'evolution_private/lineage.json', lineage)
    sources = tuple(sources)
    scope = GroupingScope(round_id, parent_digest, tuple(s.ref for s in sources))
    batch = build_experience_cards(sources, scope=scope, max_input_chars=400000)
    save(root / 'experience_cards.json', batch.payload)
    groups = run_experience_grouping(batch, scope=scope, artifact_dir=root / 'grouping')
    requests = build_group_diagnosis_inputs(sources, scope=scope, grouping_result=groups, parent_skill=parent)
    diagnoses = []; rejected = []
    for request in requests:
        group_id = request.provenance['group_id']; directory = root / 'diagnosis' / group_id
        print(f'{round_id} Diagnosis {group_id}', flush=True)
        result = run_group_diagnosis(request, artifact_dir=directory)
        if result['status'] != 'VALID':
            rejected.append(group_id); continue
        validated = validate_diagnosis_response(load(directory / 'response.json')['raw_response'], request=request)
        diagnoses.append(CompilerDiagnosisSource('DIAGNOSIS/' + digest(validated.payload.encode()), request, validated))
    if rejected:
        raise ValueError(f'Diagnosis rejected: {rejected}; no partial compilation')
    value = CompilerInput(round_id, parent, parent_digest, tuple(diagnoses))
    result = run_compiler(value, artifact_dir=root / 'compiler')
    if result['status'] != 'VALID':
        raise ValueError('Compiler rejected')
    plan = compile_edit_plan(value)
    result = run_editor(EditorInput(value, plan), artifact_dir=root / 'editor')
    if result['status'] in ('NO_UPDATE', 'UNABLE'):
        return None, result['status']
    if result['status'] != 'VALID':
        raise ValueError('Editor rejected')
    return (root / 'editor/candidate_skill.md').read_text(), 'CANDIDATE'


def run_campaign(config, output):
    from .monitor_benchmark_v17 import CurrentBenchmarkMonitor
    from .monitor_v17 import run_monitor
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'frozen_manifest.json', load(FREEZE / 'manifest.json'))
    save(output / 'config.json', config)
    parent = (FREEZE / 'S0.md').read_text(); rounds = []
    (output / 'current_skill.md').write_text(parent)
    try:
        with frozen_policies(config):
            for index in range(1, config['rounds'] + 1):
                verify_freeze()
                round_id = f'round-{index:02d}'; root = output / round_id; root.mkdir()
                candidate, status = evolve_round(config, root, round_id, parent)
                if candidate is None:
                    rounds.append({'round': round_id, 'status': status, 'decision': 'RETAIN'})
                    break
                backend = CurrentBenchmarkMonitor(artifact_dir=root / 'monitor_private/backend',
                    parent_skill=parent, candidate_skill=candidate)
                if backend.base_config != config['base_config'] or backend.seed != config['seed']:
                    raise ValueError('Monitor configuration differs from frozen Evolution')
                result = run_monitor(backend.monitor_input(round_id), backend=backend,
                    artifact_dir=root / 'monitor_private/monitor')
                if result.get('decision') not in ('ACCEPT', 'RETAIN'):
                    raise ValueError('Monitor incomplete')
                if result['decision'] == 'ACCEPT':
                    parent = candidate
                    (output / 'current_skill.md').write_text(parent)
                record = {'round': round_id, **result, 'retained_skill_sha256': digest(parent.encode())}
                rounds.append(record); save(root / 'round_result.json', record)
                save(output / 'campaign.json', {'status': 'RUNNING', 'rounds': rounds})
                print(json.dumps(record), flush=True)
        save(output / 'campaign.json', {'status': 'COMPLETE', 'rounds': rounds,
            'stop_reason': status if candidate is None else 'ROUND_LIMIT'})
    except BaseException as exc:
        save(output / 'campaign.json', {'status': 'INCOMPLETE', 'rounds': rounds,
             'error_type': type(exc).__name__})
        raise
