"""Independent, fixed-Test evaluation. No optimizer or Memory publication."""
import json
from pathlib import Path

from src.adapters.officeqa.execution import _locked, atomic_json, EXECUTION_CONFIG
from .facts import require
from .storage import load_skill
from .stages import read, freeze, freeze_text
from .benchmarks.officeqa import protocol as p


TEST_IDS = tuple(read(Path(__file__).with_name('resources') / 'officeqa_test_ids.json'))
VERSION = 'v26_officeqa_test_v1'
ROLE = {'split': 'test', 'role': 'evaluation'}


class ArchiveTransport:
    """Metadata-only binding for reports and completed-journal recovery."""
    def __init__(self, metadata):
        self._metadata = metadata

    def metadata(self):
        return dict(self._metadata)

    def with_output_limit(self, limit):
        return ArchiveTransport({**self.metadata(), 'max_completion_tokens': limit})

    def __call__(self, **kwargs):
        raise RuntimeError('Archive-only evaluation cannot issue Actor requests')


def _tasks(adapter):
    adapter._bound()
    require(len(TEST_IDS) == len(set(TEST_IDS)) == 172, 'Invalid frozen Test inventory')
    require(tuple(adapter.dataset.splits['test']) == TEST_IDS,
            'Evaluation requires exactly the frozen 172 Test IDs in manifest order')
    require(adapter.gate_metric is None, 'Independent Test evaluation must not configure a Gate')
    return list(TEST_IDS)


def _contract(adapter):
    return {**{name: p.digest(text) for name, text in adapter.frozen_files().items()},
            'fixed_test_ids': p.digest(TEST_IDS)}


def _journal(root):
    """Read committed rows without repairing/truncating the common journal."""
    path = root / 'batch/actor/results.jsonl'
    rows, seen = [], set()
    if path.exists():
        with path.open('rb') as handle:
            for line in handle:
                if not line.endswith(b'\n'): break
                row = json.loads(line)
                require(row['id'] == row['record']['task_id'] and row['id'] not in seen
                        and row['id'] in TEST_IDS, 'Invalid Test journal identity')
                seen.add(row['id']); rows.append(row)
    return rows


def _verify(root, adapter):
    tasks = _tasks(adapter); plan = read(root / 'plan.json')
    require(plan['version'] == VERSION and plan['tasks'] == tasks and plan['role'] == ROLE,
            'Test plan identity differs')
    require(plan['execution'] == {**EXECUTION_CONFIG, 'workers': adapter.workers} and plan['contract'] == _contract(adapter),
            'Frozen Test implementation changed')
    require(plan['runtime'] == adapter.runtime_snapshot({'batches': [tasks]}),
            'Frozen Test data, sources or Actor configuration changed')
    skill = plan['skill']
    require(skill['mode'] in ('fixed', 'none'), 'Invalid frozen Test Skill')
    if skill['mode'] == 'fixed':
        freeze_text(root / 'skill.md', skill['text'], read_only=True)
    else:
        require(skill['text'] is None and not (root / 'skill.md').exists(), 'Unexpected Test Skill')
    return plan


def _summary(root, adapter):
    plan = _verify(root, adapter); rows = _journal(root)
    done = [row['id'] for row in rows]
    result = {'version': VERSION, 'split': 'test', 'total': 172, 'completed': len(done),
              'pending_ids': [uid for uid in TEST_IDS if uid not in done],
              'status': 'incomplete', 'em': None, 'f1': None,
              'skill_sha256': p.digest(plan['skill']['text']),
              'plan_sha256': p.digest(plan), 'actor': plan['runtime']['actor'],
              'result_order': 'completion', 'optimization_updates': False,
              'records_verified': False}
    marker = root / 'records.json'
    if not marker.exists():
        result['awaiting_record_recovery'] = len(done) == 172
        return result
    records = read(marker)
    require(isinstance(records, list) and len(records) == 172
            and len({r['task_id'] for r in records}) == 172
            and {r['task_id'] for r in records} == set(TEST_IDS), 'Incomplete Test record coverage')
    require([r['execution'] for r in records] == [r['record'] for r in rows],
            'Test records differ from the committed Actor journal')
    per_case = []
    for record in records:
        adapter.check_record(record, record['task_id'], plan['skill']['text'], ROLE)
        raw = record['execution']; metrics = raw['metrics']
        per_case.append({'task_id': record['task_id'], 'em': metrics['em'], 'f1': metrics['f1'],
                         'answer': raw['answer'], 'fail_reason': raw['raw_result']['fail_reason']})
    result.update(status='complete', em=sum(r['em'] for r in per_case) / 172,
                  f1=sum(r['f1'] for r in per_case) / 172,
                  exact_matches=sum(r['em'] == 1 for r in per_case), cases=per_case,
                  records_verified=True,
                  actor_requests=sum(r['execution']['raw_result']['api_requests'] for r in records),
                  tool_calls=sum(r['execution']['raw_result']['n_tool_calls'] for r in records))
    return result


