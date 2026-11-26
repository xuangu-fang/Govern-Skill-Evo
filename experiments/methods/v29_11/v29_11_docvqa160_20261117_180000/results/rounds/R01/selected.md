# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Treat the answer as the requested value, not as surrounding form text. When the question names the field, return the value without prefixing its label or appending a numeric/word equivalent, conversion, or explanatory gloss.
- If the document shows two parallel renderings of the same value, return the primary entry for the field; if one entry visibly contains both renderings, return only the rendering that answers the question's form and omit the redundant other.
- Keep genuinely requested multi-part content together, such as a full official name with its short form in parentheses or a list the question explicitly asks for.
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
