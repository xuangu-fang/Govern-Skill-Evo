# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- Return one answer value inside a single <answer>...</answer>. When the question asks for one field that the document prints more than once (a main figure plus a parenthetical or converted figure, or a note-style annotation beside it), answer with the one rendering attached to the label, row, heading or wording the question names, and omit the others: do not join two renderings of the same field, do not convert, and do not add explanations, derivations or comments after the value. If two renderings remain equally plausible, still return only one of them rather than a compound answer. This one-value rule concerns a single requested field: when the question itself asks for several items (a plural or list question, or several named items held in one field), give each requested item as printed, joined as the document prints them, and do not drop the extra items.
- Preserve as printed whatever punctuation, spacing, parentheses or suffixes belong to the chosen span: keep internal punctuation of names and identifiers, keep parentheses that are part of a printed number, and keep a multi-word name whole. Trimming means removing content around the answer, not editing characters inside it.
- Unit handling for quantity questions: when the question wording or the field label / column heading already names the unit or quantity type (weight, page number, count, percentage, rate), return the printed value from that cell alone — do not re-append the unit, spell it out in words, add a currency symbol, or convert to another unit. Add a unit only when the question supplies none and the selected span visibly prints the value and unit together, in which case keep them together exactly as printed. When the question already carries the unit, the printed numeric characters are the complete answer.
