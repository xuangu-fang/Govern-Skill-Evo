"""Bind the approved Diagnosis to the existing full-batch evidence contract."""
from dataclasses import replace

from . import protocol
from . import _shared_diagnosis as shared
from ._shared_diagnosis import (
    CONTRACT_VERSION, INPUT_VIEW, PROMPT_PATH, DiagnosisCall, _validate_output,
    diagnosis_input, model_input, referenced_runs, validate_diagnosis, validate_input,
    validate_model_input,
)

PROMPT_VERSION = protocol.DIAGNOSIS_VERSION


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    protocol.require(prompt_version == PROMPT_VERSION, 'Unknown diagnosis prompt version')
    return protocol.render_prompt(PROMPT_PATH, background)


def diagnosis_call(saved):
    return replace(shared.diagnosis_call(saved), prompt_version=PROMPT_VERSION)
