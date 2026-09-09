"""Explicit integration points for future calibration; importing runs nothing."""
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
UCA01='airline_unified_uca01_gjlsxx_nyc_date_budget'

def evaluate_success(task, initial_db, final_db, native_evaluator):
    """native_evaluator(task) preserves the runner's existing tau2 evaluation call."""
    task_id=task.id if hasattr(task,'id') else task['id']
    if task_id!=UCA01:
        return native_evaluator(task)
    spec=importlib.util.spec_from_file_location('uca01_success',HERE/'evaluators/uca01_success.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.evaluate(initial_db,final_db)

def bind_agent_context(orchestrator, domain):
    # Apply established description-only overrides, then bind immutable Final policy.
    from benchmarks.tau2_governed_evolution.phase_a_success_v2.run_success_v2 import apply_context
    apply_context(orchestrator,domain)
    manifest=json.loads((HERE/'contexts/context_manifest.json').read_text())
    context=manifest['contexts'][domain]
    orchestrator.agent.domain_policy=(REPO/context['policy_path']).read_text()
    return context['context_id']

def canonical_judge_policy(domain):
    contract=json.loads((HERE/'evaluators/compliance_contract.json').read_text())
    return (REPO/contract['policy_paths'][domain]).read_text()
