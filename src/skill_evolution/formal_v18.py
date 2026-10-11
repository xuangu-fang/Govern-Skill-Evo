"""Frozen v18 campaign. Private benchmark artifacts stay outside learner inputs."""
import hashlib
import json
import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / 'experiments/configs/v18_formal_001'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    temporary.replace(path)


def write_skill(path, text):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(text.encode('utf-8'))
    temporary.replace(path)


def load(path):
    return json.loads(path.read_bytes().decode('utf-8'))


@contextmanager
def campaign_lock(output):
    """Prevent concurrent CLI processes from mutating one campaign directory."""
    lock_path = output.parent / f'.{output.name}.campaign.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f'Campaign already running: {output}') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def runtime():
    from . import benchmark_runtime_v18 as benchmark_runtime
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
        return (FREEZE / policies[key]).read_bytes().decode('utf-8')
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
    config = load(FREEZE / 'config.json')
    if digest((FREEZE / 'user_prompts.json').read_bytes()) != config['user_prompts_sha256']:
        raise ValueError('Frozen User prompt snapshot digest mismatch')
    return config


def preflight(config):
    from .information_boundary_v15 import unpack
    r = runtime(); registry = r.BenchmarkRegistry(); adapter = r.UnifiedEnvironmentAdapter(registry, frozen_user_prompts=load(FREEZE / "user_prompts.json"))
    for split in ('train', 'monitor'):
        if registry.task_ids(split) != config['tasks'][split]:
            raise ValueError('Frozen task split mismatch')
    with frozen_policies(config):
        contexts = {t: unpack(adapter.visible_view_without_models(t), 'AGENT_VISIBLE_VIEW')
                    for t in config['tasks']['train'] + config['tasks']['monitor']}
    for task_id in config['tasks']['train'] + config['tasks']['monitor']:
        with frozen_policies(config):
            adapter.build_orchestrator(task_id, base_config=config['base_config'], seed=config['seed'],
                skill_path=FREEZE / 'S0.md', initial_skill_path=FREEZE / 'S0.md')
    if contexts != load(FREEZE / 'contexts.json'):
        raise ValueError('Frozen visible context mismatch')
    return {'status': 'PREFLIGHT', 'rounds': config['rounds'], 'evolution_tasks': len(config['tasks']['train']),
            'monitor_tasks': len(config['tasks']['monitor']), 'rollouts_per_task_per_role': 1,
            'max_agent_rollouts': config['rounds'] * (len(config['tasks']['train']) + 2 * len(config['tasks']['monitor']))}


def evolution_rollout(directory, *, orchestrator, evaluator, task_id, seed):
    """Reuse completed trajectories, independent of success/compliance outcomes."""
    initial = orchestrator.environment.tools.db.model_dump(mode='json')
    names = ('initial_db', 'simulation', 'final_db')
    if all((directory / f'{name}.json').is_file() for name in names):
        stored_initial, simulation, final = (load(directory / f'{name}.json') for name in names)
        if stored_initial != initial or simulation.get('task_id') != task_id or simulation.get('seed') != seed:
            raise ValueError('Saved Evolution trajectory binding mismatch')
        print(f'  REUSE {directory.name}', flush=True)
    else:
        # Archive a partial checkpoint before rerunning the task from its initial state.
        if directory.exists():
            index = 1
            archive = directory.with_name(directory.name + f'.partial-{index}')
            while archive.exists():
                index += 1
                archive = directory.with_name(directory.name + f'.partial-{index}')
            directory.rename(archive)
        simulation = orchestrator.run().model_dump(mode='json')
        final = orchestrator.environment.tools.db.model_dump(mode='json')
        for name, data in zip(names, (initial, simulation, final)):
            save(directory / f'{name}.json', data)
    evaluation_path = directory / 'evaluation.json'
    if evaluation_path.is_file():
        evaluation = load(evaluation_path)
    else:
        evaluation = evaluator.evaluate(task_id, initial_db=initial, final_db=final, simulation=simulation)
        save(evaluation_path, evaluation)
    return simulation, evaluation


