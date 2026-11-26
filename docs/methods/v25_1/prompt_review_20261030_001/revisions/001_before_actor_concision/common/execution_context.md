## SpreadsheetBench Execution Context

This section describes the Actor's execution conditions. It is evidence for
your assigned optimization role, not an instruction to solve the current task
or to request additional execution. Your module's own input contract still
determines which records you may use.

Actor-visible information
The Actor receives a fixed system instruction, the complete current Skill,
the task instruction, task type, answer region and its worksheet information,
and a bounded preview of the original input workbook. The Skill is fixed for
the entire task. The Actor does not receive Memory, another execution's code
or results, a reference workbook, expected values, or evaluator feedback.

The preview includes worksheet names and dimensions, then up to the first
{{preview_rows}} rows and {{preview_columns}} columns per worksheet with cell
coordinates. Cell text is limited to {{preview_cell_chars}} characters. After
all worksheet previews are generated, a preview longer than
{{preview_max_chars}} characters causes an explicit input-protocol error
before any Actor request; it is not truncated to fit this limit. Formula text
is shown, and row, column, and cell-text omissions are marked. Unshown cells
are not absent cells. Access to the full
input file does not establish that the model saw its contents before acting.

Capabilities and attempts
The Actor has no interactive shell, file browser, Python session, or workbook
inspection tool. It returns one complete Python script in a python fenced
block. An external executor runs the script with INPUT_PATH and OUTPUT_PATH
bound to the current attempt's paths. The supported libraries are
{{allowed_libraries}}. The program can read the complete original input and
write within its current attempt's output and temporary space. It cannot
access reference answers, previous attempts' files, other tasks, the network,
or external command execution. A fresh attempt starts from the original input.
The executor does not repair the task algorithm.

History and runtime feedback
{{context_history_description}}
{{context_attempt_budget_description}}

Only response-format errors, program execution errors, and missing or
unreadable output-file errors can be returned to the Actor. Error details
retain only the first {{runtime_error_detail_chars}} characters when longer
than that limit, with marked truncation. They contain actual runtime
information, not evaluator findings
or extra solution advice. Successful stdout does not open an exploration
round. An exception deliberately used to inspect data is still a budgeted
attempt. Stored logs are not necessarily feedback the Actor received.

Budgets and stopping
Each generation has an output limit of {{actor_max_output_tokens}} tokens.
{{context_time_budget_description}}

The first normally terminated program that produces an openable .xlsx at
OUTPUT_PATH ends the Actor execution. Opening a workbook is not a correctness
check. A missing target sheet or an incorrect answer discovered by grading
cannot reopen the Actor. Exhausting {{actor_exhaustion_conditions}}
without a valid submission is a task failure. API or execution-infrastructure
interruptions and scoring failures are recorded separately, not silently
converted into model failures or omitted from the batch. Complete history is
not silently shortened to fit a request.

Formula and scoring conditions
The formula policy is {{formula_policy_description}}. In the initial profile,
there is no automatic formula recalculation; grading reads saved cell values
with data_only=True. Writing a valid formula does not establish that a cached
result exists. The shared Actor system prompt states these formula conditions and
that scoring feedback is unavailable. These are environment facts, not an instruction
to replace every required formula with a literal. Inspect the supplied Actor messages
for the conditions visible in a particular run; historical runs may use older prompts.

Scoring occurs only after submission. The main score, hard, is one only when
all designated answer cells pass the shared comparison rules. The auxiliary
per_cell_pass_rate is correct cells divided by graded cells for each task;
aggregate reports average these task-level rates. Neither score is runtime
feedback. Comparison is limited to the evaluator's supported value semantics;
it does not establish that all formatting, formulas, or non-target cells are
correct.

For optimization tasks, permitted post-execution evidence includes scores,
exact cell counts, bounded mismatched coordinates, and missing-sheet names,
subject to your module's input contract. It excludes expected answer values.
The coordinate and missing-sheet lists are limited to {{score_coordinate_limit}}
and {{score_missing_sheet_limit}} entries respectively; marked truncation does
not change the exact counts. Never describe this later evidence as information
the Actor received. Do not propose a Skill step that waits for grader feedback.
Generalize executable rules from evidence; do not copy task answers into Skill
or Knowledge. Test results are for final reporting, not optimization.

Pairing and evidence interpretation
The same Parent execution is reused for diagnosis, Gate, and Replay. Candidate
executes independently from the original input under the same feedback and
budget conditions. It receives no Parent transcript or result. Gate accepts
only a strict increase in successful tasks over the complete paired batch;
the auxiliary metric does not break ties. A no_change branch does not create
Candidate executions. A score change alone is not proof that one Skill edit
caused it. Code text is not a record of which runtime branches executed.

Actual Actor message templates
<actor_system_prompt>
{{actor_system_prompt}}
</actor_system_prompt>
<actor_initial_template>
{{actor_initial_template}}
</actor_initial_template>
<actor_runtime_feedback_template>
{{actor_runtime_feedback_template}}
</actor_runtime_feedback_template>

{{evidence_history_description}} A post-execution record does not
become Actor-visible merely because an optimization module can read it.
