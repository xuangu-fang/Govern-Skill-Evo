"""Native SkillAdam DocVQA scoring with hard-only same-batch comparison."""
import math
from skilladam.benchmarks.docvqa.evaluation import extract_answer, anls_score, HARD_MATCH_THRESHOLD
from src.skill_evolution.v27.benchmarks.lmb.actor import parse_response
from .protocol import require, validate_answers, nonempty_text


def score(content, reference_answers):
    validate_answers(reference_answers)
    prediction = extract_answer(content)
    anls = anls_score(prediction, reference_answers)
    return ({'raw_content': content, 'extracted_answer': prediction},
            {'hard': int(anls >= HARD_MATCH_THRESHOLD), 'anls': anls})


def score_response(response, reference_answers):
    content, _ = parse_response(response)
    return score(content, reference_answers)


def validate_metrics(metrics):
    require(isinstance(metrics, dict) and set(metrics) == {'hard', 'anls'}, 'Expected hard/anls metrics')
    anls = metrics['anls']
    require(type(anls) in (int, float) and math.isfinite(anls) and 0 <= anls <= 1, 'Invalid ANLS')
    require(type(metrics['hard']) is int and metrics['hard'] == int(anls >= HARD_MATCH_THRESHOLD),
            'hard differs from the ANLS threshold')
    return metrics


def _indexed(records, expected_ids):
    require(isinstance(expected_ids, list) and expected_ids
            and len(set(expected_ids)) == len(expected_ids), 'Expected unique task IDs')
    for task_id in expected_ids:
        nonempty_text(task_id, 'Task ID')
    require(isinstance(records, list), 'Expected score records')
    indexed = {}
    for record in records:
        task_id = record['task_id']
        require(task_id not in indexed, 'Duplicate scored task')
        indexed[task_id] = validate_metrics(record['metrics'])
    require(set(indexed) == set(expected_ids), 'Incomplete or mismatched task coverage')
    return indexed


def compare_scores(parent, candidate, expected_ids):
    """Pure comparison; the adapter checks completed executions and paired tasks."""
    left, right = _indexed(parent, expected_ids), _indexed(candidate, expected_ids)
    p = sum(m['hard'] for m in left.values())
    q = sum(m['hard'] for m in right.values())
    return {'decision': 'ACCEPT' if q > p else 'RETAIN', 'parent_success': p,
            'candidate_success': q, 'compared': len(expected_ids)}


def summarize_scores(records, expected_ids):
    indexed = _indexed(records, expected_ids)
    count = len(indexed)
    successes = sum(m['hard'] for m in indexed.values())
    return {'sample_count': count, 'success_count': successes, 'hard': successes / count,
            'anls': sum(m['anls'] for m in indexed.values()) / count}
