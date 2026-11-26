"""Lossless OfficeQA timeline encoding after source validation and scope selection."""
from copy import deepcopy
from src.skill_evolution.v26.benchmarks.officeqa import input_view as native
from .protocol import fields, require

INPUT_VIEW = 'v26_1_officeqa_formal_lossless_v1'
FIELDS = {'diagnosis': ('parent', 'runs'),
          'preconditioner': ('parent', 'plan', 'runs', 'memory'),
          'replay': ('parent', 'diff', 'plan', 'edits', 'pairs', 'runs')}


def model_input(view, *, module):
    fields(view, FIELDS[module], module + ' input')
    encoded = native.project(view)
    # v2 histories serve partial citations only. No unused history format is advertised.
    if native.HEADER in encoded and not native.has_history_pointers(encoded):
        encoded = native.project(view, input_view=native.PREVIOUS)
    raw = deepcopy(view)
    if len(native.exact(raw).encode('utf-8')) < len(native.exact(encoded).encode('utf-8')):
        encoded = raw
    require(native.equal(native.restore(encoded), view), 'OfficeQA view is not lossless')
    return encoded


def restore_model_input(view, *, module):
    restored = native.restore(view)
    fields(restored, FIELDS[module], module + ' input')
    return restored


def validate_model_input(view, *, original, module):
    require(native.equal(restore_model_input(view, module=module), original) and
            native.equal(model_input(original, module=module), view), 'OfficeQA encoded input differs')
    return view
