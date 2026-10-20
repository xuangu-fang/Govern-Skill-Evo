"""One explicitly authorized exact-input R5 Memory character-limit exception."""
import json
from pathlib import Path
from src.adapters.alfworld.skill_runtime import object_digest
from src.adapters.alfworld.verify_skill_run import require
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'benchmarks/alfworld').is_dir())
AMENDMENT_PATH=ROOT/'artifacts/methods/v22/23_alfworld57_five_round/recovery_06_control/capacity_amendment.json'

def character_limit(messages,plan,stage):
    base=plan['budget']['evolution_input_unicode_chars_max']
    wire=json.dumps(messages,ensure_ascii=False,separators=(',',':'))
    if len(wire)<=base:return base
    amendment=json.loads(AMENDMENT_PATH.read_text())
    require(amendment['schema']=='v22.alfworld57.authorized_memory_capacity_exception.v1'
            and amendment['authorization']=='User: 暂时无视超过冻结的 400,000 上限，使其5轮全部完成'
            and amendment['original_plan_sha256']==object_digest(plan)
            and amendment['original_character_limit']==base==400000
            and stage==amendment['scope']['stage']=='post_gate_learning'
            and amendment['scope']['round']==5
            and object_digest(messages)==amendment['scope']['messages_sha256']
            and len(wire)==amendment['scope']['messages_unicode_chars']==amendment['effective_character_limit']
            and amendment['context_tokens']==1000000 and amendment['requested_output_tokens']==65536
            and amendment['algorithm_prompt_model_gate_changes'] is False
            and amendment['content_removed_or_truncated'] is False,
            'Oversized input is outside the authorized exact R5 Memory exception.')
    return amendment['effective_character_limit']
