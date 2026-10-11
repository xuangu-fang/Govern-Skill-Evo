"""Lossless repeated-text storage and bounded edit Memory Review repair."""
from collections import Counter
from .edit_tracking_v19 import encode,digest,parse

TEXT_INSTRUCTIONS = '''
repeated_text contains exact shared JSON values. An object {"shared_text_ref":"TEXT/n"}
stands for that complete JSON value wherever it occurs in the input. Resolve it before
interpreting the field. This is lossless storage, not evidence summarization.
'''


def compact_text(value):
    counts=Counter();values={}
    def collect(x):
        if isinstance(x,(str,dict,list)):
            key=encode(x)
            if len(key)>80:counts[key]+=1;values[key]=x
        if isinstance(x,dict):
            for v in x.values():collect(v)
        elif isinstance(x,list):
            for v in x:collect(v)
    collect(value)
    refs={key:'TEXT/'+str(i) for i,key in enumerate(sorted(k for k,n in counts.items() if n>1))}
    used=set()
    def walk(x):
        key=encode(x)
        if key in refs:
            used.add(key);return {'shared_text_ref':refs[key]}
        if isinstance(x,dict):return {k:walk(v) for k,v in x.items()}
        if isinstance(x,list):return [walk(v) for v in x]
        return x
    result=walk(value)
    return {**result,'repeated_text':{refs[k]:values[k] for k in sorted(used)}} if used else value


def build_repair(original,raw,error):
    from .contract_repair_v19 import build_repair as shared_repair
    return shared_repair(original,raw,error)
