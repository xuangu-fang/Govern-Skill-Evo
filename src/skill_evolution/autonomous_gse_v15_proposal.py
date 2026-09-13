"""Independent v15 deterministic compilation and bounded hypothesis proposal."""
import copy
from dataclasses import dataclass
from .information_boundary_v15 import BoundaryError, Envelope, unpack, _seal
from .diagnosis_compiler_v15 import compile_semantic_diagnosis
from .skill_text_v15 import parse_skill, render_skill

SEMANTIC_ORIGINS = {'TRAJECTORY_DERIVED', 'LEARNER_INFERRED', 'LEARNER_SAFE_SUPERVISION'}


@dataclass(frozen=True)
class DiagnosisEditorRequest:
    hypotheses: Envelope


def build_editor_request(diagnoses):
    if not isinstance(diagnoses, tuple) or not diagnoses:
        raise BoundaryError('Safe inferred diagnoses required')
    accepted, decisions, parents = [], [], set()
    for i, envelope in enumerate(diagnoses, 1):
        value = unpack(envelope, 'LEARNER_INFERRED')
        if value['semantic_origin'] != 'LEARNER_INFERRED':
            raise BoundaryError('ORACLE_DERIVED or unknown semantics')
        expected_origins = {
            **{key: 'LEARNER_INFERRED' for key in value['semantic']},
            **{'target_behavior.' + key: 'LEARNER_INFERRED' for key in value['semantic']['target_behavior']},
            'source_refs': 'TRAJECTORY_DERIVED',
            'supervision_refs': 'LEARNER_SAFE_SUPERVISION',
        }
        if value.get('field_provenance') != expected_origins:
            raise BoundaryError('Unknown or Oracle-derived field provenance')
        parent = value['current_skill']
        parents.add(parent)
        compiled, trace = compile_semantic_diagnosis(value['semantic'], parse_skill(parent))
        decisions.append({'decision': compiled, 'trace': trace})
        if compiled['update_eligible']:
            accepted.append({
                'patch_id': f'H{i:03d}', 'domain': value['domain'],
                'operation': compiled['operation'], 'section': compiled['target_section'],
                'target_rule_id': compiled['target_rule_id'] or '',
                'semantic': value['semantic'], 'provenance': value['provenance'],
                'semantic_origin': 'LEARNER_INFERRED',
                'field_provenance': value['field_provenance'],
            })
    if len(parents) != 1:
        raise BoundaryError('Cross-task Parent mismatch')
    if not accepted:
        return None, decisions
    return DiagnosisEditorRequest(_seal('EDITOR_SAFE_HYPOTHESES', {
        'current_skill': next(iter(parents)), 'eligible_hypotheses': accepted,
    })), decisions


def editor_payload(request):
    if not isinstance(request, DiagnosisEditorRequest):
        raise BoundaryError('Require v15 Editor request')
    data = unpack(request.hypotheses, 'EDITOR_SAFE_HYPOTHESES')
    if any(v['semantic_origin'] != 'LEARNER_INFERRED' for v in data['eligible_hypotheses']):
        raise BoundaryError('Untrusted semantic provenance')
    return data


def apply_editor_output(request, raw):
    """Keep add/replace/delete and source-lineage guards, not Oracle correctness."""
    import json
    data = editor_payload(request)
    try:
        result = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise BoundaryError('Malformed Editor JSON') from exc
    if not isinstance(result, dict) or set(result) != {'canonical_edits'} or not isinstance(result['canonical_edits'], list):
        raise BoundaryError('Invalid Editor result')
    sections = copy.deepcopy(parse_skill(data['current_skill']))
    sources = {p['patch_id']: p for p in data['eligible_hypotheses']}
    used, targets = set(), set()
    for edit in result['canonical_edits']:
        fields = {'derived_from_patch_ids', 'operation', 'section', 'target_rule_id', 'text', 'reason', 'verification_hypothesis'}
        if not isinstance(edit, dict) or set(edit) != fields:
            raise BoundaryError('Unexpected Editor metadata')
        ids = edit['derived_from_patch_ids']
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids) or not set(ids) <= set(sources) or used & set(ids):
            raise BoundaryError('Invalid hypothesis provenance')
        used.update(ids)
        src = [sources[i] for i in ids]
        if any(p['operation'] != edit['operation'] for p in src):
            raise BoundaryError('Compiler operation drift')
        section = edit['section']
        if section not in sections:
            raise BoundaryError('Invalid section')
        if not all(isinstance(edit[k], str) for k in ['operation','section','target_rule_id','text','reason']):
            raise BoundaryError('Invalid edit fields')
        vh = edit['verification_hypothesis']
        if not isinstance(vh, dict) or set(vh) != {'problem','trigger_condition','expected_behavior'} or not all(isinstance(v, str) and v.strip() for v in vh.values()):
            raise BoundaryError('Verification must be a learner hypothesis')
        domains = {p['domain'] for p in src}
        if len(domains) == 1 and edit['operation'] != 'delete' and not edit['text'].startswith('For ' + next(iter(domains)) + ' requests,'):
            raise BoundaryError('Domain scope missing')
        if '\n' in edit['text'] or (edit['operation'] != 'delete' and not edit['text'].strip()):
            raise BoundaryError('Invalid Skill rule')
        if edit['operation'] == 'add':
            if edit['target_rule_id']:
                raise BoundaryError('Add must not target a rule')
            sections[section].append({'rule_id': '', 'clause': edit['text']})
        elif edit['operation'] in {'replace','delete'}:
            target = edit['target_rule_id']
            if target in targets or any(p['target_rule_id'] != target or p['section'] != section for p in src):
                raise BoundaryError('Rule target drift')
            matches = [r for r in sections[section] if r['rule_id'] == target]
            if len(matches) != 1:
                raise BoundaryError('Unknown target rule')
            targets.add(target)
            if edit['operation'] == 'delete':
                if edit['text']:
                    raise BoundaryError('Delete text must be empty')
                sections[section].remove(matches[0])
            else:
                matches[0]['clause'] = edit['text']
        else:
            raise BoundaryError('Invalid operation')
    return _seal('LEARNER_INFERRED_SKILL', {
        'candidate_skill': render_skill(sections, data['current_skill'].splitlines()[0]),
        'canonical_edits': result['canonical_edits'], 'semantic_origin': 'LEARNER_INFERRED',
    })


class MultiRolloutDiagnosisProposalOperator:
    """Same diagnose → deterministic compile → Editor → Candidate skeleton."""
    def propose(self, requests, *, diagnosis_call, editor_call):
        diagnoses = tuple(diagnosis_call(r) for r in requests)
        editor_request, decisions = build_editor_request(diagnoses)
        if editor_request is None:
            return {'status': 'NO_UPDATE_ELIGIBLE_DIAGNOSIS', 'decisions': decisions, 'candidate': None}
        candidate = editor_call(editor_request)
        unpack(candidate, 'LEARNER_INFERRED_SKILL')
        return {'status': 'CANDIDATE_CREATED', 'decisions': decisions, 'candidate': candidate}
