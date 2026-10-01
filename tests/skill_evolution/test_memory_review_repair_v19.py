from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.skill_evolution.memory_review_repair_v19 import compact_text,build_repair
from src.skill_evolution.edit_memory_review_v19 import build_packet_request,validate_packet,MAX_INPUT_TOKENS,packet_wire
from src.skill_evolution.review_contract_v19 import MemoryReviewInput


def test_compaction_lossless():
    data={'a':[{'body':'long text '*100,'source':'original'}]*5,'b':'unicode 中文'*100}
    wire=compact_text(data);table=wire.pop('repeated_text')
    def expand(v):
        if isinstance(v,dict) and set(v)=={'shared_text_ref'}:return table[v['shared_text_ref']]
        if isinstance(v,dict):return {k:expand(x) for k,x in v.items()}
        if isinstance(v,list):return [expand(x) for x in v]
        return v
    assert expand(wire)==data


def test_real_rejected_response_repair_fits():
    import gzip
    fixture=json.loads(gzip.decompress((Path(__file__).parent/'fixtures/memory_review_shared_evidence_rejection.json.gz').read_bytes()))
    packet=MemoryReviewInput(json.dumps(fixture['packet']))
    raw=fixture['raw']
    with pytest.raises(ValueError,match='unlinked_findings') as error:validate_packet(raw,packet)
    request=build_packet_request(packet)
    repair=build_repair(request,raw,{'message':str(error.value)})
    assert request['input_budget']['proxy_input_tokens']<=MAX_INPUT_TOKENS
    assert repair['input_budget']['proxy_input_tokens']<=MAX_INPUT_TOKENS
    assert json.loads(repair['user_prompt'])['original_input']==json.loads(request['user_prompt'])


@pytest.mark.parametrize('size',[28801,32001,40000,64000])
def test_full_request_observation_is_not_a_rejection(size):
    from src.skill_evolution.evidence_review_prompt_v19 import check_review_budget
    from src.skill_evolution.edit_memory_review_v19 import MAX_INPUT_TOKENS
    for kind in ('initial','repair'):
        request={'input_budget':{'proxy_input_tokens':size},'kind':kind}
        check_review_budget(request,MAX_INPUT_TOKENS)
        assert request['input_budget']['above_observation_threshold']==(size>32000)
    with pytest.raises(ValueError,match='budget'):
        check_review_budget({'input_budget':{'proxy_input_tokens':64001}},MAX_INPUT_TOKENS)
