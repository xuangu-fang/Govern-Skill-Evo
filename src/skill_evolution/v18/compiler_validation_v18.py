"""Strict edit-plan acceptance against the bound deterministic compilation."""
from dataclasses import asdict
import json

from .compiler_contract_v18 import CompilerRejected, EditPlan, build_edit_plan_schema
from .compiler_v18 import compile_edit_plan


def _check(value, schema):
    kind = schema['type']
    valid = {'object': type(value) is dict, 'array': type(value) is list,
             'string': type(value) is str, 'integer': type(value) is int}[kind]
    if not valid:
        raise CompilerRejected('PLAN', 'invalid field type')
    if kind == 'object':
        if set(value) != set(schema['properties']):
            raise CompilerRejected('PLAN', 'exact plan fields required')
        for key, child in schema['properties'].items():
            _check(value[key], child)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0):
            raise CompilerRejected('PLAN', 'missing plan entries')
        for item in value:
            _check(item, schema['items'])
        encoded = [json.dumps(item, sort_keys=True) for item in value]
        if len(set(encoded)) != len(encoded):
            raise CompilerRejected('PLAN', 'duplicate plan entries')
    elif kind == 'string' and not value.strip():
        raise CompilerRejected('PLAN', 'empty plan field')
    elif kind == 'integer' and value < schema.get('minimum', 0):
        raise CompilerRejected('PLAN', 'negative gap index')
    if 'enum' in schema and value not in schema['enum']:
        raise CompilerRejected('PLAN', 'invalid operation or status')
    if 'const' in schema and value != schema['const']:
        raise CompilerRejected('PLAN', 'invalid constant')


def plan_payload(plan: EditPlan) -> dict:
    """DTO tuples become JSON arrays; this is serialization, not plan repair."""
    return json.loads(json.dumps(asdict(plan), allow_nan=False))


def validate_edit_plan(plan, *, compiler_input) -> None:
    """Accept DTO or JSON object. Never sort, coerce or replace submitted content.

    Source acceptance is rerun and the submitted plan must equal the canonical
    compilation. This is not an independent semantic judge or compiler algorithm.
    """
    expected = plan_payload(compile_edit_plan(compiler_input))
    try:
        submitted = plan_payload(plan) if isinstance(plan, EditPlan) else plan
        _check(submitted, build_edit_plan_schema())
    except (TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, CompilerRejected):
            raise
        raise CompilerRejected('PLAN', 'invalid plan serialization') from exc
    if submitted != expected:
        raise CompilerRejected('PLAN', 'plan differs from bound canonical compilation')
