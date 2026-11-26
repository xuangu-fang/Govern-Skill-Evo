"""Read-only coverage and same-budget paired EM for independent OfficeQA Tests."""
import json
from pathlib import Path

from ..v26_1.reporting import costs, training_rounds
from .protocol import require
from .stages import read


def _completed_scores(root, tasks):
    journal = Path(root) / 'runs/actor/results.jsonl'
    scores = {}
    if journal.exists():
        with journal.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    break  # The final uncommitted line can be recovered on resume.
                row = json.loads(line)
                uid, record = row['id'], row['record']
                require(uid == record['task_id'] and uid in tasks and uid not in scores,
                        'Invalid Test journal task')
                em = record['metrics']['em']
                budget = record['actor']['max_completion_tokens']
                require(em in (0, 1) and type(budget) is int and budget > 0,
                        'Invalid Test EM or output budget')
                scores[uid] = (int(em), budget)
    return scores


def pending_test(root, tasks):
    scores = _completed_scores(root, tasks)
    return {'completed': len(scores), 'correct': sum(em for em, _ in scores.values()),
            'pending': [uid for uid in tasks if uid not in scores]}


def compare_tests(evaluation, baseline):
    runs = [Path(root).resolve() for root in (evaluation, baseline)]
    current, previous = [read(root / 'evaluation.json') for root in runs]
    require(all(current[key] == previous[key] for key in ('revision', 'scorer_profile')),
            'Test release or scorer differs')
    new, old = [_completed_scores(root, identity['tasks'])
                for root, identity in zip(runs, (current, previous))]
    common = [uid for uid in current['tasks'] if uid in new and uid in old and new[uid][1] == old[uid][1]]
    gains = [uid for uid in common if new[uid][0] > old[uid][0]]
    losses = [uid for uid in common if new[uid][0] < old[uid][0]]
    return {'evaluation': str(runs[0]), 'baseline': str(runs[1]), 'common': len(common),
            'evaluation_correct': sum(new[uid][0] for uid in common),
            'baseline_correct': sum(old[uid][0] for uid in common),
            'gains': len(gains), 'losses': len(losses), 'gain_ids': gains, 'loss_ids': losses}
