import json
from src.skill_evolution.v19.contract_repair_v19 import build_repair
from src.skill_evolution.v19.edit_tracking_v19 import digest


def test_shared_repair_preserves_input_response_and_shortens_only_feedback():
    raw='{"incomplete": "'+('evidence '*1000)
    original={'prompt_version':'example','system_prompt':'Original rules',
              'user_prompt':'{"evidence":"full original"}',
              'response_format':{'type':'json_object'},'max_completion_tokens':24000}
    error={'type':'ValueError','stage':'LINKAGE','message':'Missing ref X. '*1000,'raw_response_sha256':digest(raw)}
    repair=build_repair(original,raw,error);body=json.loads(repair['user_prompt'])
    assert body['previous_raw_response']==raw
    assert body['original_input']==json.loads(original['user_prompt'])
    assert len(body['validation_error']['message'])<2100
    assert 'raw_response_sha256' not in body['validation_error']
    assert error['message']=='Missing ref X. '*1000
    assert repair['response_format']==original['response_format']
    assert repair['max_completion_tokens']==24000
    from src.skill_evolution.v19.memory_review_repair_v19 import build_repair as memory
    from src.skill_evolution.v19.memory_generation_prompt_v19 import build_memory_diagnosis_repair_request
    from src.skill_evolution.v19.attribution_pairs_v19 import repair_request
    assert memory(original,raw,error)==build_memory_diagnosis_repair_request(original,raw,error)==repair_request(original,raw,error)==repair
