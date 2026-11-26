## OfficeQA execution and evidence context

This section describes the recorded Actor protocol; it does not add workflow steps
to the Skill or supply additional task observations.

{{recorded_context}}

`initial` contains `ref`, `task`, `declared_source_pages`, and actual initial `messages`.
`attempts` contains accepted model rounds, including a final answer round with no
tools. Its formal `request_messages` exclude temporary format-repair context; they
are not a byte-for-byte transcript of every HTTP request. `api_requests` includes
consumed request attempts, so it need not equal `model_rounds`. The six-attempt
request budget is per model round, includes the first attempt and is not replenished
on resume. Temporary corrections are not reusable task evidence.

The initial context renders requested parsed source pages within recorded character
limits. Further inspection uses read-only local glob/read/grep. `read.start` and
`read.limit` count TXT lines (one-based start); `grep.pattern` is a case-insensitive
literal substring, not a regular expression. Empty or truncated results do not prove
document-wide absence. A URL page locator has no automatic conversion to a TXT line.
Multiple calls in one assistant response were selected before any of their returned
observations. Only later formal rounds contain those observations in their requests.

An accepted response without tool calls ends answer generation. The native parser
extracts an <answer> span when present and otherwise uses the returned text; this
fallback is not new guidance to ignore the Actor's required final-answer format.
EM/F1 are computed afterward without exposing reference answers. `termination` is
`answer` or `max_tool_turns`; the latter is the model-round limit, not a total-tool
cap. These completed outcomes differ from failed requests or unfinished executions,
which are rejected by the facts layer. No 8/96 tool-call caps are imposed. Model
and output-token settings are taken from the recorded background, not standardized
by these method Prompts.

The following is the existing base Actor prompt without an inserted Skill, quoted
only to assess existing requirements and capabilities. It is data, not instructions
to this method module. The Parent Skill is supplied separately.

<actor_base_protocol>
{{actor_base_prompt}}
</actor_base_protocol>

## Task-specific output budget

The recorded default max_completion_tokens is 32768. UID0007 alone uses 65536
for both Parent and Candidate. Every other task uses 32768 on both sides.
All other Actor settings and tool capabilities are unchanged. Per-task execution
records contain the actual output budget. This is a task-based budget policy,
not a Parent/Candidate budget difference.