def _write_report(root, result):
    # The report is derived data: it can always be regenerated from the journal.
    atomic_json(root / 'report.json', result)
    lines = ['# V26 OfficeQA Test', '', f"Status: {result['status']}",
             f"Completed: {result['completed']} / 172", '',
             'Test results do not enter optimization or Memory updates.', '']
    if result['status'] == 'complete':
        lines += [f"EM: {result['em']:.8f}", f"Token F1: {result['f1']:.8f}", '',
                  '| Task | EM | F1 |', '|---|---:|---:|']
        lines += [f"| {r['task_id']} | {r['em']} | {r['f1']:.8f} |" for r in result['cases']]
    else:
        lines += ['EM and F1 are withheld until all 172 cases are recovered and validated.']
    temporary = root / 'report.md.tmp'
    temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    temporary.replace(root / 'report.md')


def report_evaluation(directory, *, adapter):
    """Validate and regenerate a report without invoking the Actor."""
    root = Path(directory).resolve()
    require((root / 'plan.json').is_file(), 'Missing Test plan')
    with _locked(root):
        result = _summary(root, adapter)
        _write_report(root, result)
        return result


def run_evaluation(directory, *, adapter, skill_file, resume=False):
    """Reuse the common Actor's journal and attempt state; never retry a batch."""
    root = Path(directory).resolve(); tasks = _tasks(adapter)
    skill = load_skill(skill_file)  # None is an explicitly requested No Skill arm.
    protected = [adapter.dataset.root.resolve(), adapter.runtime.parsed_root.resolve()]
    if skill_file is not None: protected.append(Path(skill_file).resolve())
    require(all(not root.is_relative_to(path) and not path.is_relative_to(root) for path in protected),
            'Use a separate evaluation directory outside data and the source Skill')
    # Do not let an evaluation write anywhere inside an existing Campaign.
    require(not any((path / 'state.json').exists() and (path / 'config.json').exists()
                    for path in (root, *root.parents)), 'Test output cannot be inside a Campaign')
    with _locked(root):
        exists = (root / 'plan.json').exists()
        if exists:
            require(resume, 'Existing Test run requires explicit resume')
            plan = read(root / 'plan.json')
            require(plan['skill'] == skill, 'Frozen Test Skill differs')
        else:
            require(not any(path.name != '.execution.lock' and not path.name.startswith('.plan.json')
                            for path in root.iterdir()), 'Nonempty directory has no Test plan')
            plan = {'version': VERSION, 'tasks': tasks, 'role': ROLE, 'skill': skill,
                    'execution': {**EXECUTION_CONFIG, 'workers': adapter.workers}, 'contract': _contract(adapter),
                    'runtime': adapter.runtime_snapshot({'batches': [tasks]})}
            atomic_json(root / 'plan.json', plan)
        # A crash between plan commit and Skill copy is recoverable without new identity.
        if skill['mode'] == 'fixed': freeze_text(root / 'skill.md', skill['text'])
        _verify(root, adapter)
        if not (root / 'records.json').exists():
            require(not isinstance(adapter.transport, ArchiveTransport) or len(_journal(root)) == 172,
                    'Pending Test cases require an explicit Actor transport and credentials')
            try:
                records = adapter.actor_batch(tasks, root / 'skill.md' if skill['mode'] == 'fixed' else None,
                                              root / 'batch', ROLE, final=True)
                freeze(root / 'records.json', records)
            except Exception:
                _write_report(root, _summary(root, adapter))
                raise
        result = _summary(root, adapter)
        _write_report(root, result)
        return result
