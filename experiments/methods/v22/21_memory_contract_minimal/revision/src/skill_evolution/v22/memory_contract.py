"""Exact retirement field clarification; all prior learning rules unchanged."""
from . import unified_dsc
PROFILE = "v22.unified_dsc.v5.minimal"
RULE_VERSION = "v22.memory_retirement_fields.v2"
OLD = """Each retirement
names an effect in replace, its exact zero-based ACTIVE limit index, a specific reason
and current finding IDs also in this delta.findings."""
ADDITION = '''Each non-empty retire_limits entry must contain exactly:
{"effect_id": string, "index": integer, "reason": string, "findings": string[]}.
Use these exact field names.'''
NEW = OLD + "\n" + ADDITION
assert unified_dsc.LEARNING_RULES.count(OLD) == 1
LEARNING_RULES = unified_dsc.LEARNING_RULES.replace(OLD, NEW)
