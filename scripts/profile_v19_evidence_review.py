"""Offline per-proposal budget comparison; never calls a model or changes sources."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.evidence_review_v19 import EvidenceReviewCase,build_evidence_review_input
from src.skill_evolution.evidence_review_prompt_v19 import build_evidence_review_request
from src.skill_evolution.evolution_replay_v19 import _load,_file_digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--input-version',choices=('v19.2','v19.3'),default='v19.3')
    args=parser.parse_args();assert not args.output.exists(),'report exists'
    import tiktoken
    encoder=tiktoken.get_encoding('cl100k_base')
    count=lambda v:len(encoder.encode(encode(v)))
    rows=[];files={}
    for directory in sorted((args.source/'proposals').iterdir()):
        if not directory.is_dir():continue
        case=EvidenceReviewCase(encode(_load(directory/'case.json')))
        old=_load(directory/'input-0.json');new=build_evidence_review_input(case,input_version=args.input_version)
        from src.skill_evolution.evidence_review_v19 import EvidenceReviewInput
        before=build_evidence_review_request(EvidenceReviewInput(encode(old)),max_input_tokens=1000000)
        after=build_evidence_review_request(new,max_input_tokens=1000000)
        responses=[{'path':str(p),'finish_reason':_load(p)['finish_reason'],'usage':_load(p).get('usage')} for p in directory.glob('review-*/response.json')]
        row={'proposal_id':old['proposal_id'],'issue':case.payload['issue']['issue_statement'],
            'old_proxy_input_tokens':before['input_budget']['proxy_input_tokens'],
            'new_proxy_input_tokens':after['input_budget']['proxy_input_tokens'],
            'new_within_32000':after['input_budget']['proxy_input_tokens']<=32000,
            'canonical_field_tokens_not_additive_to_wire':{k:count(v) for k,v in old.items()},
            'old_loaded_events':len(old['events']),'new_loaded_events':len(new.payload['events']),
            'seed_events':len(case.payload['seed_refs']),'known_counterevidence':len(case.payload['known_counterevidence_refs']),
            'old_loaded_policies':len(old['policies']),'new_loaded_policies':len(new.payload['policies']),
            'responses':responses}
        from src.skill_evolution.review_packet_v19 import scoped_case
        required=(scoped_case(case).payload['seed_refs'] if new.payload.get('packet_version')in ('evidence_packet_v19.4','evidence_packet_v19.5')
                  else case.payload['seed_refs'])
        assert set(required)<=set(new.payload['events'])
        missing=set(case.payload['known_counterevidence_refs'])-set(new.payload['events'])
        assert len(missing)==new.payload.get('memory_consumption',{}).get('omitted_counterevidence_count',0)
        row['required_event_count']=len(required)
        row['all_required_events_loaded']=True
        row['all_known_counterevidence_loaded']=not new.payload.get('memory_consumption',{}).get('omitted_counterevidence_count')
        row['memory_consumption']=new.payload.get('memory_consumption',{})
        rows.append(row)
        for p in directory.rglob('*.json'):files[str(p.resolve())]=_file_digest(p)
    report={'method':'cl100k_base proxy, not gateway tokenizer; canonical field costs exclude projection effects',
        'source':str(args.source.resolve()),'input_version':args.input_version,'source_files':files,'rows':rows,'output_limit':24000,'input_limit':32000}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for row in rows:print(row['proposal_id'][6:14],row['old_proxy_input_tokens'],row['new_proxy_input_tokens'])


if __name__=='__main__':main()
