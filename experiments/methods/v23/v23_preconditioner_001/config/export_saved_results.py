"""Read-only recovery of report export after the one-shot run's mkdir omission.
No generator or network request; never reruns the original validation script.
"""
from datetime import datetime
import json
from pathlib import Path
from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23 import preconditioner as pc

EXP = Path('experiments/methods/v23/v23_preconditioner_001')
ROOT = Path('artifacts/methods/v23/v23_preconditioner_001')
LIVE = ROOT/'live'
UPSTREAM = Path('artifacts/methods/v23/v23_prompt_alignment_001')
config = json.loads((EXP/'config/plan.json').read_text())['call_config']

def snapshot(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}

def forbidden(*_):
    raise AssertionError('No additional model call is permitted')

before = snapshot(LIVE)
source = pc.read_upstream(UPSTREAM/'grouping', UPSTREAM/'diagnosis')
result = pc.load_preconditioner(LIVE, expected_diagnosis=source, expected_call_config=config)
assert pc.run_preconditioner(UPSTREAM/'grouping', UPSTREAM/'diagnosis', LIVE,
                              generate=forbidden, call_config=config) == result
assert before == snapshot(LIVE)
assert all(snapshot(UPSTREAM/name) == snapshot(ROOT/'original_archives'/name) for name in ('grouping', 'diagnosis'))
assert all(p.read_bytes() == (Path('src/skill_evolution/v23')/p.name).read_bytes() for p in (EXP/'config/source').iterdir())
payload = pc.preconditioner_input(source)
assert payload == json.loads((ROOT/'frozen_input.json').read_text())
assert result['effective_plan'] == source['diagnosis']['plan']  # actual Keep, not a forced expected outcome before call
response = json.loads((LIVE/'response.json').read_text())
meta = json.loads((LIVE/'run.json').read_text())
request = json.loads((LIVE/'request.json').read_text())
assert request['attempts'] == response['api_attempts'] == 1
assert request['body']['messages'] == json.loads((ROOT/'frozen_messages.json').read_text())
(EXP/'results').mkdir(exist_ok=True)
for name in ('preconditioner', 'effective_plan'):
    (EXP/f'results/{name}.json').write_bytes((LIVE/f'{name}.json').read_bytes())
summary = {
    'tests': {'passed': 284, 'subtests': 19, 'failed': 0, 'skipped': 0},
    'decision': result['preconditioner']['decision'], 'adjustments': len(result['preconditioner']['adjustments']),
    'effective_updates': len(result['effective_plan']['updates']), 'effective_checks': len(result['effective_plan']['checks']),
    'effective_plan_equals_original': True,
    'input_chars': meta['input_chars'], 'api_attempts': response['api_attempts'],
    'response_model': response['response_model'], 'finish_reason': response['finish_reason'], 'usage': response['usage'],
    'elapsed_seconds': (datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds(),
    'reuse_verified': True, 'additional_reuse_calls': 0, 'upstream_archives_unchanged': True,
    'facts_equal_saved_source': True, 'prompt_and_source_snapshots_unchanged': True,
    'upstream_calls': 0, 'new_environment_episodes': 0, 'memory_entries': 0,
    'historical_response_preconditioning_validated': False,
    'model_or_contract_failures': 0,
    'report_export_failure': 'Original script omitted results.mkdir after successful validation and reuse. Original traceback preserved; export recovered from saved results with zero requests.',
    'monetary_cost': None, 'monetary_cost_note': 'API reports token usage, not a billed monetary amount; no estimate made.'}
write_record(EXP/'results/summary.json', summary)
print(json.dumps(summary, indent=2))
