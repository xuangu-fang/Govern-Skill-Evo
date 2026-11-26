"""Native SearchQA metrics, ordinary-content-only parsing and pure EM Gate.

No HTTP or retry loop is provided here. Campaign integration must establish
archive, data, model, prompt and Skill identities before comparing scores.
"""
import math
from skilladam.benchmarks.searchqa.evaluation import best_token_f1, exact_match
from skilladam.benchmarks.searchqa.rollout import extract_answer
from .protocol import nonempty_text, validate_answers


def score(content, gold_answers):
    if not isinstance(content, str):
        raise ValueError('Content must be text')
    validate_answers(gold_answers)
    # Never pass the native extractor an `answer` override or reasoning field.
    prediction, raw = extract_answer({'response': content})
    metrics = {'em': exact_match(prediction, gold_answers),
               'f1': best_token_f1(prediction, gold_answers)}
    validate_metrics(metrics)
    return {'raw_content': raw, 'extracted_answer': prediction}, metrics


def score_response(raw_response, gold_answers):
    """Score a completed API envelope using exactly v27's termination checks.

    RequestFailure propagates unchanged: length/malformed response is retryable;
    refusal/tools are terminal under v27's classification. This function never
    retries, archives, or substitutes a zero score for an incomplete response.
    """
    from ....v27.benchmarks.lmb.actor import parse_response
    validate_answers(gold_answers)
    content, _ = parse_response(raw_response)
    return score(content, gold_answers)


def validate_metrics(metrics):
    if not isinstance(metrics, dict) or set(metrics) != {'em', 'f1'}:
        raise ValueError('Expected em and f1 metrics')
    if type(metrics['em']) not in (int, float) or metrics['em'] not in (0, 1):
        raise ValueError('EM must be binary')
    f1 = metrics['f1']
    if type(f1) not in (int, float) or not math.isfinite(f1) or not 0 <= f1 <= 1:
        raise ValueError('F1 must be finite and within [0, 1]')
    if metrics['em'] == 1 and f1 != 1:
        raise ValueError('Exact match must also have F1=1')
    return metrics


def _indexed_scores(records, expected_ids):
    if not isinstance(expected_ids, list) or not expected_ids:
        raise ValueError('Expected task IDs must be a non-empty list')
    for task_id in expected_ids:
        nonempty_text(task_id, 'Expected task ID')
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError('Duplicate expected task ID')
    if not isinstance(records, list):
        raise ValueError('Scores must be a list')
    indexed = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {'task_id', 'metrics'}:
            raise ValueError('Expected a task_id and completed metrics')
        task_id = nonempty_text(record['task_id'], 'Task ID')
        if task_id in indexed:
            raise ValueError('Duplicate task score')
        indexed[task_id] = validate_metrics(record['metrics'])
    if set(indexed) != set(expected_ids):
        raise ValueError('Incomplete or mismatched task coverage')
    return indexed


def compare_scores(parent, candidate, expected_ids):
    """Pure Gate over complete, provenance-verified per-task score projections.

    F1 is checked for a valid record, but never used in the decision.
    """
    parents = _indexed_scores(parent, expected_ids)
    candidates = _indexed_scores(candidate, expected_ids)
    p = sum(value['em'] == 1 for value in parents.values())
    q = sum(value['em'] == 1 for value in candidates.values())
    return {'decision': 'ACCEPT' if q > p else 'RETAIN',
            'parent_success': p, 'candidate_success': q, 'compared': len(expected_ids)}


def summarize_scores(records, expected_ids):
    """Report macro means only when the entire requested set is complete."""
    indexed = _indexed_scores(records, expected_ids)
    count = len(expected_ids)
    return {'sample_count': count,
            'success_count': sum(m['em'] == 1 for m in indexed.values()),
            'em': sum(indexed[t]['em'] for t in expected_ids) / count,
            'f1': sum(indexed[t]['f1'] for t in expected_ids) / count}
