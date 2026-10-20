"""Offline receipt and execution report; does not make or retry any calls."""
import hashlib,json
from pathlib import Path
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;P=E.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    summary=read(E/'results/summary.json');assert summary['complete']
    results={};totals={'input_tokens':0,'output_tokens':0,'total_tokens':0,'reasoning_tokens_included_in_output':0,'cached_input_tokens_included_in_input':0}
    known_subtotal=dict(totals)
    for arm,meta in summary['groups'].items():
        d=E/'runs'/arm
        req=read(d/'request.json');frozen=read(P/f'requests/{arm}_UNSENT.json')
        assert req==frozen and sha(d/'request.json')==sha(P/f'requests/{arm}_UNSENT.json')
        usage=meta.get('usage') or {};record={'run':meta,'request_hash_matches':True,'request_sha256':sha(d/'request.json')}
        if not (d/'usage.json').exists():
            (d/'usage.json').write_text(json.dumps({'usage':None,'response_model':None,'finish_reason':None,'availability':'No response received; server consumption and billing unknown.'},indent=2)+'\n')
        if meta['status']=='valid':
            result=read(d/'preconditioner.json');payload=json.loads(req['body']['messages'][1]['content']);ep=pc.compile_effective_plan(result,payload)
            assert ep==read(d/'effective_plan.json')
            if ep is not None:
                assert ep['goal']==payload['plan']['goal']
                byid={u['id']:u for u in ep['updates']};consumed={x for a in result['adjustments'] for x in a['from']}
                for a in result['adjustments']:
                    for u in a['to']:assert byid[u['id']]['text']==u['text']
                for u in payload['plan']['updates']:
                    if u['id'] not in consumed:assert byid[u['id']]['text']==u['text']
                record['lineage']={'consumed':sorted(consumed),'kept':[u['id'] for u in payload['plan']['updates'] if u['id'] not in consumed],'effective_ids':list(byid),'goal_preserved':True,'all_to_text_exact':True}
            record['deterministic_recompile']=True
        values={'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),'total_tokens':usage.get('total_tokens'),
                'reasoning_tokens_included_in_output':(usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                'cached_input_tokens_included_in_input':(usage.get('prompt_tokens_details') or {}).get('cached_tokens',usage.get('prompt_cache_hit_tokens'))}
        record['tokens']=values
        for k,v in values.items():
            if v is None:totals[k]=None
            else:
                known_subtotal[k]+=v
                if totals[k] is not None:totals[k]+=v
        results[arm]=record
    out={'groups':results,'totals':totals,'http_attempts':summary['http_attempts'],'logical_calls':summary['logical_calls_started'],'automatic_retries':0,
         'both_valid':len(results)==2 and all(r['run']['status']=='valid' for r in results.values()),
         'same_reported_model':(len({r['run'].get('response_model') for r in results.values()})==1
                                if len(results)==2 and all(r['run'].get('response_model') for r in results.values()) else None),
         'same_request_model':len({r['run']['request_model'] for r in results.values()})==1,
         'known_usage_subtotal_only':known_subtotal,'missing_usage_groups':[a for a,r in results.items() if not r['run'].get('usage')],
         'environment_calls':0,'monetary_cost':None,'money_reason':'No reliable billed currency amount provided; no price inference.'}
    (E/'results/execution_receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'totals':totals,'groups':{a:{k:r['run'].get(k) for k in ['status','decision','response_model','elapsed_seconds','finish_reason','http_attempts']} for a,r in results.items()},'both_valid':out['both_valid'],'same_reported_model':out['same_reported_model']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
