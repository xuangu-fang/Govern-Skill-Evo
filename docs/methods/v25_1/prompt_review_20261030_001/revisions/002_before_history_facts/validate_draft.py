"""Read-only checks of draft inputs; writes reports/previews only inside this draft.

No model, executor, training, scoring or network calls. Run with the existing
SpreadsheetBench Python environment that supplies openpyxl.
"""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
DRAFT = Path(__file__).resolve().parent
ROOT = DRAFT.parents[3]
SOURCE_ROOT = ROOT / 'experiments/comparisons/v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run/v25/frozen_workspace'
SOURCE = SOURCE_ROOT / 'src/skill_evolution/v25/benchmarks/spreadsheetbench/prompts'
CONFIG = ROOT / 'experiments/configs/v25_sheetbench_upstream_actor_no_review_20261030.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    checks = []
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
    protected = json.loads((DRAFT/'protected_files_before.json').read_text())
    check(all(digest(ROOT/p) == expected for p, expected in protected.items()),
          'Runtime sources, selected old experiment prompts and base configuration unchanged')
    for p in (DRAFT/'baseline').glob('*.md'):
        check(p.read_bytes() == (SOURCE/p.name).read_bytes(), f'Exact frozen baseline: {p.name}')
    for name in ['actor_initial.md', 'actor_runtime_feedback.md', 'initial_skill.md']:
        check((DRAFT/'common'/name).read_bytes() == (DRAFT/'baseline'/name).read_bytes(),
              f'Common unchanged: {name}')
    old = (DRAFT/'baseline/preconditioner.md').read_text()
    new = (DRAFT/'v25_1/preconditioner.md').read_text()
    for start, end in [('# Preconditioner', '## 2.'), ('**D — Direction.**', '**S — Scope.**'),
                       ('**Explicit Keep.**', 'Before finalizing'), ('## 5.', None)]:
        a = old[old.index(start):old.index(end) if end else len(old)]
        b = new[new.index(start):new.index(end) if end else len(new)]
        check(a == b, f'Preconditioner preserved section: {start}')
    check(re.findall(r'\{\{(\w+)\}\}', old) == re.findall(r'\{\{(\w+)\}\}', new),
          'Preconditioner input template slots unchanged')
    changed_files = {}
    for group, names, patch in [
        ('common', ['actor_system.md', 'actor_initial.md', 'actor_runtime_feedback.md',
                    'execution_context.md', 'initial_skill.md'], '01_common_actor.patch'),
        ('v25_1', ['preconditioner.md'], '02_v25_1_preconditioner.patch')]:
        expected = ''
        for name in names:
            a = (DRAFT/'baseline'/name).read_text()
            b = (DRAFT/group/name).read_text()
            if a != b:
                changed_files[f'{group}/{name}'] = {'old_words': len(a.split()), 'new_words': len(b.split())}
            expected += ''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                fromfile=f'baseline/{name}', tofile=f'{group}/{name}'))
        check(expected == (DRAFT/'diffs'/patch).read_text(), f'Complete diff matches full files: {patch}')
    check(set(changed_files) == {'common/actor_system.md', 'common/execution_context.md', 'v25_1/preconditioner.md'},
          'Only three proposed prompt files differ from frozen baseline')

    spec = importlib.util.spec_from_file_location('draft_frozen_protocol', SOURCE.parent/'protocol.py')
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)
    # Change only this isolated Python module's template lookup, never repository files.
    protocol.PROMPTS = DRAFT/'common'
    config = json.loads(CONFIG.read_text())
    profile = config['actor_profile']
    check(config['method']['knowledge_review'] == 'disabled_v1', 'Both arms use review disabled')
    check(not {'verifier', 'repair'} & config['module_max_tokens'].keys(), 'No review stage budgets')
    skill = (DRAFT/'common/initial_skill.md').read_text()
    check(skill == config['initial_skill']['text'], 'Initial Skill equals configuration input')
    task = {'instruction': 'In Sheet1, sum the data in column A into B2.',
            'instruction_type': 'Cell-Level Manipulation', 'answer_region': "'Sheet1'!B2"}
    preview = '## Sheet: Sheet1 (dim=A1:B3, max_row=3, max_col=2)\nA1=Amount | B1=Total\nA2=2 | B2=\nA3=3 | B3='
    messages = protocol.initial_messages(task, skill, preview, profile)
    check(len(messages) == 2 and [m['role'] for m in messages] == ['system', 'user'], 'Frozen message structure preserved')
    check(messages[0]['content'].count('## Skill\n') == 1, 'Skill inserted exactly once')
    check(not re.search(r'\{\{\w+\}\}', json.dumps(messages)), 'Actor messages fully rendered')
    check(not re.search(r'(?i)budget|timeout|max_code_attempts|remaining|49152|16384', json.dumps(messages)),
          'No budget narration in synthetic Actor messages')
    check('data_only=True' in messages[0]['content'] and 'Scores, wrong-cell coordinates' in messages[0]['content'],
          'Actor receives formula and feedback conditions')
    no_skill = protocol.initial_messages(task, None, preview, profile)
    check('data_only=True' in no_skill[0]['content'] and 'no interactive tools' in no_skill[0]['content']
          and 'wrong-cell coordinates' in no_skill[0]['content'],
          'No Skill also receives basic execution, feedback and formula facts')
    check('## Skill\n' not in no_skill[0]['content'] and not re.search(r'\{\{\w+\}\}', json.dumps(no_skill)),
          'No Skill messages render without Skill section or unbound slots')
    feedback = protocol.feedback('execution_error', 'Synthetic execution error.', 1, 1, profile)
    check('budget' not in feedback['content'].lower() and not re.search(r'\{\{\w+\}\}', feedback['content']),
          'Original runtime error template renders without budget narration')
    context = protocol.execution_context(protocol.background(profile))
    rendered_preconditions = [protocol.render(p, {'execution_context': context}) for p in [old, new]]
    check(all(not re.search(r'\{\{\w+\}\}', p) for p in rendered_preconditions), 'Both Preconditioner contexts fully rendered')
    check(all(context in p for p in rendered_preconditions), 'Both arms receive the identical shared context')
    (DRAFT/'previews').mkdir(exist_ok=True)
    save(DRAFT/'previews/common_actor_messages.synthetic.json', messages)
    save(DRAFT/'previews/common_actor_no_skill_messages.synthetic.json', no_skill)
    save(DRAFT/'previews/runtime_feedback.synthetic.json', feedback)
    (DRAFT/'previews/common_execution_context.rendered.md').write_text(context+'\n')

    shared = {p.name: str(p.relative_to(DRAFT)) for p in sorted((DRAFT/'common').glob('*.md'))}
    arms = {}
    for name, preconditioner in [('v25_control', 'baseline/preconditioner.md'), ('v25_1', 'v25_1/preconditioner.md')]:
        arms[name] = {'shared_config': str(CONFIG.relative_to(ROOT)), 'shared_config_sha256': digest(CONFIG),
                      'prompt_bindings': {**shared, 'preconditioner.md': preconditioner}}
    differing = [key for key in arms['v25_control']['prompt_bindings']
                 if arms['v25_control']['prompt_bindings'][key] != arms['v25_1']['prompt_bindings'][key]]
    check(differing == ['preconditioner.md'], 'Only Preconditioner binding differs between arms')
    artifacts = {str(p.relative_to(DRAFT)): digest(p) for folder in ['baseline', 'common', 'v25_1', 'diffs']
                 for p in sorted((DRAFT/folder).glob('*')) if p.is_file()}
    save(DRAFT/'review_manifest.json', {
        'status': 'draft_pending_user_review', 'installed': False, 'launch_authorized': False,
        'frozen_prompt_source': str(SOURCE.relative_to(ROOT)), 'arms': arms, 'sha256': artifacts,
        'version_registration_pending': 'v25_1_current_update_evidence_to_behavior_v1',
        'note': 'Review metadata, not a runnable campaign config. Explicit isolated runtime wiring remains pending.'})
    check(all(digest(ROOT/p) == expected for p, expected in protected.items()), 'Protected files unchanged after validation')
    save(DRAFT/'offline_checks.json', {'status': 'passed', 'checks': checks, 'prompt_word_counts': changed_files,
        'model_requests': 0, 'program_executions': 0, 'training_runs': 0, 'test_runs': 0,
        'scope': 'Static draft/contract checks and synthetic message rendering only; no semantic model evaluation or runtime integration.'})
    print(json.dumps({'status': 'passed', 'checks': len(checks), 'model_requests': 0, 'draft': str(DRAFT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
