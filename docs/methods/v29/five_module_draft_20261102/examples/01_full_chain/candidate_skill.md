# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.
- For an amount question, distinguish the requested role (such as subtotal, total, or balance due) before selecting a value; prefer a value explicitly labeled for that role when present.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
