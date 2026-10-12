"""Offline tokenizer-proxy accounting for the exact saved model request."""
from collections import Counter, defaultdict
from .edit_tracking_v19 import encode, parse, digest
from .evidence_projection_v19 import expand


def profile_request(request):
    import tiktoken
    tokenizer=tiktoken.get_encoding('cl100k_base')
    count=lambda text:len(tokenizer.encode(text,disallowed_special=()))
    wire=parse(request['user_prompt'])
    canonical=expand(wire) if 'representation_version' in wire else wire
    sections={}
    for key,value in wire.items():
        if key in ('event_bodies','text_bodies'):continue
        if key=='review_input':
            sections.update({f'review_input.{k}':v for k,v in value.items()})
        else:sections[key]=value
    owners=defaultdict(set)
    def references(value,owner):
        if isinstance(value,list):
            for child in value:references(child,owner)
        elif isinstance(value,dict):
            for field,table in (('event_body_ref','event_bodies'),('text_body_ref','text_bodies')):
                if field in value:
                    key=(table,value[field])
                    if owner not in owners[key]:
                        owners[key].add(owner);references(wire[table][value[field]],owner)
                    return
            for child in value.values():references(child,owner)
    for owner,value in sections.items():references(value,owner)
    rows={key:{'inline_tokens':count(encode(value)),'body_tokens':0,'body_count':0}
          for key,value in sections.items()}
    for table in ('event_bodies','text_bodies'):
        for key,value in wire.get(table,{}).items():
            links=owners[(table,key)]
            owner=next(iter(links)) if len(links)==1 else 'shared_bodies' if links else 'unreferenced_bodies'
            row=rows.setdefault(owner,{'inline_tokens':0,'body_tokens':0,'body_count':0})
            row['body_tokens']+=count(encode({key:value}));row['body_count']+=1
    for row in rows.values():row['section_proxy_tokens']=row['inline_tokens']+row['body_tokens']
    envelope=encode({'messages':[{'role':'system','content':request['system_prompt']},
                                {'role':'user','content':request['user_prompt']}],
                     'response_format':request['response_format']})
    # Section counts use individual JSON fragments; boundaries/key framing differ
    # from the exact user string. Report the signed residual, not false precision.
    user_tokens=count(request['user_prompt'])
    result={'method':'cl100k_base_PROXY_NOT_GATEWAY_TOKENIZER',
        'request_sha256':digest(encode(request)),'prompt_version':request['prompt_version'],
        'proxy_input_tokens':count(envelope),'user_prompt_tokens':user_tokens,
        'system_prompt_tokens':count(request['system_prompt']),
        'response_format_tokens':count(encode(request['response_format'])),
        'user_characters':len(request['user_prompt']),'user_utf8_bytes':len(request['user_prompt'].encode()),
        'sections':dict(sorted(rows.items(),key=lambda item:-item[1]['section_proxy_tokens'])),
        'section_serialization_residual':user_tokens-sum(r['section_proxy_tokens'] for r in rows.values()),
        'accounting_note':'Sections count physical inline values plus uniquely owned interned bodies. Shared bodies counted once. Signed residual accounts for fragment boundaries and JSON framing. Envelope proxy includes escaped content; none of these are gateway token counts.',
        'stored_input_budget':request.get('input_budget'),
    }
    review=canonical.get('review_input',{})
    findings=review.get('current_findings',[])
    result['counts']={'current_findings':len(findings),
        'finding_event_refs':len({r for f in findings for r in f['evidence_refs']}),
        'historical_reviews':len(canonical.get('historical_reviews',{}).get('reviews',[])),
        'historical_objects':len(review.get('historical_objects',[])),
        'memory_rounds':len(review.get('memory_context',{}).get('rounds',[])),
        'loaded_events':len(canonical.get('events',review.get('current_evidence',{})))}
    identities=Counter(encode({k:v for k,v in event.items() if k!='event'})
                       for event in review.get('current_evidence',{}).values())
    result['duplicate_representation']={
        'per_event_identity_occurrences':sum(identities.values()),
        'distinct_trajectory_identities':len(identities),
        'redundant_identity_occurrences':sum(n-1 for n in identities.values()),
        'historical_raw_response_repeated':bool(canonical.get('historical_reviews',{}).get('raw_response'))}
    return result
