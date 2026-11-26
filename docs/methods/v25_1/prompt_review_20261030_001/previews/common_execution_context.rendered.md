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
5 rows and 20 columns per worksheet with cell
coordinates. Cell text is limited to 40 characters. After
all worksheet previews are generated, a preview longer than
100000 characters causes an explicit input-protocol error
before any Actor request; it is not truncated to fit this limit. Formula text
is shown, and row, column, and cell-text omissions are marked. Unshown cells
are not absent cells. Access to the full
input file does not establish that the model saw its contents before acting.

Capabilities and attempts
The Actor has no interactive shell, file browser, Python session, or workbook
inspection tool. It returns one complete Python script in a python fenced
block. An external executor runs the script with INPUT_PATH and OUTPUT_PATH
bound to the current attempt's paths. The supported libraries are
Python standard library, openpyxl, pandas. The program can read the complete original input and
write within its current attempt's output and temporary space. It cannot
access reference answers, previous attempts' files, other tasks, the network,
or external command execution. A fresh attempt starts from the original input.
The executor does not repair the task algorithm.

History and runtime feedback
Within a task, formal history retains the original messages, executed
program responses and returned execution-feedback messages. It has no
cross-task conversation. At most 30 actual program executions are
allowed, including successful submission. Each executable program allows at most
6 total API requests, including the first. Network failures, truncation,
empty outputs and format retries share this budget and do not consume executions.
Technical failures, truncated and empty responses retry the current request unchanged.
Complete invalid responses are corrected using only the latest invalid response and
its validation error, temporarily appended to the formal execution history. This
temporary context is replaced on another format error and cleared after execution.
Only executed responses and actual execution feedback enter formal history.
The execution evidence view excludes generation failures and temporary corrections;
its request_messages reconstruct formal history, not every actual API request.
Full requests, responses and usage remain in the raw audit archive. Generation
budget exhaustion preserves the checkpoint and pauses without scoring the task.
Budgets persist across resume; request allowance renews only after execution.

For the execution_only_v1 profile used here, formal history consists of initial
messages, executed program responses and returned execution feedback. Temporary
format-correction context contains the latest invalid response and validation
error; it is replaced on another format error and cleared after execution.
The execution evidence view reconstructs formal history in request_messages and
omits generation failures and temporary corrections. Only raw archived API messages
establish the full request when those records are supplied. Do not assume access
to raw archives outside the module input, or treat omitted context as never seen.

Only response-format errors, program execution errors, and missing or
unreadable output-file errors can be returned to the Actor. Error details
retain only the first 3000 characters when longer
than that limit, with marked truncation. They contain actual runtime
information, not evaluator findings
or extra solution advice. Successful stdout does not open an exploration
round. An exception deliberately used to inspect data is still a budgeted
attempt. Stored logs are not necessarily feedback the Actor received.

Budgets and stopping
Each generation has an output limit of 49152 tokens.
The request timeout is 300 seconds and each program execution timeout is
600 seconds. There is no cumulative Actor task time limit. Preparation,
requests, retry waiting, execution and output checks are recorded for
observability but do not consume a shared task time budget. Each request and
program retains its own timeout. Code-attempt and request-retry limits
persist across resume and are never reset.

The first normally terminated program that produces an openable .xlsx at
OUTPUT_PATH ends the Actor execution. Opening a workbook is not a correctness
check. A missing target sheet or an incorrect answer discovered by grading
cannot reopen the Actor. Exhausting program executions
without a valid submission is a task failure. API or execution-infrastructure
interruptions and scoring failures are recorded separately, not silently
converted into model failures or omitted from the batch. History retained by the configured protocol is not silently shortened to fit a
request; protocol-defined removal of temporary format corrections is separate.

Formula and scoring conditions
The formula policy is No additional formula recalculation; grading reads saved cell values with data_only=True.. In the initial profile,
there is no automatic formula recalculation; grading reads saved cell values
with data_only=True. Writing a valid formula does not establish that a cached
result exists. The shared Actor system prompt states these formula conditions and
that scoring feedback is unavailable. The requested deliverable is defined by the task.
Inspect the supplied Actor messages for the conditions visible in a particular run;
historical runs may use older prompts.

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
The coordinate and missing-sheet lists are limited to 100
and 100 entries respectively; marked truncation does
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
Perform the user's spreadsheet task. Return one complete Python script in a
single ```python``` fenced block, without explanation. Read INPUT_PATH and save
the result to OUTPUT_PATH; the executor supplies these variables. Do not reassign
them, hardcode file paths, print output, or use input(). Use only the standard
library, openpyxl and pandas.

## Execution conditions

An external executor runs your script; there are no interactive tools. Exploration
and self-checks belong in the script, which can read the full workbook despite the
limited preview. Each execution starts from the original input without prior
attempts' files. Skill template path placeholders mean the supplied variables.

Format, execution, and missing or unreadable output-file errors may be returned;
respond with a complete replacement script. The first normally terminated program
producing an openable .xlsx at OUTPUT_PATH ends the task, regardless of correctness.
Scores, wrong-cell coordinates and reference answers are not returned to you.

Formulas are not automatically recalculated. Evaluation uses data_only=True to
read saved cell values or formula caches; writing a formula with openpyxl does
not calculate its cache. Deliver the result requested by the task.

## Library Selection

| Use case | Library |
|----------|---------|
| Preserve formulas, formatting, named ranges | `openpyxl` |
| Bulk data transformation, aggregation, sorting | `pandas` → write back with `openpyxl` |
| Simple cell read/write | `openpyxl` |

**Warning**: `pandas.to_excel()` silently destroys existing formulas and named ranges. When writing back to a spreadsheet that contains formulas, always load with `openpyxl.load_workbook(...)`, mutate values in place, and persist via `wb.save(OUTPUT_PATH)`.

## Output Requirements

- Do not hardcode row counts or column letters — iterate over actual rows in the workbook (`ws.max_row`, `ws.iter_rows(...)`).
- Preserve sheets and cells not mentioned in the instruction.
- When in doubt about which sheet to mutate, use `wb.active` only if the workbook has a single sheet; otherwise explicitly pick by name.[runtime field: skill_section]

</actor_system_prompt>
<actor_initial_template>
# Instruction
[runtime field: instruction][runtime field: task_metadata]

# Input spreadsheet preview
[runtime field: workbook_preview]

# Task
Write a Python script that reads the workbook from `INPUT_PATH`, applies the instruction, and writes the modified workbook to `OUTPUT_PATH`. Preserve all other cells unchanged. The preview may be truncated — do not hardcode row counts or assume the data ends at the last previewed row; iterate over all actual rows in the workbook instead. Return only a ```python``` code block.
</actor_initial_template>
<actor_runtime_feedback_template>
# Runtime feedback
category: [runtime field: error_category]
exit_status: [runtime field: exit_status]

[runtime field: error_detail_prefix]

detail_truncated: [runtime field: detail_truncated]

Correct the reported execution or output-file error and return one complete Python script in a single python fenced block.

</actor_runtime_feedback_template>

These templates describe what can be sent. Raw archived API messages determine
what was actually sent; execution-only evidence shows formal history and omits
temporary format corrections even when they influenced the executed response. A post-execution record does not
become Actor-visible merely because an optimization module can read it.
