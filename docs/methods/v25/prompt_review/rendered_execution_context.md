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
Within a task, the model retains the original messages and every complete
assistant response and returned runtime-feedback message. It has no
cross-task conversation. There are at most 30 code attempts;
a complete malformed or truncated generation also consumes an attempt.
Transport retries are counted separately, with at most
6 total request attempts per generation, including
the first. Retries of an incomplete request keep the same messages. Remaining
code attempts are reported after each completed response when continuing.

Only response-format errors, program execution errors, and missing or
unreadable output-file errors can be returned to the Actor. Error details
retain only the first 3000 characters when longer
than that limit, with marked truncation. They contain actual runtime
information, not evaluator findings
or extra solution advice. Successful stdout does not open an exploration
round. An exception deliberately used to inspect data is still a budgeted
attempt. Stored logs are not necessarily feedback the Actor received.

Budgets and stopping
Each generation has an output limit of 16384 tokens.
The request timeout is 300 seconds, the program
timeout is 600 seconds, and the Actor task budget is
600 seconds. The task clock starts when an execution
slot is acquired and input preparation begins; it includes preparation,
requests, retry waiting, execution, and output checks. Queue waiting and
post-submission scoring are outside this Actor budget. In-flight operations
are bounded by remaining task time. These are upper limits, not guarantees
of that much time for every attempt.

The first normally terminated program that produces an openable .xlsx at
OUTPUT_PATH ends the Actor execution. Opening a workbook is not a correctness
check. A missing target sheet or an incorrect answer discovered by grading
cannot reopen the Actor. Exhausting code attempts or the Actor time budget
without a valid submission is a task failure. API or execution-infrastructure
interruptions and scoring failures are recorded separately, not silently
converted into model failures or omitted from the batch. Complete history is
not silently shortened to fit a request.

Formula and scoring conditions
The formula policy is No additional formula recalculation; grading reads saved cell values with data_only=True.. In the initial profile,
there is no automatic formula recalculation; grading reads saved cell values
with data_only=True. Writing a valid formula does not establish that a cached
result exists. The Actor is told this execution condition.

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
You are a Python programmer performing the spreadsheet task supplied by the user.
Return one complete, self-contained Python script inside a single ```python```
fenced block, with no surrounding explanation. Read the original .xlsx workbook
through INPUT_PATH and save the result to OUTPUT_PATH. These variables are bound
by the executor; do not hardcode paths, rebind them, or request interactive input.
Use only the Python standard library, openpyxl and pandas.

You have no interactive shell, file browser, Python session, workbook inspection
tool or grader tool. The external executor runs your script. The program can read
the complete original input and write in its current output/temporary directory;
it cannot access reference answers, other tasks, prior attempts' files, the network
or external command execution. Do not print output for an extra exploration turn.

The preview is limited to the first 5 rows and
20 columns of each worksheet. Each displayed cell is limited to
40 characters. Unshown data may still exist in the file.
You retain the complete messages within this task, but each execution starts in
a fresh directory with the original input. Return a complete replacement script
after an error; no variables or files from previous attempts persist.

There are at most 30 code attempts, including malformed or
truncated responses. Each response allows at most 16384
tokens. The task has a total Actor time budget of 600
seconds, including preparation, requests, retry waiting, execution and output
checks. A program runs for at most 600 seconds and no
longer than the remaining task time. Exhausting either budget ends the attempt
to solve this task; unused code rounds do not guarantee additional time.

Only response-format, program-execution, and missing or unreadable output-file
errors can be returned for correction, subject to the remaining budget. The first
normally terminated program producing an openable .xlsx at OUTPUT_PATH is the
final submission. You cannot continue after that submission. Correctness is scored
afterward; no scores, wrong-cell coordinates, expected values, or grading-based
correction requests will be returned to you.

No additional formula recalculation is performed. Grading reads the output
workbook's saved cell values with data_only=True. For formula cells, this reads
saved cached results; writing a formula does not compute its cached result.

The Skill below supplies task-solving guidance within these execution conditions.
Its references to exploring, executing, and checking refer to the generated program
and external executor, not extra tools or access to reference answers. The fixed
execution conditions above remain in force throughout the task.

## Skill

[runtime field: skill]

</actor_system_prompt>
<actor_initial_template>
# Task instruction
[runtime field: instruction]

# Task type
[runtime field: instruction_type]

# Answer region
[runtime field: answer_region]

# Input workbook preview
[runtime field: workbook_preview]

# Code budget
max_code_attempts=30
code_attempts_used=0
code_attempts_remaining=30

Return the complete Python script in one python fenced block. The executor supplies
INPUT_PATH and OUTPUT_PATH. Use the original input and save the result to OUTPUT_PATH.

</actor_initial_template>
<actor_runtime_feedback_template>
# Runtime feedback
category: [runtime field: error_category]
exit_status: [runtime field: exit_status]

[runtime field: error_detail_prefix]

detail_truncated: [runtime field: detail_truncated]
code_attempts_used: [runtime field: code_attempts_used]
code_attempts_remaining: [runtime field: code_attempts_remaining]

Correct the reported format, execution or output-file error and return one complete
Python script in a single python fenced block. The next execution starts from the
original input in a fresh directory, without any previous attempt's files or state.
This message contains runtime information, not a correctness evaluation.

</actor_runtime_feedback_template>

These templates describe what can be sent. The saved messages for a specific
execution determine what was actually sent. A post-execution record does not
become Actor-visible merely because an optimization module can read it.
