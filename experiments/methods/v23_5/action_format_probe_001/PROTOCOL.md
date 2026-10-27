# Action format / reasoning boundary probe

Run at most 16 real requests, with no retries or environment execution. Preserve
DeepSeek model, thinking=enabled, reasoning_effort=medium, temperature=1,
max_tokens=16,384, and non-streaming transport from the historical Editor request.
Archive each actual request and raw HTTP response in a fresh artifact directory.

Three arms: original; replace only the initial Skill output-format sentence;
replace that sentence and both Actor runtime template format instructions.
The replacement describes an XML-style element named `action`, without an inline
tag example or a demand to emit reasoning in the response body.

Actor: historical R04 P1:49 and P2:8 inputs, two repetitions per arm (12 requests).
Assess finish reason, exact action-only output, and the existing parser's action
membership in the original admissible list. Do not execute any environment action.

Editor: historical R01 input, one request per arm (3 requests). Parent copies and
system protocol descriptions must agree with each arm. Keep the Effective Plan
unchanged; use existing strict JSON / patch validators against the copied Parent.
R04 aligned arm adds one stress request, keeping historical u3 unchanged: this
case still contains a literal think-tag requirement and is not a clean-start test.

Only modify production V23.5 after inspecting the raw-response boundaries and
validation results. A small sample cannot prove zero failure probability. Distinguish
token-budget truncation, suspected reasoning-boundary leakage, and ordinary patch
validation failures. Preserve old campaigns, baseline files and upstream SkillOpt.
