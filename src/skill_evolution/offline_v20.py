"""Read-only validation and conservative conversion of existing v19 artifacts.

This module never writes a v20 Memory head and never claims that converted
records are v20 experimental outcomes. It preserves issue observations while
leaving attempts empty when v19 cannot prove a local edit association.
"""
from dataclasses import dataclass
from pathlib import Path
import json

from .edit_tracking_v19 import encode, digest
from .issue_memory_v20 import validate_memory, merge_update


@dataclass(frozen=True)
class OfflineReport:
    payload_json: str
    @property
    def payload(self): return json.loads(self.payload_json)


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def convert_v19_issue_fusion(*, run_id, round_id, fusion_result, source_prefix='V19_OFFLINE'):
    """Convert only issue statements and provenance; never invent attempts.

    v19 Fusion has no stable v20 attempt ownership for most proposals. Such
    records become problem-only Memory entries. A later v20 round may attach a
    real edit through the normal update path after local evidence review.
    """
    p = fusion_result.payload if hasattr(fusion_result, 'payload') else fusion_result
    issues = []
    for index, item in enumerate(p.get('issues', [])):
        if item.get('decision') not in ('PROPOSE', 'NO_EDIT'):
            continue
        key = f'{source_prefix}/{p.get("input_ref", "UNKNOWN")}/{index}'
        refs = list(dict.fromkeys(item.get('source_finding_refs', []) + item.get('historical_refs', [])))
        issues.append({'new_issue_key': key, 'problem': item['issue_statement'],
            'source_refs': refs or [f'{source_prefix}/ISSUE/{index}']})
    return {'schema_version': 'issue_memory_update_v20.1', 'run_id': run_id,
        'round_id': round_id, 'issues': issues}


def convert_v19_diagnosis(*, run_id, round_id, diagnosis, source_prefix='V19_OFFLINE'):
    """Convert existing v19 gap observations without pretending they were edits."""
    p = diagnosis.payload if hasattr(diagnosis, 'payload') else diagnosis
    p = p.get('diagnosis', p)
    issues = []
    for index, gap in enumerate(p.get('parent_skill_gaps', [])):
        refs = list(dict.fromkeys(gap.get('evidence_refs', [])))
        issues.append({'new_issue_key': f'{source_prefix}/DIAGNOSIS/{index}',
            'problem': gap.get('gap') or gap.get('finding') or 'v19 diagnosis gap',
            'source_refs': refs or [f'{source_prefix}/DIAGNOSIS/{index}']})
    return {'schema_version': 'issue_memory_update_v20.1', 'run_id': run_id,
        'round_id': round_id, 'issues': issues}


def validate_v19_artifact(value, *, source_path=None):
    """Validate shape/provenance without loading private evaluator/Monitor data."""
    payload = _load(source_path) if source_path is not None else (value.payload if hasattr(value, 'payload') else value)
    if isinstance(payload, str):
        try: payload = json.loads(payload)
        except json.JSONDecodeError as exc: raise ValueError('invalid v19 artifact JSON text') from exc
    if not isinstance(payload, dict):
        raise ValueError('v19 artifact must be an object')
    schema = payload.get('schema_version', '')
    allowed = ('local_generation_v19.1', 'generation_audit_v19.1', 'issue_fusion_result_v19.1',
               'issue_fusion_response_v19.1', 'issue_fusion_input_v19.1', 'issue_fusion_input_v19.2',
               'memory_review_input_v19.1', 'historical_reviews_v19.1', 'reconciliation_input_v19.1',
               'reconciliation_input_v19.2', 'reconciliation_input_v19.3', 'reconciliation_input_v19.4',
               'issue_fusion_result_v20.1', 'memory_diagnosis_response_v19.1')
    if schema not in allowed:
        raise ValueError('unsupported offline artifact schema')
    if schema in ('issue_fusion_result_v19.1', 'issue_fusion_result_v20.1'):
        if not isinstance(payload.get('issues'), list): raise ValueError('issue result issues required')
        for issue in payload['issues']:
            if not {'issue_id', 'decision'} <= set(issue): raise ValueError('invalid issue proposal')
    if schema == 'issue_fusion_response_v19.1':
        if not isinstance(payload.get('issues'), list): raise ValueError('issue response issues required')
        for issue in payload['issues']:
            if not {'issue_statement', 'decision'} <= set(issue): raise ValueError('invalid issue response')
    if schema == 'memory_diagnosis_response_v19.1':
        body = payload.get('diagnosis', payload)
        if not isinstance(body.get('parent_skill_gaps'), list): raise ValueError('diagnosis gaps required')
    if schema == 'local_generation_v19.1':
        if not {'issue_fusion', 'evidence_reviews'} <= set(payload): raise ValueError('incomplete v19 local audit')
    return payload


def offline_validate_v19(*, artifacts, run_id='offline-v20', round_prefix='offline'):
    """Validate/convert a sequence of v19 result JSONs into an in-memory report.

    No model, campaign directory, or Memory head is touched. The report counts
    what was structurally observable and explicitly reports unconverted edits.
    """
    converted = []; schemas = []; proposals = 0; reviews = 0; unbound = 0
    for index, item in enumerate(artifacts):
        payload = validate_v19_artifact(item)
        schemas.append(payload['schema_version'])
        if 'issues' in payload:
            proposals += len(payload['issues'])
            converted.append(convert_v19_issue_fusion(run_id=run_id, round_id=f'{round_prefix}-{index+1:02d}',
                fusion_result=payload))
        body = payload.get('diagnosis', payload)
        if 'parent_skill_gaps' in body:
            proposals += len(body['parent_skill_gaps'])
            converted.append(convert_v19_diagnosis(run_id=run_id, round_id=f'{round_prefix}-{index+1:02d}',
                diagnosis=payload))
        if 'evidence_reviews' in payload:
            reviews += len(payload['evidence_reviews'])
            unbound += sum(1 for row in payload['evidence_reviews']
                           if not row.get('result', row).get('edit_refs'))
    return OfflineReport(encode({'schema_version': 'offline_validation_v20.1', 'mode': 'READ_ONLY',
        'artifact_count': len(artifacts), 'schemas': schemas, 'fusion_proposals': proposals,
        'review_records': reviews, 'unbound_edit_records': unbound,
        'converted_updates': converted,
        'claims': 'STRUCTURAL_OFFLINE_VALIDATION_ONLY_NO_V20_EXPERIMENT_RESULT'}))


def validate_converted_updates(updates, *, run_id):
    memory = {'schema_version': 'issue_memory_v20.1', 'run_id': run_id, 'issues': []}
    for update in updates:
        memory = merge_update(memory, update)
    return validate_memory(memory, run_id=run_id)
