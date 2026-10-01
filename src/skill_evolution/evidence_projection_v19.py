"""Lossless wire interning. Canonical persisted evidence is never shortened."""
from .edit_tracking_v19 import encode, digest
from .memory_store_v19 import require

INSTRUCTIONS = '''
LOSSLESS INPUT REFERENCES
representation_version identifies a lossless wire projection. Original event refs
remain citation IDs. An event_body_ref resolves in event_bodies; combine that body
with its evidence_ref. A text_body_ref resolves to the exact string in text_bodies.
These are storage references, not summaries, and may occur in any input field or
event body. Read resolved values. Never cite body IDs as observation evidence.
'''


def project(payload):
    events, texts = {}, {}
    def walk(value):
        if isinstance(value, str) and len(value)>512:
            key='TEXT/'+digest(value);texts[key]=value
            return {'text_body_ref':key}
        if isinstance(value,list): return [walk(v) for v in value]
        if isinstance(value,dict):
            if 'event_type' in value and 'evidence_ref' in value:
                body={k:v for k,v in value.items() if k!='evidence_ref'}
                key='BODY/'+digest(encode(body));events[key]=walk(body)
                return {'evidence_ref':value['evidence_ref'],'event_body_ref':key}
            return {k:walk(v) for k,v in value.items()}
        return value
    result=walk(payload)
    require(not set(result)&{'representation_version','event_bodies','text_bodies','canonical_payload_sha256'},
            'projection metadata collision')
    result.update(representation_version='evidence_projection_v19.1',event_bodies=events,text_bodies=texts,
                  canonical_payload_sha256=digest(encode(payload)))
    require(expand(result)==payload,'lossless projection mismatch')
    return result


def expand(payload):
    if 'reference_prefixes' in payload:
        from .review_context_v19 import expand_reference
        prefixes=payload['reference_prefixes']
        def refs(value):
            if isinstance(value,str):return expand_reference(value,prefixes)
            if isinstance(value,list):return [refs(v) for v in value]
            if isinstance(value,dict):return {refs(k):refs(v) for k,v in value.items()}
            return value
        payload=refs({k:v for k,v in payload.items() if k!='reference_prefixes'})
    def walk(value):
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,dict):
            if set(value)=={'text_body_ref'}:return payload['text_bodies'][value['text_body_ref']]
            if set(value)=={'event_body_ref','evidence_ref'}:
                return {**walk(payload['event_bodies'][value['event_body_ref']]),'evidence_ref':value['evidence_ref']}
            return {k:walk(v) for k,v in value.items()}
        return value
    result=walk({k:v for k,v in payload.items() if k not in
                 ('representation_version','event_bodies','text_bodies','canonical_payload_sha256')})
    require(digest(encode(result))==payload['canonical_payload_sha256'],'projection content changed')
    return result