def resume_grouping(batch, *, scope, directory):
    from .experience_grouping_v17 import prepare_grouping_request, run_experience_grouping
    from .experience_grouping_contract_v17 import bind_grouping_result
    if directory.exists():
        if (directory / 'grouping_request.json').exists() and load(directory / 'grouping_request.json') != prepare_grouping_request(batch, scope=scope):
            raise ValueError('Saved Grouping input differs from current experience')
        completed = directory / 'validated_groups.json'
        if completed.is_file():
            result = load(completed)
            rebound = bind_grouping_result(batch.payload, {'groups': result['groups']}, scope=scope)
            if any(result.get(key) != value for key, value in rebound.items()):
                raise ValueError('Saved Grouping result binding mismatch')
            return result
        # Explicit resume restarts the interrupted call; preserve its audit trail.
        index = 1
        archive = directory.with_name(f'grouping.interrupted-{index}')
        while archive.exists():
            index += 1
            archive = directory.with_name(f'grouping.interrupted-{index}')
        directory.rename(archive)
        # Diagnoses from an unvalidated grouping are never valid inputs for the
        # replacement grouping, even if a later model reuses the same IDs.
        stale_diagnosis = directory.parent / 'diagnosis'
        if stale_diagnosis.exists():
            index = 1
            archived_diagnosis = directory.parent / f'diagnosis.stale-grouping-{index}'
            while archived_diagnosis.exists():
                index += 1
                archived_diagnosis = directory.parent / f'diagnosis.stale-grouping-{index}'
            stale_diagnosis.rename(archived_diagnosis)
    return run_experience_grouping(batch, scope=scope, artifact_dir=directory)


def resume_diagnosis(request, *, directory):
    from .diagnosis_v18 import run_group_diagnosis
    from .diagnosis_prompt_v18 import build_diagnosis_request
    from .diagnosis_validation_v18 import validate_diagnosis_response
    from .information_boundary_v15 import unpack
    if directory.exists():
        if (directory / 'request.json').is_file():
            saved = load(directory / 'request.json')
            if any(saved.get(k) != v for k, v in build_diagnosis_request(request).items()):
                raise ValueError('Saved Diagnosis input differs from current group')
        validation = load(directory / 'validation.json') if (directory / 'validation.json').is_file() else {}
        if validation.get('status') == 'VALID':
            response = load(directory / 'response.json')
            if response.get('finish_reason') != 'stop' or response.get('refusal'):
                raise ValueError('Saved Diagnosis completion is invalid')
            checked = validate_diagnosis_response(response['raw_response'], request=request)
            if unpack(checked, 'V18_VALIDATED_DIAGNOSIS') != load(directory / 'validated_diagnosis.json'):
                raise ValueError('Saved Diagnosis differs from revalidated response')
            print(f'  REUSE Diagnosis {directory.name}', flush=True)
            return validation
        index = 1
        archive = directory.with_name(f'{directory.name}.attempt-{index}')
        while archive.exists():
            index += 1
            archive = directory.with_name(f'{directory.name}.attempt-{index}')
        directory.rename(archive)
    # One new attempt per explicit resume; failures still block compilation.
    return run_group_diagnosis(request, artifact_dir=directory)


def evolve_round(config, root, round_id, parent):
    from .information_boundary_v15 import capture_experience, project_oracle_supervision
    from .autonomous_gse_v15_benchmark_runtime import normalize_stored_simulation
    from .experience_cards_v17 import CapturedGroupingExperience, build_experience_cards
    from .experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingScope
    from .group_diagnosis_input_v17 import build_group_diagnosis_inputs
    from .diagnosis_validation_v18 import validate_diagnosis_response
    from .compiler_contract_v18 import CompilerDiagnosisSource, CompilerInput
    r = runtime(); registry = r.BenchmarkRegistry(); adapter = r.UnifiedEnvironmentAdapter(registry, frozen_user_prompts=load(FREEZE / "user_prompts.json"))
    evaluator = r.DeterministicEvaluatorDispatcher(registry)
    parent_path = root / 'parent_skill.md'; parent_path.write_bytes(parent.encode('utf-8'))
    initial_path = FREEZE / 'S0.md'
    skill_path = initial_path if parent == initial_path.read_bytes().decode('utf-8') else parent_path
    parent_digest = digest(parent.encode()); sources = []; contexts = {}; lineage = []
    def generate(job):
        index, task_id = job
        print(f'{round_id} Evolution {index}/32 {task_id}', flush=True)
        orchestrator, view = adapter.build_orchestrator(task_id, base_config=config['base_config'],
            seed=config['seed'], skill_path=skill_path, initial_skill_path=initial_path)
        directory = root / 'evolution_private' / f'T{index:03d}'
        simulation, evaluation = evolution_rollout(directory, orchestrator=orchestrator,
            evaluator=evaluator, task_id=task_id, seed=config['seed'])
        return index, task_id, view, simulation, evaluation

    # Each worker owns its orchestrator and task directory. Gather in fixed task order.
    with ThreadPoolExecutor(max_workers=8) as pool:
        generated = list(pool.map(generate, enumerate(config['tasks']['train'], 1)))
    for index, task_id, view, simulation, evaluation in generated:
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
    groups = resume_grouping(batch, scope=scope, directory=root / 'grouping')
    requests = build_group_diagnosis_inputs(sources, scope=scope, grouping_result=groups, parent_skill=parent)
    diagnoses = []; rejected = []
    for request in requests:
        group_id = request.provenance['group_id']; directory = root / 'diagnosis' / group_id
        print(f'{round_id} Diagnosis {group_id}', flush=True)
        result = resume_diagnosis(request, directory=directory)
        if result['status'] != 'VALID':
            rejected.append(group_id); continue
        validated = validate_diagnosis_response(load(directory / 'response.json')['raw_response'], request=request)
        diagnoses.append(CompilerDiagnosisSource('DIAGNOSIS/' + digest(validated.payload.encode()), request, validated))
    if rejected:
        raise ValueError(f'Diagnosis rejected: {rejected}; no partial compilation')
    value = CompilerInput(round_id, parent, parent_digest, tuple(diagnoses))
    return compile_and_edit(value, root)


