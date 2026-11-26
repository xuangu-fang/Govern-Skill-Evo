"""Lossless serialized-input limits with explicit output reservation accounting.

UTF-8 bytes plus framing is a conservative byte-token estimate, not a provider
usage measurement. A known provider context limit can be frozen explicitly in
call_config; no tokenizer or model capacity is inferred from the model name.
"""
import json
from .facts import require


def account(messages, call_config, *, max_input_chars, max_message_utf8_bytes):
    encoded=json.dumps(messages,ensure_ascii=False,allow_nan=False)
    size=len(encoded.encode('utf-8'));chars=len(encoded)
    require(chars<=max_input_chars and size<=max_message_utf8_bytes,
            'Input exceeds frozen character/UTF-8 capacity')
    reserve=call_config['max_tokens']
    # Serialization bytes already include role/JSON wrappers; extra framing is conservative.
    estimate=size+64*len(messages)+64
    total=estimate+reserve
    limit=call_config.get('context_window_tokens')
    if limit is not None:
        require(total<=limit,'Input plus reserved output exceeds frozen context capacity')
    return {'input_chars':chars,'input_utf8_bytes':size,'reserved_output_tokens':reserve,
            'context_token_upper_estimate':total,'context_window_tokens':limit,
            'estimator':'utf8_bytes_plus_conservative_message_framing_v1','provider_token_measurement':False}
