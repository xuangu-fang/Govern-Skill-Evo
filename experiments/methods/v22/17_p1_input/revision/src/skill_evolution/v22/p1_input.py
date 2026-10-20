"""Versioned, lossless model-consumption encoding; no evidence selection.

Output validators and state transitions continue to consume the original payload.
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


PROFILE = "v22.unified_dsc.v4"
VIEW_SCHEMA = "v22.p1_shared_input.v1"
INSTRUCTIONS = """P1 LOSSLESS INPUT REPRESENTATION (v22.p1_shared_input.v1):
The user JSON contains evidence plus shared pools. All rules above apply to the
fully decoded evidence; no steps or active historical evidence were selected away.
If literal is true, evidence is original JSON: do not interpret any @ markers.
All pool indices are zero-based. In command_sets only, integer entries index
command_pool; literal strings remain literal commands. Preserve each menu's order
and duplicates. A step's commands ID selects its complete pre-action menu.
Objects {"@text":i} and {"@object":i} refer to text_pool[i] and object_pool[i].
Resolve nested references. {"@concat":[...]} concatenates the decoded literal parts
in order with no inserted spaces or newlines. A steps object with @table columns
and rows restores each row by column position; {"@missing":true} is an absent key,
not null. Rows and step numbers keep their original order and execution identity.
If event_source_rule is true, sources additionally contains alias:0 and alias:step
for every step in runs[alias]: each means {kind:event,run:alias,step:that_number}.
Other sources stay explicit. P/C aliases retain their separate run/task/Skill IDs;
historical namespaces retain their original meaning. Shared text is not a shared
execution or extra trial. Observations and menu semantics are unchanged.
Output ORIGINAL event, requirement, Watch, group and Effect IDs under the unchanged
output schema, never pool indices. Do not output a decoded copy of the input.
"""



def encode(view):
    data = deepcopy(view)
    # Never silently interpret a coincidentally identical field as our reserved syntax.
    reserved = {'@text', '@object', '@missing', '@table', '@concat'}
    if any(isinstance(x, dict) and reserved & set(x) for x in walk(data)):
        return {'view': VIEW_SCHEMA, 'literal': True, 'evidence': data}
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
    return {'view': VIEW_SCHEMA, 'event_source_rule': event_rule,
            'command_pool': command_pool, 'text_pool': text_pool, 'object_pool': object_pool, 'evidence': data}


def decode(packed):
    if packed.get('view') != VIEW_SCHEMA:
        raise ValueError('Unknown P1 input encoding')
    if packed.get('literal') is True:
        return deepcopy(packed['evidence'])
    def expand(x):
        if isinstance(x, dict) and set(x) == {'@object'}: return expand(packed['object_pool'][x['@object']])
        if isinstance(x, dict) and set(x) == {'@text'}: return packed['text_pool'][x['@text']]
        if isinstance(x, dict) and set(x) == {'@concat'}: return ''.join(expand(v) for v in x['@concat'])
        if isinstance(x, dict) and set(x) == {'@table', 'rows'}:
            if any(len(row) != len(x['@table']) for row in x['rows']):
                raise ValueError('P1 table row/column mismatch')
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



def encode_messages(messages):
    """Encode only model consumption; keep raw facts for compilation/validation."""
    if len(messages) != 2 or [m['role'] for m in messages] != ['system', 'user']:
        raise ValueError('P1 expects the existing system/user message pair')
    view = json.loads(messages[1]['content'])
    packed = encode(view)
    if decode(packed) != view:
        raise ValueError('P1 roundtrip changed model-visible evidence')
    return [{'role': 'system', 'content': messages[0]['content'] + '\n' + INSTRUCTIONS},
            {'role': 'user', 'content': compact(packed)}]
