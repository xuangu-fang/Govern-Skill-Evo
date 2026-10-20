"""OFFLINE prototypes only; never imported by the frozen runner.

Reversible representation of existing evidence, not a semantic trajectory summary.
The role view intentionally reduces Editor evidence and reports that coverage change.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def size(value):
    return len(compact(value))


def sha(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


INSTRUCTIONS = '''OFFLINE INPUT-VIEW PROTOTYPE, not a production profile. Decode references
exactly; they are literal evidence, not model summaries. Integer command_set entries
index command_pool (preserve order); @concat concatenates literal parts with no inserted
spacing. @text indexes text_pool;
@object indexes object_pool. tables have ordered columns and rows; @missing means an
absent key, not an unknown observation. Order, step numbers and Parent/Candidate
identities are unchanged. event_source_rule restores current sources alias:0 and
alias:step for every recorded run step. Full original archives remain authoritative.
A reference is not an extra independent observation. Do not infer absence or failure
from evidence excluded by the stated coverage. Model usability is not yet validated.'''


def lossless_pack(view):
    data = deepcopy(view)
    # Never silently interpret a coincidentally identical field as our reserved syntax.
    reserved = {'@text', '@object', '@missing', '@table', '@concat'}
    assert all(not (isinstance(x, dict) and reserved & set(x)) for x in walk(data))
    event_rule = False
    if 'runs' in data and 'sources' in data:
        expected = {f'{alias}:{step}': {'kind': 'event', 'run': alias, 'step': step}
                    for alias, run in data['runs'].items()
                    for step in [0] + [e['step'] for e in run['steps']]}
        actual = {k: v for k, v in data['sources'].items() if v.get('kind') == 'event'}
        if expected == actual:
            data['sources'] = {k: v for k, v in data['sources'].items() if k not in expected}
            event_rule = True
    # Identical command atoms shared across otherwise different ordered menus.
    menus = data.get('command_sets', {})
    command_counts = Counter(command for menu in menus.values() for command in menu)
    command_pool = [s for s, count in command_counts.items() if count > 1 and len(s)>8]
    command_ids = {s:i for i,s in enumerate(command_pool)}
    for key,menu in menus.items():
        menus[key] = [command_ids[s] if s in command_ids else s for s in menu]
    # Exact sentence/newline fragments expose common literal observations without
    # summarizing or dropping unique details. No arbitrary character-offset decoder.
    obs_keys = {'observation', 'initial_observation', 'observation_before'}
    def fragments(text):
        return re.split(r'(?<=\n)|(?<=[.!?])(?=\s)', text)
    counts = Counter(part for row in walk(data) if isinstance(row,dict)
                     for key,value in row.items() if key in obs_keys and isinstance(value,str)
                     for part in fragments(value) if len(part)>=48)
    def fragment_pack(x):
        if isinstance(x,list):return [fragment_pack(v) for v in x]
        if not isinstance(x,dict):return x
        result={k:fragment_pack(v) for k,v in x.items()}
        for key in obs_keys & set(result):
            value=result[key]
            if isinstance(value,str):
                parts=fragments(value)
                if len(parts)>1 and any(counts[part]>1 and len(part)>=48 for part in parts):
                    result[key]={'@concat':parts}
        return result
    data=fragment_pack(data)
    strings = Counter(x for x in walk(data) if isinstance(x, str) and len(x) >= 24)
    text_pool = [text for text, count in strings.items() if count > 1 and (len(compact(text))-15)*(count-1)>20]
    text_ids = {s: i for i, s in enumerate(text_pool)}
    def text_pack(x):
        if isinstance(x, str) and x in text_ids: return {'@text': text_ids[x]}
        if isinstance(x, list): return [text_pack(v) for v in x]
        if isinstance(x, dict): return {k: text_pack(v) for k, v in x.items()}
        return x
    data = text_pack(data)
    # Only step row keys are factored; every value and row is retained.
    def tables(x):
        if isinstance(x, list): return [tables(v) for v in x]
        if not isinstance(x, dict): return x
        result = {k: tables(v) for k, v in x.items()}
        steps = result.get('steps')
        if isinstance(steps, list) and steps and all(isinstance(e, dict) for e in steps):
            columns = list(dict.fromkeys(k for row in steps for k in row))
            table = {'@table': columns, 'rows': [[row.get(k, {'@missing': True}) for k in columns] for row in steps]}
            if size(table) < size(steps): result['steps'] = table
        return result
    data = tables(data)
    objects = Counter(compact(x) for x in walk(data) if isinstance(x, (dict, list)) and size(x) >= 180)
    object_pool, ids = [], {}
    def pool(x):
        if isinstance(x, (dict, list)):
            key = compact(x)
            if objects[key] > 1 and len(key) >= 180:
                if key not in ids:
                    ids[key] = len(object_pool); object_pool.append(x)
                return {'@object': ids[key]}
        if isinstance(x, list): return [pool(v) for v in x]
        if isinstance(x, dict): return {k: pool(v) for k, v in x.items()}
        return x
    data = pool(data)
    return {'view': 'offline.lossless_evidence.v1', 'event_source_rule': event_rule,
            'command_pool': command_pool, 'text_pool': text_pool, 'object_pool': object_pool, 'evidence': data}


def lossless_unpack(packed):
    def expand(x):
        if isinstance(x, dict) and set(x) == {'@object'}: return expand(packed['object_pool'][x['@object']])
        if isinstance(x, dict) and set(x) == {'@text'}: return packed['text_pool'][x['@text']]
        if isinstance(x, dict) and set(x) == {'@concat'}: return ''.join(expand(v) for v in x['@concat'])
        if isinstance(x, dict) and set(x) == {'@table', 'rows'}:
            return [{key: expand(value) for key, value in zip(x['@table'], row)
                     if value != {'@missing': True}} for row in x['rows']]
        if isinstance(x, dict): return {k: expand(v) for k, v in x.items()}
        if isinstance(x, list): return [expand(v) for v in x]
        return x
    data = expand(packed['evidence'])
    for key,menu in data.get('command_sets',{}).items():
        data['command_sets'][key]=[packed['command_pool'][v] if isinstance(v,int) else v for v in menu]
    if packed['event_source_rule']:
        data['sources'].update({f'{alias}:{step}': {'kind': 'event', 'run': alias, 'step': step}
                               for alias, run in data['runs'].items()
                               for step in [0]+[e['step'] for e in run['steps']]})
    return data


def editor_role_view(view):
    """Use declared requirement/watch links only, never guess natural-language relevance.

    Effective Plan stays complete. This is *not* globally information-lossless.
    All referenced Effect bases remain; unrelated histories/traces are not displayed.
    """
    data = deepcopy(view)
    refs = {ref for row in data['plan']['requirements'] for ref in row['basis']}
    selected = {}
    for alias, run in data.get('runs', {}).items():
        hits = {int(ref.split(':')[1]) for ref in refs if ref.startswith(alias+':') and ref.split(':')[1].isdigit()}
        if not hits: continue
        original = run['steps']; keep = {step for hit in hits for step in (hit-1, hit, hit+1)}
        row = deepcopy(run); row['steps'] = [e for e in original if e['step'] in keep]
        row['coverage'] = {'shown_steps': [e['step'] for e in row['steps']], 'original_step_count': len(original),
                           'not_shown_does_not_mean_absent': True}
        selected[alias] = row
    data['runs'] = selected
    data['sources'] = {k: v for k, v in data.get('sources', {}).items()
                       if v.get('kind') != 'event' or (v['run'] in selected and
                           (v['step'] == 0 or v['step'] in selected[v['run']]['coverage']['shown_steps']))}
    commands = {r['initial_commands'] for r in selected.values()}
    commands.update(e['commands'] for r in selected.values() for e in r['steps'])
    data['command_sets'] = {k: v for k, v in data.get('command_sets', {}).items() if k in commands}
    data['memory'] = [e for e in data.get('memory', []) if e['id'] in refs]
    contexts = {b['actual_update_ref'] for e in data['memory'] for b in e['basis']}
    sources = {ref for e in data['memory'] for b in e['basis'] for ref in b['sources']}
    data['historical_updates'] = {k: v for k, v in data.get('historical_updates', {}).items() if k in contexts}
    data['historical_sources'] = {k: v for k, v in data.get('historical_sources', {}).items() if k in sources}
    data['coverage'] = {'role': 'Editor implementation of the complete effective Plan',
                        'selection': 'explicit requirement basis events plus adjacent steps; explicit Effect bases',
                        'omissions': 'unreferenced current steps and historical evidence; not proof of absence',
                        'permission': 'No independent strategy change; unresolved evidence may use existing issue/watch exits',
                        'source_view_sha256': sha(view)}
    assert data['plan'] == view['plan'] and data['parent'] == view['parent']
    return data


def history_cards(view):
    """Exploratory bounded-by-active-knowledge view. No fake retrieval or fact claims.

    All claims/limits are verbatim, but raw historical basis is no longer displayed.
    This deliberately *fails* full history-evidence coverage and cannot yet be adopted
    for response-driven Fusion/learning without a justified evidence expansion rule.
    """
    data = deepcopy(view)
    data['memory'] = [{k: deepcopy(e[k]) for k in ('id','claim','limits','supersedes','attribution','claim_context_id','limit_contexts') if k in e}
                      | {'archived_basis_count': len(e['basis']), 'basis_archive_digest': sha(e['basis'])}
                      for e in view.get('memory', [])]
    for key in ('historical_sources','historical_updates','historical_contexts'): data.pop(key, None)
    data['history_coverage'] = {'claims_and_limits': 'complete active fallible interpretations',
                              'raw_basis': 'archived only, NOT available to this model call',
                              'warning': 'Not sufficient alone to independently compare historical response evidence',
                              'source_view_sha256': sha(view)}
    return data
