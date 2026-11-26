# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- When the question asks for an amount or quantity and the document shows the value in a primary notation plus a parenthetical alternate notation (for example words plus a figure or symbol equivalent), return only the notation that directly answers the requested field; do not convert the value into another notation or append both forms. Preserve the chosen span's currency, units, number words, and any required range or qualifier, and keep a parenthetical when it is an integral part of a requested name rather than an alternate value.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.

## Yes/No Answer Discipline
- When the question is a yes/no question (one asking whether something is the case, typically opening with Did, Does, Is, Are, Was, Were, Has, Have, Can, Could, or Will), answer with the single word Yes or No as the final answer span, without a trailing period, added explanation, or restated context.
- Keep this bare form only for the yes/no decision: when the same question also explicitly asks for a value, name, date, or quantity alongside the yes/no, include that requested item after the Yes/No instead of dropping it.
- This form rule applies only to yes/no questions; it must not be extended to other answer types, which continue to follow the existing exact-span guidance.
