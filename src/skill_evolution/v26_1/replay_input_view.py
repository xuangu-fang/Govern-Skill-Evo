"""Replay uses the same OfficeQA codec, after EM-transition filtering."""
from . import execution_input_view as view
INPUT_VIEW = view.INPUT_VIEW

def model_input(payload):
    return view.model_input(payload, module='replay')
