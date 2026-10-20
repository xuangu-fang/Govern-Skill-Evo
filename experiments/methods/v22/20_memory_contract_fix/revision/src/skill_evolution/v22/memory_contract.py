"""v5 clarifies existing retirement field names; no learning semantics change."""
import json
from . import unified_dsc

PROFILE = "v22.unified_dsc.v5"
RULE_VERSION = "v22.memory_retirement_fields.v1"

# A synthetic delta, not an instruction to replace any actual input Effect.
RETIREMENT_EXAMPLE = {
    "replace": ["old:m1"], "claim": "Current f1 corrects the tested part of the old assertion.",
    "limits": ["The remaining condition is still untested."], "findings": ["f1"],
    "retire_limits": [{"effect_id": "old:m1", "index": 0,
                       "reason": "Current f1 corrects this active limit's tested part.",
                       "findings": ["f1"]}],
}

OLD = """Each retirement
names an effect in replace, its exact zero-based ACTIVE limit index, a specific reason
and current finding IDs also in this delta.findings."""
NEW = """Each retirement is an object with EXACTLY these fields:
effect_id: string, an existing input Effect ID also listed in this delta.replace;
index: integer (not boolean), the zero-based index in that Effect's current ACTIVE
limits, 0 <= index < len(limits); reason: nonempty string giving the specific evidence;
findings: nonempty array of current Finding ID strings, all also in this delta.findings.
Do not repeat an (effect_id, index) pair. Use these exact keys, not effect or limit_index.
Synthetic format example ONLY: assume old:m1 is an input Effect with active limit 0,
and current finding f1 supports correcting its tested part. Use actual IDs/evidence,
never copy these illustrative IDs. This example does not require retirement:
""" + json.dumps(RETIREMENT_EXAMPLE, separators=(",", ":"))
assert unified_dsc.LEARNING_RULES.count(OLD) == 1
LEARNING_RULES = unified_dsc.LEARNING_RULES.replace(OLD, NEW)
