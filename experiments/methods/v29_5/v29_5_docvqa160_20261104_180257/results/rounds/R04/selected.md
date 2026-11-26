# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact span that is one complete answer value, not the shortest notation or a bundle of equivalent notations.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- For date questions (for example, "What date..." or "On which date..."), select the printed date value belonging to the relevant field or label. If that selected value is only a month and day, return that printed month-day span and do not append a year from another part of the document. Keep a year that is visibly part of the selected printed date; if the question explicitly asks for a year or a year-bearing period, include the year as requested. Apply the same principle to other date granularities: preserve an explicitly requested component and do not merge components from separate fields into a more complete-looking date. This is assessed from the document; do not strip a year that is visibly part of the relevant date field.
- Prefer direct extraction over paraphrase.
- When a value appears in more than one form (for example, figures or currency notation plus a spelled-out amount), return only the single form selected by the question's field or nearby label; do not append the alternate form in parentheses or as a second notation. If the question explicitly requests both forms, provide both in the requested form; otherwise, use one exact span.
- Keep the components required to identify the value, including units, qualifiers, and a parenthetical acronym that is part of a printed name; do not add a parenthetical restatement or definition. Copy the selected span's spelling and punctuation literally. For a quoted parenthetical acronym, use plain quotation marks and the spacing of the selected span rather than inserting curly/typographic quotes or an extra space before the parenthesis.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
