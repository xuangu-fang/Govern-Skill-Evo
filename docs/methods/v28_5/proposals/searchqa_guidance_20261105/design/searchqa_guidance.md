## SearchQA domain guidance

Use the following distinctions to interpret the evidence supplied to this module. They are analytical vocabulary, not new output fields, a per-task classification report, or proof of an internal cause. Use the relevant terms in reason when helpful; retain uncertainty when the observations do not distinguish explanations. The vocabulary does not expand this module's role or evidence access.

### Failure patterns

- **rule_missing**: No relevant guidance covers the observed decision problem. Consider a scoped addition for the transferable gap, not a rule that reproduces one reference answer.
- **rule_wrong**: Existing guidance directs behavior inconsistent with the task. Consider revising or removing the misleading requirement rather than adding a competing rule. Distinguish an observable conflict from proof that the Actor followed it.
- **rule_ignored**: Relevant guidance exists, but the visible response does not satisfy it. Consider making its trigger or action concrete instead of adding an equivalent rule. A short answer alone does not establish which internal instruction was followed or why it was missed.
- **answer_format**: The evidence supports the same underlying entity or fact, but the submitted answer form differs: unnecessary expansion, singular/plural, common versus full name, spelling, diacritics, abbreviation, punctuation or tokenization. Check the actual normalization before treating a surface difference as a scoring difference; capitalization and many punctuation differences are already ignored. Do not infer a wrong entity solely from EM=0.
- **other**: Ambiguous evidence, capability limits, possible sampling variability or reference/scoring limitations may leave no supported Skill correction. Do not force a rule or declare noise merely because the cause is unclear.

### Successful patterns worth preserving or transferring

- **applied_rule**: Visible behavior is consistent with relevant guidance. Preserve the useful behavior; do not infer internal rule use from success alone or duplicate an already adequate instruction.
- **disambiguation**: Resolve the requested answer type in a Jeopardy-style “this X” clue, subject/object or inverse relationships, the encompassing entity versus an example, or a historical versus current name. Transfer the decision relationship and its observable conditions, not the particular answer.
- **concise_normalization**: Select the conventional answer form supported by the question and context. Prefer the smallest sufficient answer unit; shorten only by removing genuinely redundant content. Preserve required name components, feature/company designators, units, ranges, meaningful spelling and grammatical number. Brevity does not authorize dropping information needed to identify the requested referent; neither a full name nor a shorter form is always preferable.
- **other**: A correct answer may reflect background knowledge, an answer stated directly in the passages or an uncertain choice. Success alone does not warrant a new rule; identify a transferable behavior before proposing one.

Prefer recurring decision patterns over collections of case-specific exceptions. Multiple supporting cases strengthen transfer, but a single clear case may still justify a scoped proposal under the existing method. Reference answers diagnose current discrepancies; they do not establish a universal naming preference. All applicability conditions must be available to the Actor from the question, context or its own response. Do not copy this vocabulary, scoring terms or illustrative answers into the deployed Skill as boilerplate.
