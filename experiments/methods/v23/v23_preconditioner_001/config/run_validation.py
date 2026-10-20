"""One-shot archived validation; run at repository root with PYTHONPATH=.
Refuse an existing call directory: at most one request, no retries or episodes.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23 import preconditioner as pc
from src.skill_evolution.v23.prompts import execution_context

EXP = Path('experiments/methods/v23/v23_preconditioner_001')
ROOT = Path('artifacts/methods/v23/v23_preconditioner_001')
LIVE = ROOT/'live'
UPSTREAM = Path('artifacts/methods/v23/v23_prompt_alignment_001')
assert not LIVE.exists(), 'This experiment must not be retried'
log = (ROOT/'offline_tests.txt').read_text()
assert '284 passed, 19 subtests passed' in log and 'failed' not in log and 'skipped' not in log
load_dotenv('.env', override=False)
assert os.environ.get('OPENAI_API_KEY')
base_url = os.environ['OPENAI_BASE_URL']
assert urlparse(base_url).hostname == 'api.deepseek.com'
config = pc.call_configuration(base_url=base_url, model='deepseek-flash', max_tokens=16384, timeout=300)
assert config == json.loads((UPSTREAM/'diagnosis/run.json').read_text())['call_config']
saved = pc.read_upstream(UPSTREAM/'grouping', UPSTREAM/'diagnosis')
payload = pc.preconditioner_input(saved)
messages = pc.messages_for(saved)
assert payload['parent'] is None and payload['memory'] == []
assert len(payload['runs']) == 4 and sum(len(r['steps']) for r in payload['runs']) == 93
assert len(payload['grouping']['groups']) == 2
assert len(payload['plan']['updates']) == len(payload['plan']['checks']) == 3
assert payload['runs'] == saved['facts']['runs'] and payload['command_sets'] == saved['facts']['command_sets']
assert [s['task_id'] for s in saved['sources']] == [f'train:{i:04}' for i in range(12,16)]
assert messages[0]['content'].count(execution_context(saved['background'])) == 1
size = len(json.dumps(messages, ensure_ascii=False))
assert size <= 100000

def snapshot(directory):
    return {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob('*') if p.is_file()}

old_archives = {name: snapshot(UPSTREAM/name) for name in ('grouping', 'diagnosis')}
for name, contents in old_archives.items():
    for file, data in contents.items():
        destination = ROOT/'original_archives'/name/file
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(data)
source_names = ('preconditioner.py', 'preconditioner_prompt.md', 'execution_context.md', 'prompts.py', 'facts.py', 'grouping.py', 'diagnosis.py', 'grouping_prompt.md', 'diagnosis_prompt.md')
source_dir = EXP/'config/source'; source_dir.mkdir()
for name in source_names:
    (source_dir/name).write_bytes((Path('src/skill_evolution/v23')/name).read_bytes())
criteria = [
    'understands original Plan and preserves its goal and useful behavior',
    'checks Actor-visible triggering conditions and limited history',
    'distinguishes existing base protocol from additional guidance',
    'adjusts only with supplied factual or capability grounds, or reasonably keeps',
    'does not invent historical responses or attribute current evidence to historical benefit',
    'does not withdraw dependencies or introduce unsupported scope changes',
    'checks reference effective Updates and are useful behavioral questions',
    'effective Plan order, unchanged goal, inherited basis and independent adjustment basis match deterministic compilation',
    'reports semantic weaknesses without prompt patches or resampling',
]
write_record(EXP/'config/plan.json', {
    'frozen_at': datetime.now(timezone.utc).isoformat(), 'call_config': config,
    'grouping_directory': str(UPSTREAM/'grouping'), 'diagnosis_directory': str(UPSTREAM/'diagnosis'),
    'output_directory': str(LIVE), 'tasks': [s['task_id'] for s in saved['sources']],
    'runs': 4, 'steps': 93, 'groups': 2, 'original_updates': 3, 'original_checks': 3,
    'parent': None, 'memory': [], 'input_chars': size, 'max_input_chars': 100000,
    'max_calls': 1, 'automatic_retries': 0, 'upstream_calls': 0, 'new_environment_episodes': 0,
    'semantic_check_criteria': criteria,
})
write_record(ROOT/'frozen_input.json', payload)
write_record(ROOT/'frozen_messages.json', messages)
print(f'Offline tests passed; input and configuration frozen ({size} characters). Starting the ONLY call.', flush=True)
generate = pc.live_generator(base_url=base_url, key=os.environ['OPENAI_API_KEY'], model='deepseek-flash', max_tokens=16384, timeout=300)
try:
    result = pc.run_preconditioner(UPSTREAM/'grouping', UPSTREAM/'diagnosis', LIVE,
                                  generate=generate, max_input_chars=100000, call_config=config)
except BaseException:
    write_record(EXP/'results/stop.json', {'technical_failure': True, 'retry_allowed': False,
                 'validation': json.loads((LIVE/'validation.json').read_text()) if (LIVE/'validation.json').exists() else None,
                 'usage': json.loads((LIVE/'response.json').read_text()).get('usage') if (LIVE/'response.json').exists() else None})
    raise
print('Response valid; checking zero-call reuse and deterministic compilation.', flush=True)
def forbidden(*_): raise AssertionError('Additional call forbidden')
before = snapshot(LIVE)
assert pc.run_preconditioner(UPSTREAM/'grouping', UPSTREAM/'diagnosis', LIVE, generate=forbidden, call_config=config) == result
assert before == snapshot(LIVE)
assert all(snapshot(UPSTREAM/name) == contents for name,contents in old_archives.items())
assert all((source_dir/name).read_bytes() == (Path('src/skill_evolution/v23')/name).read_bytes() for name in source_names)
response = json.loads((LIVE/'response.json').read_text())
meta = json.loads((LIVE/'run.json').read_text())
request = json.loads((LIVE/'request.json').read_text())
assert request['attempts'] == response['api_attempts'] == 1
assert request['body']['messages'] == messages
assert meta['call_config'] == config
for name in ('preconditioner', 'effective_plan'):
    write_record(EXP/f'results/{name}.json', result[name])
summary = {'tests': {'passed': 284, 'subtests': 19, 'failed': 0, 'skipped': 0},
           'decision': result['preconditioner']['decision'],
           'adjustments': len(result['preconditioner']['adjustments']),
           'effective_updates': len(result['effective_plan']['updates']) if result['effective_plan'] else 0,
           'effective_checks': len(result['effective_plan']['checks']) if result['effective_plan'] else 0,
           'input_chars': size, 'api_attempts': response['api_attempts'],
           'response_model': response['response_model'], 'finish_reason': response['finish_reason'],
           'usage': response['usage'],
           'elapsed_seconds': (datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds(),
           'reuse_verified': True, 'additional_reuse_calls': 0, 'upstream_archives_unchanged': True,
           'facts_equal_saved_source': True, 'prompt_and_source_snapshots_unchanged': True,
           'upstream_calls': 0, 'new_environment_episodes': 0, 'memory_entries': 0,
           'historical_response_preconditioning_validated': False,
           'monetary_cost': None, 'monetary_cost_note': 'API reports token usage, not a billed monetary amount; no estimate made.'}
write_record(EXP/'results/summary.json', summary)
print(json.dumps(summary, indent=2), flush=True)
