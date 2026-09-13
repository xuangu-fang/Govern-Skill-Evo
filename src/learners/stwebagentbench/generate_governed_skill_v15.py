"""v15 bounded Editor; receives certified learner hypotheses, never Oracle input."""
import json
from src.skill_evolution.autonomous_gse_v15_proposal import editor_payload, apply_editor_output

EDITOR_SYSTEM_PROMPT = '''You are GSE-v15 bounded Editor. In one call, deduplicate,
generalize incidental details, normalize wording, select a Parent section, and write
Skill edits. Preserve the v14 bounded-edit skeleton. The eligible Diagnosis is a
LEARNER_INFERRED_HYPOTHESIS, not normative Oracle truth. It may be wrong. Do not
re-diagnose, consult canonical policy, evaluator answers, source code or Oracle IDs,
or correct hypotheses from hidden truth. Preserve uncertainty and counterevidence.
The deterministic Compiler determines allowed operation and target. Preserve each
source hypothesis's scope, trigger, decision boundary, repair and stopping boundary.
Do not strengthen or broaden a rule beyond its source. Preserve user control over
unresolved choices; do not invent deterministic selectors or exhaustive taxonomies.
Merge only compatible triggers, repair operators and predicates; shared operators
alone do not justify merging. Source-specific conditions remain branch-scoped.
Each source H ID contributes to at most one edit. Add selects an existing section
and empty target_rule_id; replace/delete retain the exact compiled section and rule.
Single-domain text starts with 'For airline requests,' or 'For retail requests,'.
Generalize episode IDs/dates/amounts when incidental, not mechanism-defining values.
Do not put source or supervision identifiers into Skill text. Verification is a
learner-generated hypothesis, not an oracle expected solution, and must match the
Skill rule without broadening or strengthening. Delete has empty text.
Return only canonical_edits JSON under the supplied schema.'''

_STRING = {'type': 'string'}
VERIFICATION_HYPOTHESIS_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['problem', 'trigger_condition', 'expected_behavior'],
    'properties': {k: _STRING for k in ['problem', 'trigger_condition', 'expected_behavior']},
}
_EDIT_PROPERTIES = {
    'derived_from_patch_ids': {'type': 'array', 'items': _STRING},
    'operation': {'type': 'string', 'enum': ['add','replace','delete']},
    **{k: _STRING for k in ['section','target_rule_id','text','reason']},
    'verification_hypothesis': VERIFICATION_HYPOTHESIS_SCHEMA,
}
EDITOR_RESPONSE_FORMAT = {'type':'json_schema','json_schema':{
    'name':'v15_canonical_edits','strict':True,'schema':{
        'type':'object','additionalProperties':False,'required':['canonical_edits'],
        'properties':{'canonical_edits':{'type':'array','items':{
            'type':'object','additionalProperties':False,
            'required':list(_EDIT_PROPERTIES),'properties':_EDIT_PROPERTIES,
        }}},
    },
}}


def build_editor_prompts(request):
    return EDITOR_SYSTEM_PROMPT, json.dumps(editor_payload(request), ensure_ascii=False, sort_keys=True)


def call_governed_editor(request, *, learner_call):
    system, user = build_editor_prompts(request)
    response = learner_call(system, user, EDITOR_RESPONSE_FORMAT)
    return apply_editor_output(request, response)
