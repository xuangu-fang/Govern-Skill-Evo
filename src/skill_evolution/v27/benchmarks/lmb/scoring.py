"""Use native extraction only from ordinary content; never accept overrides."""
import re
from skilladam.benchmarks.lmb.evaluation import extract_answer, parse_choice_label
from ...facts import require
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
