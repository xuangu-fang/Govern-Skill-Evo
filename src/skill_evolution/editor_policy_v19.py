"""Task-facing rule text; provenance stays in the existing edit ledger."""
import re
from .editor_contract_v18 import EditorRejected

INSTRUCTIONS = '''
Write a flat collection of task-facing rules. Do not emit Markdown headings or
recreate category sections from Parent. The program removes inherited section
headings as an audited layout change. Preserve all applicable rule content.
Describe conditions and actions in task language. Do not copy experiment group,
check, finding, trajectory or evidence identifiers into Skill text. Translate their
meaning using the supplied evidence; if that meaning is unavailable, return UNABLE.
Keep actual tool names, argument names and domain identifiers needed for execution.
Source identifiers belong in the existing provenance, not the guidance text.
'''


def internal_ids(audit):
    ids=set()
    def walk(v,key=''):
        if isinstance(v,dict):
            for k,x in v.items():walk(x,k)
        elif isinstance(v,list):
            for x in v:walk(x,key)
        elif isinstance(v,str) and key in ('group_id','group_ids','constraint_id','check_id',
                'context_ref','goal_id','finding_id','issue_id','proposal_id','trajectory_ref','evidence_ref'):
            ids.add(v)
    walk(audit)
    return ids


def validate_text(text, ids):
    if re.search(r'(?m)^\s*#{1,6}\s+|^\s*(?:={3,}|-{3,})\s*$',text):
        raise EditorRejected('OUTPUT_POLICY','Write flat rule text without Markdown headings or section separators')
    found=[ref for ref in sorted(ids) if re.search(r'(?<![\w])'+re.escape(ref)+r'(?![\w])',text)]
    # Namespaced provenance is unambiguously internal even if invented by the model.
    found+=re.findall(r'\b(?:CF|ISSUE|EDIT|ATTRIBUTION|CURRENT|PAIR|POLICY|RULE|HO|HR)/[^\s,;]+',text)
    if found:
        raise EditorRejected('OUTPUT_POLICY','Replace internal provenance IDs with task semantics: '+', '.join(found[:8]))
