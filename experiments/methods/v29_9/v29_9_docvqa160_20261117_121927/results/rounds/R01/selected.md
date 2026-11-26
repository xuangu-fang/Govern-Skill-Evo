# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- When the requested value appears in more than one equivalent representation in the same answer area, return only the single representation that directly answers the question; do not append a parenthetical, numeric, or otherwise secondary restatement merely for completeness.
- If the question explicitly asks for a particular form, use that form; otherwise use the primary full value printed in the relevant answer field and keep any unit belonging to that single form. Preserve punctuation integral to the value itself, such as parentheses within a phone number; avoid duplicate equivalent representations without removing meaningful characters.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
