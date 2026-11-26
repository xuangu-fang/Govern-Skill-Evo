# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase: for "how many / how much" questions, give the count as printed in the document (keeping the unit when it is printed beside the number), rather than restating the noun phrase that the question itself supplies.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
