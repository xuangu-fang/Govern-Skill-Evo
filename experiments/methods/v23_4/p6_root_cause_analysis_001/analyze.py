"""Deterministic read-only audit of frozen P6. Writes only this new analysis folder.

No model calls, archive commits, production mutations or output repairs. Never
emit model reasoning or malformed Actor action prose; retain only its metadata.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
from experiments.methods.v23_4.archive_io import archive_glob, resolve

BASE = HERE.parent
P4 = BASE / 'multi_knowledge_p4_001'
P6 = BASE / 'multi_knowledge_p6_001'
OLD = BASE / 'replay_prompt_candidate_001'


def read(path):
    return json.loads(resolve(path).read_text())


def sha(path):
    return hashlib.sha256(resolve(path).read_bytes()).hexdigest()


def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def safe_action(action):
    return action if len(action) < 200 and '\n' not in action else '[malformed long action omitted]'


def step(view, ref):
    runid, num = ref.rsplit(':', 1)
    n = int(num)
    if '/' not in runid:
        run = next(r for r in view['runs'] if r['ref'] == runid)
        item = deepcopy(run['steps'][n-1])
        menus = view['command_sets']
        visible = True
    else:
        src = view['memory']['sources'][runid]
        run = src['run']
        item = deepcopy(run['trace'][n-1])
        detail = next((s for s in src['detailed_steps'] if s['step'] == ref), None)
        visible = detail is not None
        if detail: item.update(deepcopy(detail))
        menus = view['memory']['command_pool']
    item['action'] = safe_action(item['action'])
    result = {'task': run['task'], 'ref': ref, 'state_and_menu_visible': visible,
              'item': item, 'outcome': run['outcome']}
    if visible:
        result['before_menu'] = menus.get(item['before']['commands_ref'])
        result['after_menu'] = menus.get(item['after']['commands_ref'])
    return result


def main():
    protected = read(P6 / 'protected_before.json')
    for folder in (P6, P4, OLD, ROOT / 'src', ROOT / 'docs/methods/v23_4'):
        protected.update({str(p.relative_to(ROOT)): sha(p) for p in archive_glob(folder, '*', recursive=True)
                          if p.is_file() and '__pycache__' not in str(p)})
    assert all(sha(ROOT / path) == digest for path, digest in protected.items())
    save('READ_ONLY_BEFORE.json', protected)
    frozen = read(P6 / 'config/freeze.json')
    assert all(sha(ROOT / p) == d for p, d in frozen['sha256'].items())
    result = {'cases': {}, 'format_failures': [], 'source_files': {}}
    for label in ('R05', 'R06'):
        runroot = P6 / f'runs/{label}_replay'
        selected = read(runroot / 'selected.json')['attempt']
        messages = read(runroot / f'attempt_{selected:03}/http/request.json')['body']['messages']
        assert messages == read(P4 / f'cases/{label}/messages.json') == read(runroot / 'messages.json')
        view = json.loads(messages[1]['content'])
        assert view == read(P4 / f'cases/{label}/model_input.json')
        bundle = read(P4 / f'cases/{label}/replay_bundle.json')
        editor = Path(bundle['editor_directory'])
        assert (editor / 'actual.diff').read_text() == view['diff']
        assert (editor / 'candidate.md').read_text() == bundle['candidate']
        oldview = read(OLD / f'config/{label}/model_input.json')
        normalized = deepcopy(oldview)
        for entry in normalized['memory']['entries']:
            entry['knowledge'] = [{'text': entry['knowledge'], 'evidence': entry.pop('evidence')}]
        assert normalized == view
        assert {r['ref']: {k:v for k,v in r.items() if k != 'executed_steps'} for r in view['runs']} == {
            r['ref']: r for r in bundle['payload']['runs']}
        proposal = read(runroot / f'attempt_{selected:03}/parsed.json')
        historical_round = 'R04' if label == 'R05' else 'R05'
        formal = ROOT / f'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/{historical_round}/memory'
        index = read(formal / 'active.json')
        archived_entries = {e['id']: e for cid in index['commits']
                            for e in read(formal / 'archive' / f'{cid}.json')['entries']}
        original_entries = []
        for mid in index['active_ids']:
            e = archived_entries[mid]
            original_entries.append({'id': mid, 'knowledge': [{'text': e['knowledge'], 'evidence': e['evidence']}]})
        assert original_entries == view['memory']['entries']
        source_runs = [s for k,s in view['memory']['sources'].items() if not k.endswith('/diff')]
        chars = lambda o: len(json.dumps(o, ensure_ascii=False, separators=(',', ':')))
        stats = {'input_tokens': read(runroot / f'attempt_{selected:03}/response.json')['usage']['prompt_tokens'],
            'system_chars': len(messages[0]['content']), 'user_chars': len(messages[1]['content']),
            'current_pairs': len(view['pairs']), 'current_runs': len(view['runs']),
            'current_steps': sum(len(r['steps']) for r in view['runs']),
            'historical_runs': len(source_runs), 'historical_pairs': len(view['memory']['pairs']),
            'historical_unpaired_runs': view['memory']['unpaired_runs'],
            'historical_steps': sum(len(s['run']['trace']) for s in source_runs),
            'historical_detailed_steps': sum(len(s['detailed_steps']) for s in source_runs),
            'historical_contexts': [k for k in view['memory']['sources'] if k.endswith('/diff')],
            'memory_chars': chars(view['memory']), 'memory_share_of_user_chars': chars(view['memory'])/len(messages[1]['content']),
            'current_menu_chars': chars(view['command_sets']),
            'history_menu_chars': chars(view['memory']['command_pool'])}
        current = {r['ref']:r for r in view['runs']}
        refs = (['Q7:25','P8:8','P8:15','Q8:39','Q8:40','P6:3','Q6:3','P10:9','Q10:6',
                 'S1_R04/Q6:25'] if label == 'R05' else
                ['P2:13','Q2:5','P2:15','Q2:7','S1_R04/P2:4','S1_R04/P2:11',
                 'S1_R04/P2:13','S1_R04/Q2:50','S1_R05/Q7:2','S1_R05/Q7:50'])
        details = {ref:step(view,ref) for ref in refs}
        drawer8 = []
        for r in view['runs']:
            drawer8.extend({'ref':s['step'],'task':r['task'],'feedback':s['feedback']} for s in r['steps'] if s['action']=='go to drawer 8')
        for key,s in view['memory']['sources'].items():
            if key.endswith('/diff'): continue
            drawer8.extend({'ref':t['step'],'task':s['run']['task'],'feedback':t['feedback']} for t in s['run']['trace'] if t['action']=='go to drawer 8')
        response_checks = []
        for attempt in archive_glob(runroot, 'attempt_*'):
            req = read(attempt / 'http/request.json')
            assert req['body']['messages'] == messages
            expected = {k:v for k,v in frozen['call_config'].items() if k not in ('endpoint','timeout_seconds')}
            expected['messages'] = messages
            assert req['body'] == expected
            response = read(attempt / 'response.json')
            raw = json.loads(resolve(attempt / 'http/http_response.txt').read_text())
            assert raw['choices'][0]['message']['content'] == response['content']
            content = response['content']
            meta = {'attempt':attempt.name, 'status':read(attempt/'attempt.json')['status'],
                    'finish_reason':response['finish_reason'],'model':response['response_model'],
                    'content_chars':len(content),'usage':response['usage'],'raw_content_unchanged_by_adapter':True}
            if meta['status']=='valid': assert json.loads(content)==read(attempt/'parsed.json')
            else:
                positions = [m.start() for m in re.finditer(r'\{\s*"entries"\s*:',content)]
                meta['json_object_offsets'] = positions
                if len(positions)==1:
                    obj, end = json.JSONDecoder().raw_decode(content[positions[0]:])
                    meta.update(non_json_prefix_chars=positions[0], suffix_chars=len(content)-positions[0]-end,
                                trailing_object_parseable=True)
                    # Inspect shape only. Do not save, repair, or adopt this embedded proposal.
                result['format_failures'].append({'case':label,**meta})
            response_checks.append(meta)
        coverage = []
        for ei,entry in enumerate(proposal['entries'],1):
            for ki,k in enumerate(entry['knowledge'],1):
                coverage.append({'entry_position':ei,'knowledge_position':ki,'revises':entry['revises'],
                    'text':k['text'],'evidence':k['evidence'],
                    'current_runs_referenced':sorted({r.split(':')[0] for r in k['evidence'] if r!='diff' and '/' not in r}),
                    'historical_numeric_state_visibility':{r:step(view,r)['state_and_menu_visible']
                        for r in k['evidence'] if '/' in r and r.rsplit(':',1)[-1].isdigit() and int(r.rsplit(':',1)[-1])>0}})
        case = {'actual_request_matches_p4':True,'actual_facts_equal_old_candidate_except_entry_wrapping':True,
                'actual_current_runs_complete':True, 'actual_editor_diff_matches':True,
                'formal_active_entries_normalization_exact':True,
                'stats':stats,'details':details,'drawer8_matches':drawer8,'response_checks':response_checks,
                'knowledge':coverage,'old_entries':view['memory']['entries'],
                'plan':view['plan'],'actual_diff':view['diff'], 'pairs':view['pairs']}
        preview = read(P6 / f'cases/{label}/results/memory_view.json')
        prefix = f'v23_4_{label}_multi_knowledge_p6_001/'
        case['next_view_selection'] = {
            'historical_sources_removed':sorted(set(view['memory']['sources'])-set(preview['sources'])),
            'current_runs_not_retained':[r for r in current if prefix+r not in preview['sources']],
            'current_detail_windows':{k:src['windows'] for k,src in preview['sources'].items()
                if k.startswith(prefix) and not k.endswith('/diff')},
            'historical_heat_plate_parent_windows_before':view['memory']['sources']['S1_R04/P2']['windows'],
            'historical_heat_plate_parent_windows_after':preview['sources']['S1_R04/P2']['windows']}
        if label=='R05':
            assert all(s['feedback']['action_in_admissible_commands'] is True for s in current['Q7']['steps'])
            assert details['Q7:25']['item']['action']=='go to drawer 2'
            hist = details['S1_R04/Q6:25']
            assert hist['item']['action']=='go to drawer 8' and hist['item']['feedback']['action_in_admissible_commands'] is False
            p = details['P8:8']; assert 'go to cabinet 3' not in p['before_menu'] and 'open cabinet 3' in p['before_menu']
            assert [s['action'] for s in current['P10']['steps'][9:]]==[s['action'] for s in current['Q10']['steps'][6:]]
            case['apple_actions'] = {r:[safe_action(s['action']) for s in current[r]['steps']] for r in ('P10','Q10')}
            case['butterknife_success'] = {r:{'task':current[r]['task'],'outcome':current[r]['outcome'],
                'actions':[safe_action(s['action']) for s in current[r]['steps']]} for r in ('P6','Q6')}
            case['soapbar_unvisited_shelf'] = {}
            assert any(s['action']=='go to sinkbasin 1' for s in current['P8']['steps'])
            case['sinkbasin_is_not_a_new_family']={'parent_visited':'sinkbasin 1','candidate_new_instance':'sinkbasin 2'}
            for r in ('P8','Q8'):
                assert 'go to shelf 1' in view['command_sets'][current[r]['initial']['commands_ref']]
                assert not any(s['action']=='go to shelf 1' for s in current[r]['steps'])
                case['soapbar_unvisited_shelf'][r] = {'available_initially':True,'never_visited':True}
        else:
            assert [s['action'] for s in current['P2']['steps'][13:]]==[s['action'] for s in current['Q2']['steps'][5:]]
            case['cool_tomato_actions'] = {r:[safe_action(s['action']) for s in current[r]['steps']] for r in ('P2','Q2')}
            case['heat_plate'] = {}
            for r in ('S1_R04/P2','S1_R04/Q2'):
                src=view['memory']['sources'][r]
                case['heat_plate'][r]={'steps':len(src['run']['trace']),'outcome':src['run']['outcome'],
                    'windows':src['windows'],'actions':[safe_action(s['action']) for s in src['run']['trace']]}
            src=view['memory']['sources']['S1_R05/Q7']
            assert 'go to cabinet 18' in view['memory']['command_pool'][src['run']['initial']['commands_ref']]
            assert not any(s['action']=='go to cabinet 18' for s in src['run']['trace'])
            case['historical_butterknife_unvisited_cabinet18']={'available_initially':True,'never_visited':True,
                'windows':src['windows'],'absence_text_already_in_M10':'no exact butterknife was present' in next(e for e in view['memory']['entries'] if e['id']=='M10')['knowledge'][0]['text']}
        result['cases'][label]=case
        for p in [runroot/f'attempt_{selected:03}/http/request.json',runroot/f'attempt_{selected:03}/parsed.json',
                  P4/f'cases/{label}/model_input.json',P4/f'cases/{label}/replay_bundle.json',editor/'actual.diff']:
            result['source_files'][str(p.relative_to(ROOT))]=sha(p)
    save('EVIDENCE.json',result)
    assert all(sha(ROOT / p)==d for p,d in protected.items())
    save('VERIFICATION.json',{'protected_files_unchanged':len(protected),'p6_frozen_files_checked':len(frozen['sha256']),
        'actual_requests_verified':3,'model_calls':0,'production_writes':0,'memory_commits':0,
        'script_sha256':sha(Path(__file__))})
    print(json.dumps({'cases':{k:v['stats'] for k,v in result['cases'].items()},
                      'verification':read(HERE/'VERIFICATION.json')},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