def archive_attempt(directory):
    if directory.exists():
        index = 1
        while directory.with_name(f'{directory.name}.attempt-{index}').exists():
            index += 1
        directory.rename(directory.with_name(f'{directory.name}.attempt-{index}'))


def compile_and_edit(value, root):
    from .compiler_audit_v18 import run_compiler
    from .compiler_v18 import compile_edit_plan
    from .editor_contract_v18 import EditorInput
    from .editor_v18 import run_editor
    # Explicit resume preserves incomplete attempts before replaying from bound inputs.
    archive_attempt(root / 'compiler')
    archive_attempt(root / 'editor')
    result = run_compiler(value, artifact_dir=root / 'compiler')
    if result['status'] != 'VALID':
        raise ValueError('Compiler rejected')
    plan = compile_edit_plan(value)
    result = run_editor(EditorInput(value, plan), artifact_dir=root / 'editor')
    if result['status'] in ('NO_UPDATE', 'UNABLE'):
        return None, result['status']
    if result['status'] not in ('VALID', 'APPLIED_DETERMINISTIC'):
        raise ValueError('Editor rejected')
    return (root / 'editor/candidate_skill.md').read_bytes().decode('utf-8'), 'CANDIDATE'


def run_campaign(config, output, *, resume=False, total_rounds=None, pilot=False):
    from .monitor_benchmark_v18 import CurrentBenchmarkMonitor
    from .monitor_v18 import run_monitor
    if type(pilot) is not bool:
        raise ValueError('pilot must be boolean')
    if pilot and total_rounds is not None:
        raise ValueError('Pilot cannot extend the round limit')
    target_rounds = 1 if pilot else (config['rounds'] if total_rounds is None else total_rounds)
    if not pilot and (type(target_rounds) is not int or target_rounds < config['rounds']):
        raise ValueError('total_rounds must not reduce the original round limit')
    if total_rounds is not None and not resume:
        raise ValueError('Extending rounds requires --resume')
    if verify_freeze() != config:
        raise ValueError('Campaign configuration differs from freeze')
    execution = {'mode': 'PILOT' if pilot else 'FORMAL', 'round_limit': target_rounds}
    parent = (FREEZE / 'S0.md').read_bytes().decode('utf-8'); rounds = []
    if resume:
        if load(output / 'config.json') != config:
            raise ValueError('Resume configuration differs from original run')
        saved_execution = load(output / 'execution.json')
        if saved_execution.get('mode') != execution['mode']:
            raise ValueError('Resume execution mode differs from original run')
        if load(output / 'frozen_manifest.json') != load(FREEZE / 'manifest.json'):
            raise ValueError('Resume freeze differs from original run')
        previous = load(output / 'campaign.json')
        if previous['status'] == 'COMPLETE' and (previous.get('stop_reason') != 'ROUND_LIMIT' or target_rounds <= len(previous['rounds'])):
            raise ValueError('Campaign already complete; specify a larger --total-rounds to extend a round-limit run')
        rounds = previous['rounds']
        parent = (FREEZE / 'S0.md').read_bytes().decode('utf-8')
        for record in rounds:
            if record['decision'] == 'ACCEPT':
                parent = (output / record['round'] / 'editor/candidate_skill.md').read_bytes().decode('utf-8')
            if digest(parent.encode()) != record['retained_skill_sha256']:
                raise ValueError('Committed Skill digest mismatch')
        write_skill(output / 'current_skill.md', parent)
        if rounds and digest(parent.encode()) != rounds[-1]['retained_skill_sha256']:
            raise ValueError('Current Skill differs from last retained Skill')
        root = output / f'round-{len(rounds)+1:02d}'
        if (root / 'parent_skill.md').exists() and (root / 'parent_skill.md').read_bytes().decode('utf-8') != parent:
            raise ValueError('Resume Parent differs from interrupted round')
        # Keep the original run manifest and append the implementation used to resume.
        history = output / 'resume_history.json'
        entries = load(history) if history.exists() else []
        entries.append({'previous_campaign': previous, 'target_rounds': target_rounds, 'manifest': load(FREEZE / 'manifest.json')})
        save(history, entries)
    else:
        output.mkdir(parents=True, exist_ok=False)
        save(output / 'frozen_manifest.json', load(FREEZE / 'manifest.json'))
        save(output / 'config.json', config)
        save(output / 'execution.json', execution)
        write_skill(output / 'current_skill.md', parent)
        save(output / 'campaign.json', {'status': 'RUNNING', 'rounds': rounds})
    candidate, status = '', 'CANDIDATE'
    try:
        with frozen_policies(config):
            for index in range(len(rounds) + 1, target_rounds + 1):
                verify_freeze()
                round_id = f'round-{index:02d}'; root = output / round_id; root.mkdir(exist_ok=resume)
                if resume and (root / 'editor/validation.json').is_file() and load(root / 'editor/validation.json').get('status') in ('VALID', 'APPLIED_DETERMINISTIC'):
                    candidate = (root / 'editor/candidate_skill.md').read_bytes().decode('utf-8')
                    validation = load(root / 'editor/validation.json')
                    if validation['status'] not in ('VALID', 'APPLIED_DETERMINISTIC') or validation['candidate_sha256'] != digest(candidate.encode()) or validation['parent_skill_digest'] != digest(parent.encode()):
                        raise ValueError('Saved Candidate binding mismatch')
                    for name, expected in validation['artifact_sha256'].items():
                        if digest((root / 'editor' / name).read_bytes()) != expected:
                            raise ValueError('Saved Editor artifact changed')
                    status = 'CANDIDATE'
                else:
                    candidate, status = evolve_round(config, root, round_id, parent)
                if candidate is None:
                    rounds.append({'round': round_id, 'status': status, 'decision': 'RETAIN', 'retained_skill_sha256': digest(parent.encode())})
                    break
                backend = CurrentBenchmarkMonitor(artifact_dir=root / 'monitor_private/backend',
                    parent_skill=parent, candidate_skill=candidate, resume=resume, config=config, freeze=FREEZE)
                if backend.base_config != config['base_config'] or backend.seed != config['seed']:
                    raise ValueError('Monitor configuration differs from frozen Evolution')
                result = run_monitor(backend.monitor_input(round_id), backend=backend,
                    artifact_dir=root / 'monitor_private/monitor', max_workers=8, resume=resume)
                if result.get('status') != 'COMPLETE' or result.get('decision') not in ('ACCEPT', 'RETAIN'):
                    raise ValueError('Monitor incomplete')
                if result['decision'] == 'ACCEPT':
                    parent = candidate
                record = {'round': round_id, **result, 'retained_skill_sha256': digest(parent.encode())}
                rounds.append(record); save(root / 'round_result.json', record)
                save(output / 'campaign.json', {'status': 'RUNNING', 'rounds': rounds})
                write_skill(output / 'current_skill.md', parent)
                print(json.dumps(record), flush=True)
        save(output / 'campaign.json', {'status': 'COMPLETE', 'rounds': rounds,
            'stop_reason': status if candidate is None else 'ROUND_LIMIT'})
    except BaseException as exc:
        save(output / 'campaign.json', {'status': 'INCOMPLETE', 'rounds': rounds,
             'error_type': type(exc).__name__})
        raise
