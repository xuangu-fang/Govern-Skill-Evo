# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.
- In tables and forms, resolve the row by its explicit identifier (serial number, name, date, region) and the column by its header, then read the cell where that row and column actually intersect; re-check the identifier before answering, since adjacent rows often hold similar-looking values.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- For count questions ("how many ..."), answer with the quantity alone: drop the counted noun and any unit not printed in the cell, and keep the printed form (a spelled-out word stays a word, a numeral stays a numeral).
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- Preserve interior punctuation and spacing as printed (including any space before parentheses), but render typographic curly quotation marks as plain straight quotes.
