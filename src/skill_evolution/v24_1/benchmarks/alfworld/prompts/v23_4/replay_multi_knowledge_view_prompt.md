## Replay paired-input view v1

Current `pairs` are verified task-level relationships. Each includes a task_id and
parent_result/candidate_result with status, success and steps. Steps count executed
actions, including invalid actions, not HTTP retries or unexecuted requests. An
interruption can have success=null. These are whole-task facts, not effects attributed
to an individual rule or phase.

Current `runs` follow pair order: each Parent immediately precedes its Candidate.
Their full initial states, steps, feedback and outcomes are unchanged. Timelines remain
independent: equal step numbers do not identify equivalent states or opportunities.
Use each side's actual conditions to compare behavior.

Historical `memory.pairs` contains context-qualified Parent/Candidate relationships
read from the original archives, only where both runs are present in this view.
Each item has context, parent and candidate. It is a task-level index, not step
alignment or behavioral evidence. `memory.unpaired_runs` lists supplied runs without
a complete visible verified pair (including unavailable pairing provenance). Do not
invent a counterpart or infer pairing from names, numbers or source order.

Historical entries are revisable interpretations; sources are the recorded evidence.
Use the unchanged Memory v3 evidence boundaries. A full action trace is not a full
state trace. Do not convert failure to find a target into proof of its global absence,
or combine events from different historical contexts. Preserve uncertainty where
needed. Current actual edits and paired executions are the primary new evidence;
historical Memory supports comparison and revision. The output contract is defined by the versioned main Prompt.
