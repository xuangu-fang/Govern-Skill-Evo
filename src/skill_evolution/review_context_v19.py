"""Lossless directories and explicit local context selection, never evidence truncation."""
from .memory_store_v19 import require


def pack_directory(directory):
    tables={}
    for ref,metadata in directory.items():
        prefix,_,suffix=ref.rpartition('/')
        columns=tuple(sorted(metadata));key=(prefix+'/',columns)
        tables.setdefault(key,[]).append([suffix,*[metadata[k] for k in columns]])
    packed=[]
    for (prefix,columns),rows in tables.items():
        common={i for i in range(len(columns)) if len(rows)>1 and all(row[i+1]==rows[0][i+1] for row in rows)}
        packed.append({'prefix':prefix,'columns':[k for i,k in enumerate(columns) if i not in common],
            'constants':{k:rows[0][i+1] for i,k in enumerate(columns) if i in common},
            'rows':[[row[0],*[v for i,v in enumerate(row[1:]) if i not in common]] for row in rows]})
    return {'encoding':'prefix_columns_v19.1','tables':packed}


def unpack_directory(directory):
    if directory.get('encoding')!='prefix_columns_v19.1':return directory
    result={}
    for table in directory['tables']:
        for row in table['rows']:
            ref=table['prefix']+row[0]
            require(ref not in result and len(row)==len(table['columns'])+1,'invalid directory row')
            result[ref]={**table['constants'],**dict(zip(table['columns'],row[1:]))}
    return result


def paired_events(events,selected):
    """Direct seeds plus identifiable call/results; no unrelated +/-1 neighbors."""
    chosen={e['evidence_ref'] for e in events if e['evidence_ref'] in selected}
    for i,e in enumerate(events):
        if e['evidence_ref'] not in selected:continue
        kind=e['event_type'];name=e.get('tool_name')
        if not name or kind not in ('tool_call','tool_result'):continue
        direction=1 if kind=='tool_call' else -1
        for j in range(i+direction,len(events) if direction==1 else -1,direction):
            other=events[j]
            if other.get('tool_name')!=name:continue
            if other['event_type']==kind:break
            if other['event_type'] in ('tool_call','tool_result'):
                chosen.add(other['evidence_ref']);break
    return chosen


def compact_projection(payload):
    """Lossless reference notation. Only exact structured reference strings change."""
    from collections import Counter
    from .evidence_projection_v19 import project
    wire=project(payload);counts=Counter()
    roots=('CURRENT/','HISTORICAL/','POLICY/','TOOL/','CF/','ISSUE/','HR/','HO/','HISTORY/')
    if payload.get('packet_version')in ('evidence_packet_v19.4','evidence_packet_v19.5'):
        roots+=('PAIR/',)
    def visit(v):
        if isinstance(v,str) and v.startswith(roots):
            prefix,_,_=v.rpartition('/')
            if len(prefix)>40:counts[prefix+'/']+=1
        elif isinstance(v,list):
            for x in v:visit(x)
        elif isinstance(v,dict):
            for k,x in v.items():visit(k);visit(x)
    visit(wire)
    prefixes={f'@REF{i}/':p for i,p in enumerate(sorted(p for p,n in counts.items() if n>1))}
    reverse={p:k for k,p in prefixes.items()}
    def walk(v):
        if isinstance(v,str):
            prefix,_,suffix=v.rpartition('/')
            return reverse[prefix+'/']+suffix if prefix+'/' in reverse else v
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {walk(k):walk(x) for k,x in v.items()}
        return v
    return {**walk(wire),'reference_prefixes':prefixes}


def expand_reference(ref,prefixes):
    for key,prefix in prefixes.items():
        if ref.startswith(key):return prefix+ref[len(key):]
    return ref
