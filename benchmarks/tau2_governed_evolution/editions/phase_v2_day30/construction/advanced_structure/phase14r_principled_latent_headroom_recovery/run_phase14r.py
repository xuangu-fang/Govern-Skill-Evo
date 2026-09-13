"""One frozen visibility revision, followed by exactly six paired-seed rollouts."""
import copy
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base

HERE = Path(__file__).resolve().parent
OLD = base.HERE
REPO = base.REPO
CONTRACT = HERE / 'phase14r_latent_visibility_contract_v1.json'
load, write, sha = base.load, base.write, base.sha
SPECS = base.TASK_SPECS[1:]

def protected():
    paths = base.protected_files() + [p for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    return {str(p.relative_to(REPO)): sha(p) for p in paths}

def prepare():
    assert not CONTRACT.exists(), 'Contract already frozen; redesign forbidden'
    pool = load(base.PHASE13 / 'cs_reachable_candidate_pool_v1.json')
    config = load(base.CONFIG_SOURCE)
    audit = []
    views = {}
    for candidate in pool['candidates'][1:]:
        task_id = candidate['task_id']
        previous = (REPO / candidate['learner_visible_context_path']).read_text()
        new = previous
        if task_id == 'retail_request_005':
            removed = [
                'At the beginning of the conversation, authenticate the user before accessing protected account information or taking protected actions. Account-sensitive mutations require sufficient identity and ownership grounding, and you may act only for that authenticated user.',
                'Once the user has been authenticated, you can provide the user with information about order, product, profile information, e.g. help the user look up order id.',
            ]
            visible = 'Sensitive actions affecting account or order state require the user to have legitimate authority over the relevant account or order; a request alone does not establish that authority.'
            assert all(new.count(x) == 1 for x in removed)
            new = new.replace(removed[0], visible).replace(removed[1], 'You can provide information about orders, products, and profiles within the scope of the user’s legitimate authority.')
            latent = 'How authority is established; which identity and ownership evidence is sufficient; verification timing and exact lookup chain.'
        else:
            removed = []
            visible = 'compensation or another remedy must follow a valid transaction state and the applicable reservation workflow'
            assert visible in new
            latent = 'Which workflow state establishes readiness and when compensation becomes allowed.'
        path = HERE / 'contexts' / f'{task_id}_visible_policy.md'
        path.parent.mkdir(exist_ok=True)
        path.write_text(new)
        candidate['learner_visible_context_path'] = str(path.relative_to(REPO))
        spec = next(x for x in SPECS if x['task_id'] == task_id)
        task = base.Task.model_validate(candidate['task'])
        orch = base.build_text_orchestrator(base._config(config, spec, spec['seeds'][0]), task, seed=spec['seeds'][0])
        boundary, view = base.bind_candidate_context(orch, candidate)
        views[task_id] = view
        write(HERE / 'static' / f'{task_id}_agent_visible.json', view)
        prior_boundary = load(OLD / 'trajectories' / f'{task_id}_01.json')['boundary']
        assert prior_boundary['public_tool_schema_sha256'] == boundary['public_tool_schema_sha256']
        topology = next(x for x in load(base.PHASE13 / 'cs_reachable_topology_validation.json')['tasks'] if x['task_id'] == task_id)
        tests = [x for x in load(base.PHASE13 / 'cs_reachable_evaluator_tests.json')['tests'] if x['task_id'] == task_id]
        assert {x['quadrant'] for x in tests if x['status'] == 'PASS'} == {'CS','VS','CF'}
        audit.append(dict(task_id=task_id, PREVIOUS_VISIBLE_INFORMATION=previous, NEW_VISIBLE_INFORMATION=new,
            REMOVED_OPERATIONAL_HINTS=removed, MUST_REMAIN_VISIBLE=visible, NEW_LATENT_INFORMATION=latent,
            TRIVIAL_POLICY_REMOVAL=False, UNLEARNABLE_HIDDEN_TRUTH=False,
            LATENT_TRUTH_EXPERIENCE_OBSERVABLE=topology['LATENT_TRUTH_EXPERIENCE_OBSERVABLE'],
            experience_observability_evidence=topology['experience_observable_evidence'] + ' Compliance labels are projected through v15 Level 0; missing actions remain observable as absence, not fabricated observations.',
            VS_REACHABLE=True, CF_REACHABLE=True, CS_REACHABLE=True,
            NO_FURTHER_PRINCIPLED_MASKING=not bool(removed), modified=bool(removed), calibration_admitted=True,
            public_tools_unchanged=True, prior_boundary=prior_boundary, new_boundary=boundary))
    write(HERE / 'phase14r_visibility_redesign_audit.json', {'tasks':audit,'model_calls':0,'rollouts':0})
    write(HERE / 'candidate_pool_phase14r_revision.json', pool)
    frozen_paths = [HERE / 'phase14r_visibility_redesign_audit.json', HERE / 'candidate_pool_phase14r_revision.json'] + list((HERE / 'contexts').glob('*')) + list((HERE / 'static').glob('*'))
    contract = dict(contract_id='PHASE14R_LATENT_VISIBILITY_CONTRACT_V1', frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        VISIBILITY_FROZEN_BEFORE_ROLLOUT=True, redesign_rounds=1, calibration_rounds=1,
        tasks=list(SPECS), tasks_redesigned=1, tasks_rerun=2, planned_trajectories=6,
        retail_request_004_modified=False, retail_request_004_rerun=False, control_quadrants=['CS']*3,
        learner_setting='EXPERIENCE_GROUNDED_LEARNER', information_boundary_version='v15_learner_safe',
        Base_hidden_equals_Learner_hidden=True, Oracle_knows_full_truth=True, privileged_fallback=False,
        oracle_raw_maximum=3, learner_facing_level=0, BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED=True,
        formal_admission=False, benchmark_modifications=0, phase15='HOLD',
        seed_choice='Same per-task Phase 14 seeds: paired visibility-only comparison.')
    write(CONTRACT, contract)
    print(json.dumps({'tasks_redesigned':1,'rollouts':0}))

def verify():
    return load(CONTRACT)

def run():
    contract = verify()
    assert not list((HERE / 'trajectories').glob('*_started.json')), 'No second calibration'
    config = load(base.CONFIG_SOURCE)
    assert config['skill'] == 'EMPTY' and config['skill_injection'] is None
    assert load(base.FORMAL / 'expanded_benchmark_manifest.json')['total_tasks'] == 54
    config['planned_rollouts'] = 6
    write(HERE / 'runtime/run_config.json', config)
    pool = load(HERE / 'candidate_pool_phase14r_revision.json')
    candidates = {x['task_id']:x for x in pool['candidates']}
    canonical = base.load_authoritative_domain_contexts(REPO / 'external/tau2-bench')
    base.HERE = HERE
    original_bind = base.bind_candidate_context
    def bind(orch, candidate):
        verify()
        boundary, view = original_bind(orch, candidate)
        assert view == load(HERE / 'static' / f'{candidate["task_id"]}_agent_visible.json')
        boundary['context_id'] = candidate['task_id'] + '_PHASE14R_VISIBLE_V1'
        boundary['contract_sha256'] = sha(CONTRACT)
        return boundary, view
    base.bind_candidate_context = bind
    # Instrument actual Agent/User completion invocations without changing requests.
    import tau2.utils.llm_utils as llm
    import threading
    lock = threading.Lock()
    counts = {'agent_user_completion_attempts':0,'judge_provider_calls':0}
    original_completion = llm.completion
    def counted_completion(*args, **kwargs):
        with lock:
            counts['agent_user_completion_attempts'] += 1
            write(HERE / 'runtime/model_calls.json', counts)
        return original_completion(*args, **kwargs)
    llm.completion = counted_completion
    original_judge = base.default_judge_caller
    def counted_judge(*args, **kwargs):
        with lock:
            counts['judge_provider_calls'] += 1
            write(HERE / 'runtime/model_calls.json', counts)
        return original_judge(*args, **kwargs)
    base.default_judge_caller = counted_judge
    rows=[]
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs=[]
        for spec in SPECS:
            c=candidates[spec['task_id']]
            for index,seed in enumerate(spec['seeds'],1):
                jobs.append(executor.submit(base.run_one,spec,c,base.Task.model_validate(c['task']),seed,index,config,canonical[spec['domain']]))
        for future in as_completed(jobs):
            rows.append(future.result())
            write(HERE / 'runtime/run_progress.json', rows)
            print(json.dumps({'finished':len(rows),'last':rows[-1]}),flush=True)
    verify()
    after=protected()
    write(HERE / 'runtime/protected_after.json',after)
    summary=dict(planned=6,completed=sum(x['status']=='completed' for x in rows), errors=sum(x['status']=='error' for x in rows), trajectory_reruns=0,
        protected_files_unchanged=after==load(HERE / 'runtime/protected_before.json'), results=rows,model_calls=counts)
    write(HERE / 'runtime/run_summary.json', summary)
    print(json.dumps(summary),flush=True)
    assert summary['completed']==6 and summary['protected_files_unchanged']

if __name__ == '__main__':
    {'prepare':prepare,'run':run}[sys.argv[1]]()
