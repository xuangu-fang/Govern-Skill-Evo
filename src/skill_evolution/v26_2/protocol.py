"""The v26.1 OfficeQA protocol and the two v26.2 experiment settings."""
from copy import deepcopy
from itertools import accumulate
from ..v26_1 import protocol as baseline
from ..v26_1.protocol import (
    ACTOR, FORMAL_CONTEXT, IDENTITY, LIMITS, MODEL_INPUT_VIEW, PROMPT_ROOT,
    RECORD_VERSION, REVISION, ROOT, SCORER_PROFILE, actor_base_protocol, actor_config,
    background, digest, equal, execution_context, expected_background, fields,
    initial_skill, public_task, render_prompt, require, score_view, source_pages,
    validate_actor, validate_task,
)

DESIGN = ROOT / 'docs/methods/v26_2'
PRECONDITIONER_PATH = DESIGN / 'prompts/preconditioner.md'
METHOD_VERSION = 'v26_2_campaign_v1'
PRECONDITIONER_VERSION = 'v26_2_officeqa_preconditioner_v1'

# Copy only the runtime settings. The historical design status, results and
# acceptance metadata describe v26.1 and do not belong to this campaign.
PLAN = {key: deepcopy(baseline.PLAN[key]) for key in (
    'method', 'benchmark', 'schedule', 'actor', 'actor_task_output_limits',
    'execution', 'module_calls', 'max_attempts', 'continue_no_change',
    'retry_delay_seconds', 'max_input_chars', 'max_message_utf8_bytes',
)}
schedule = PLAN['schedule']
ordered_ids = [uid for batch in schedule['batches'] for uid in batch]
schedule['batch_sizes'] = [11, 11, 11, 11, 10, 10, 10]
boundaries = list(accumulate(schedule['batch_sizes'], initial=0))
require(boundaries[-1] == len(ordered_ids), 'Schedule must cover the optimization pool')
schedule['batches'] = [ordered_ids[start:end] for start, end in zip(boundaries, boundaries[1:])]
PLAN['method']['version'] = METHOD_VERSION
PLAN['method']['prompts']['preconditioner'] = PRECONDITIONER_VERSION
# Prompt paths in a method plan are relative to its design directory.
PLAN['method']['prompt_paths'] = {
    name: path if name == 'preconditioner' else f'../v26_1/{path}'
    for name, path in baseline.PLAN['method']['prompt_paths'].items()
}
