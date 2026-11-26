"""Pure Replay output validation for the LMB evidence layer; no generation."""
from .facts import require
from .contracts.memory import MULTI_KNOWLEDGE_CONTRACT, validate_entries, run_references
from .memory_view import knowledge_only, historical_references, check_historical_prose

KNOWLEDGE_INPUT_VIEW = "v27_lmb_pairs_content_v1"
SUPPORTED_FORMATS = (KNOWLEDGE_INPUT_VIEW,)

def validate_result(result, payload, *, input_view=KNOWLEDGE_INPUT_VIEW, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    # Full archive validation checks existence and the unchanged output schema first.
    if input_view in SUPPORTED_FORMATS:
        require(memory_contract == MULTI_KNOWLEDGE_CONTRACT, 'Knowledge Only Replay requires multi-Knowledge output')
    validate_entries(result, payload, memory_contract=memory_contract)
    require(input_view in SUPPORTED_FORMATS,
            'Unsupported Replay input view')
    if input_view in SUPPORTED_FORMATS:
        view = knowledge_only(payload['memory'], memory_contract=memory_contract)
        allowed = historical_references(view)
        current = {ref for run in payload['runs'] for ref in run_references(run)}
        contexts = {ref.rsplit('/', 1)[0] for ref in payload['memory']['sources']}
        for entry_index, entry in enumerate(result['entries']):
            for item_index, item in enumerate(entry['knowledge']):
                history = {ref for ref in item['evidence'] if '/' in ref}
                require(history <= allowed, 'Unavailable historical reference in Knowledge evidence')
                check_historical_prose(item['text'], allowed, current=current, historical_contexts=contexts,
                                       location=f'entries[{entry_index}].knowledge[{item_index}].text')
    return result
