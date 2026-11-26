"""Check this draft package only; no module installation or model execution."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import socket
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def blocked(*args, **kwargs):
    raise AssertionError('This design check cannot access networks or spawn processes')


def main():
    manifest = json.loads((HERE / 'source_manifest.json').read_text())
    for relative, expected in manifest['source_sha256'].items():
        check(sha(ROOT / relative) == expected, f'Source drift: {relative}')
    for relative, expected in manifest['actor_and_data_before'].items():
        check(sha(ROOT / relative) == expected, f'Actor or data changed: {relative}')
    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p, scoring
    from src.skill_evolution.v27.contracts.editor import apply_patch as apply_actual_diff
    base = p.build_messages(question='Q', context='C', skill=None)[0]['content']
    runtime = (ROOT / 'src/skill_evolution/v27/benchmarks/lmb/context/actor_runtime.md').read_text().strip()
    prompts = {name: (HERE / 'prompts' / f'{name}.md').read_text()
               for name in manifest['proposed_versions']}
    for name, text in prompts.items():
        check(text.count('<actor_base_protocol>') == 1 and text.count('</actor_base_protocol>') == 1, 'Missing/duplicate Actor quote')
        check(text.split('<actor_base_protocol>\n')[1].split('\n</actor_base_protocol>')[0] == base, 'Base Actor protocol changed')
        check(runtime in text, 'Runtime quote changed')
        check(not re.search(r'\bLMB\b|five options|label-only|mapped reference option|theorem_type|A, B, C, D', text), 'LMB task residue')
        original = (ROOT / 'src/skill_evolution/v27/benchmarks/lmb/prompts' / f'{name}.md').read_text()
        diff = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                       fromfile=f'v27/{name}.md', tofile=f'v28-draft/{name}.md'))
        check((HERE / 'diffs' / f'{name}.diff').read_text() == diff, 'Draft diff does not reproduce source changes')
    check('Do not read historical Memory or impose a fixed Update count.' in prompts['diagnosis'], 'Missing v27 quantity policy')
    check(not re.search(r'at most two|two-Update|ceiling|Defer lower-priority repairs', prompts['diagnosis']), 'Discarded v25.2 selection rule remains')
    check('Judge refinements by useful behavioral difference' not in prompts['preconditioner'] and
          'Prefer replacing or consolidating' not in prompts['preconditioner'], 'Discarded v25.2 refinement paragraph remains')
    check(manifest['method_baseline'] == 'v27' and manifest['v25_2_additions_inherited'] is False
          and manifest['planned_ablations'] == [], 'Method scope differs from user decision')
    check('not structurally split/merge Update IDs' in prompts['preconditioner'], 'Update ID contract omitted')
    feedback = 'src/skill_evolution/v27/benchmarks/lmb/prompts/method_validation_feedback.md'
    check((HERE / 'prompts/method_validation_feedback.md').read_bytes() == (ROOT / feedback).read_bytes(), 'Feedback template changed')
    cfg = json.loads((ROOT / 'experiments/configs/v27_lmb53_epoch1_deepseek_flash.json').read_text())
    check(cfg['method']['knowledge_review'] == manifest['review_policy'] == 'disabled_v1', 'Review policy differs')

    examples = json.loads((HERE / 'evidence_examples.json').read_text())
    expected_fields = {'grouping': {'parent', 'runs'}, 'diagnosis': {'parent', 'runs', 'grouping'},
                       'preconditioner': {'parent', 'plan', 'runs', 'memory'}, 'editor': {'parent', 'plan'},
                       'replay': {'parent', 'diff', 'plan', 'runs', 'pairs', 'memory'}}
    for module, fields in expected_fields.items():
        check(set(examples[module]) == fields, f'{module}: visibility fields differ')
    for module in ('preconditioner', 'replay'):
        check(examples[module]['memory'] == {'format': 'memory_knowledge_only_v1', 'entries': []}, 'Unexpected historical view')
    replay = examples['replay']
    candidate = apply_actual_diff(replay['parent'], replay['diff'])
    check(bool(re.search(r'^@@ -\d', replay['diff'], re.M)), 'actual diff must retain numbered source format')
    refs = set()
    for run in replay['runs']:
        check(set(run) == {'ref', 'task_id', 'run_id', 'initial', 'attempts', 'outcome'}, 'Run fields differ')
        check(len(run['attempts']) == 1, 'Attempts is not one visible model round')
        initial, attempt, outcome = run['initial'], run['attempts'][0], run['outcome']
        check(set(initial['task']) == {'question', 'context'}, 'Private task fields leaked')
        check(set(attempt['assistant']) == {'role', 'content'}, 'Hidden response fields leaked')
        check(attempt['request_messages'] == initial['messages'], 'Request messages differ')
        skill = replay['parent'] if run['ref'].startswith('P') else candidate
        check(initial['messages'] == list(p.build_messages(**initial['task'], skill=skill)), 'Input messages not reproduced exactly')
        answer, metrics = scoring.score(attempt['assistant']['content'], outcome['reference_answers'])
        check(outcome['answer'] == answer and outcome['score'] == metrics, 'Derived answer/score differs')
        check(outcome['termination'] == 'stop' and outcome['status'] == 'completed', 'Incomplete example run')
        check(outcome['model_rounds'] == 1 and outcome['tool_calls'] == 0 and 1 <= outcome['api_requests'] <= 6, 'Invalid execution counters')
        refs |= {run['ref'], initial['ref'], attempt['ref'], outcome['ref']}
    by_ref = {r['ref']: r for r in replay['runs']}
    for pair in replay['pairs']:
        for side in ('parent', 'candidate'):
            r = by_ref[pair[side]]
            check(r['task_id'] == pair['task_id'], 'Paired task mismatch')
            result = {k: r['outcome'][k] for k in ('status', 'model_rounds', 'tool_calls', 'api_requests')} | r['outcome']['score']
            check(result == pair[side + '_result'], 'Paired score mismatch')
    plan = examples['preconditioner']['plan']
    check(set(ref for u in plan['updates'] for ref in u['basis']) <= refs | {'G1'}, 'Invented basis reference')
    check(by_ref['P1']['outcome']['score'] == {'em': 0, 'f1': .8} and
          by_ref['Q1']['outcome']['score'] == {'em': 1, 'f1': 1}, 'Synthetic partial F1 example changed')
    check(scoring.score('York New', ['New York'])[1] == {'em': 0, 'f1': 1}, 'F1=1/EM=0 distinction failed')
    outputs = [q for q in HERE.rglob('*') if q.is_file() and q.name != 'static_checks.json' and '__pycache__' not in q.parts]
    report = {'status': 'draft_static_checks_passed', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'Design sources, prompt quotes/diffs, visibility shapes and synthetic evidence only; not runtime or semantic acceptance.',
              'five_complete_prompts': list(prompts), 'prompt_versions': manifest['proposed_versions'],
              'method_baseline': 'v27', 'v25_2_additions_inherited': False, 'planned_ablations': [],
              'source_files_verified': len(manifest['source_sha256']),
              'actor_and_data_files_unchanged': len(manifest['actor_and_data_before']),
              'synthetic_paired_runs_checked': 2, 'actual_diff_format': 'numbered_unified_diff',
              'model_patch_format': 'unnumbered_diff_v1', 'runtime_installed': False,
              'training_started': False, 'test_started': False, 'model_requests': 0,
              'files_sha256': {str(q.relative_to(HERE)): sha(q) for q in sorted(outputs)}}
    (HERE / 'static_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files_sha256'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with patch.object(socket.socket, 'connect', blocked), patch.object(socket.socket, 'connect_ex', blocked), \
         patch('socket.create_connection', blocked), patch('subprocess.Popen', blocked):
        main()
