"""Use native extraction only from ordinary content; never accept overrides."""
import re
from skilladam.benchmarks.lmb.evaluation import extract_answer, parse_choice_label
from src.skill_evolution.v27.facts import require
from . import protocol as p


def score(content, choices, correct_label):
    require(isinstance(content,str), 'Content must be text')
    p.validate_choices(choices)
    by_label={c['label']:c['text'] for c in choices}
    require(correct_label in by_label,'Invalid mapped correct label')
    extracted,_=extract_answer({'response':content})
    label,answer=parse_choice_label(extracted,choices)
    tags=re.findall(r'<answer>(.*?)</answer>',content,re.I|re.S)
    markers=re.findall(r'</?answer\b[^>]*>',content,re.I)
    starts=re.findall(r'</?answer\b',content,re.I)
    compliant=len(tags)==1 and len(markers)==len(starts)==2 and tags[0].strip() in by_label
    em=int(label==correct_label)
    return {'raw_content':content,'extracted_answer':extracted,'predicted_label':label,
            'predicted_text':answer,'parse_valid':label in by_label,'format_compliant':compliant,
            'correct_label':correct_label,'correct_text':by_label[correct_label]}, {'em':em,'f1':em}


def summarize_scores(records, expected_ids):
    """Only completed, exact-coverage binary LMB scores have a formal mean."""
    require(isinstance(expected_ids, list) and expected_ids and
            len(set(expected_ids)) == len(expected_ids), 'Invalid expected task IDs')
    require(isinstance(records, list), 'Scores must be a list')
    indexed = {}
    for record in records:
        p.fields(record, ('task_id', 'metrics'), 'Score record')
        require(record['task_id'] not in indexed, 'Duplicate task score')
        indexed[record['task_id']] = p.score_view(record['metrics'])
    require(set(indexed) == set(expected_ids), 'Incomplete or mismatched task coverage')
    success = sum(m['em'] == 1 for m in indexed.values())
    return {'sample_count': len(expected_ids), 'success_count': success,
            'em': success / len(expected_ids), 'f1': success / len(expected_ids)}
