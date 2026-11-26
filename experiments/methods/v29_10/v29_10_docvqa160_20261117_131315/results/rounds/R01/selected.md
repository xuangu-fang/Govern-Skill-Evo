# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Return the smallest answer-bearing span that directly satisfies the requested field. Do not use minimality to truncate a proper name, title, list, or other field whose full printed span is the answer; preserve all components that identify the requested entity.
- For a quantity or count, if the question or field label already supplies the unit or counted category, answer with the value from the matching field or cell and do not append a repeated category word, a second unit, an unexplained equivalent representation, or an unrequested conversion. Keep a printed unit or equivalent when the question asks for the unit/currency, or when it is inseparable from the value and not already supplied.
- Before finalizing, re-read the chosen span and remove only additions that are not part of that span.
- When the question asks for a value tied to a label, identifier, row, or column, first locate the exact label or identifier, then read the value that shares the same row/line or adjacent cell. Verify that the requested label and selected value are visibly paired, and do not substitute closely related labels or adjacent numbered rows for one another.
- If two candidate values are near, choose the one whose row/column alignment and label match the question, not simply the nearest-looking string; do not answer with a value from a different field merely because it appears in the same block.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
