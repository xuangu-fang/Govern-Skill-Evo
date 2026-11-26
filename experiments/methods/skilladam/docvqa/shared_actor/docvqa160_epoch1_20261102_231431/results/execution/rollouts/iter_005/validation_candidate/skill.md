# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase: give the value exactly as the document prints it. For "how many / how much" questions, give the printed count rather than restating the question's noun phrase. Do not prefix the answer with the label the question already names (no "label = value" form), and when the question itself specifies the unit, give the number alone if the document prints only the number. Keep any unit or symbol the document prints together with the value (a percent sign or currency symbol shown on the number).
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
