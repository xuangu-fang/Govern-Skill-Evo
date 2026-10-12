"""Separated v19 findings/review DTOs and strict model output schemas.

Evidence status belongs only to historical review. No decision, mutation type,
compiler operation or generated Skill text is authorized by these contracts.
"""
from dataclasses import dataclass

from .edit_tracking_v19 import encode, parse, digest
from ..v18.diagnosis_contract_v18 import _object, _strings, _validate


def text_schema(*values):
    return {'type': 'string', **({'enum': list(values)} if values else {})}


FINDING_SCHEMA = _object({
    'kind': text_schema('OBSERVED_PROBLEM', 'EFFECTIVE_BEHAVIOR', 'COUNTEREVIDENCE', 'UNCERTAINTY'),
    'statement': text_schema(), 'applicability': text_schema(),
    'dimensions': {'type': 'array', 'items': text_schema('SUCCESS', 'COMPLIANCE')},
    'evidence_refs': _strings(), 'supervision_refs': _strings(),
    'policy_refs': _strings(), 'related_rule_refs': _strings(), 'uncertainty': _strings(),
})
CURRENT_SCHEMA = _object({
    'schema_version': text_schema('current_findings_response_v19.1'),
    'summary': text_schema(),
    'findings': {'type': 'array', 'items': FINDING_SCHEMA},
})
REVIEW_SCHEMA = _object({
    'schema_version': text_schema('historical_review_response_v19.1'),
    'reviews': {'type': 'array', 'items': _object({
        'historical_object_id': text_schema(),
        'evidence_status': text_schema('SUPPORTED', 'CONTRADICTED', 'MIXED', 'NOT_COVERED'),
        'supporting_current_refs': _strings(), 'contradicting_current_refs': _strings(),
        'context_current_refs': _strings(), 'current_finding_refs': _strings(),
        'historical_evidence_refs': _strings(),
        'coverage_reason': text_schema('ASSESSED', 'NO_RELEVANT_OBSERVATION', 'INSUFFICIENT_EVIDENCE'),
        'reason': text_schema(), 'uncertainty': _strings(),
    })},
})


@dataclass(frozen=True)
class CurrentDiagnosisInput:
    payload_json: str
    provenance_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def provenance(self):
        return parse(self.provenance_json)

    @property
    def input_ref(self):
        return 'CURRENT_INPUT/' + digest(encode({'payload': self.payload, 'provenance': self.provenance}))


@dataclass(frozen=True)
class CurrentFindings:
    """Runtime IDs are assigned after validation, not chosen by the model."""
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


@dataclass(frozen=True)
class MemoryReviewInput:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def input_ref(self):
        return 'MEMORY_REVIEW_INPUT/' + digest(self.payload_json)


@dataclass(frozen=True)
class HistoricalReviews:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


def checked_response(raw, schema):
    output = parse(raw)
    _validate(output, schema, 'response')
    return output
