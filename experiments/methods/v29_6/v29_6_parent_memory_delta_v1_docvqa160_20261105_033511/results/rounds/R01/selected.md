# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When the question asks for a single scalar or identifier (an amount, number, date, name, or code), return one minimal contiguous span that directly answers it. If the document shows the same value in more than one notation, such as a spelled-out amount followed by a numeric or symbolic restatement, do not concatenate the representations or append a parenthetical equivalent; keep the form that occupies the requested label/value position. Preserve exact units and printed punctuation that belong to the selected span. This rule limits redundant equivalent renderings, not legitimate parenthetical components of a proper name.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
