# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When the question asks for a single scalar or identifier (an amount, number, date, name, or code), return one minimal contiguous span that directly answers it. If the document shows the same value in more than one notation, such as a spelled-out amount followed by a numeric or symbolic restatement, do not concatenate the representations or append a parenthetical equivalent; keep the form that occupies the requested label/value position. Preserve exact units and printed punctuation that belong to the selected span. This rule limits redundant equivalent renderings, not legitimate parenthetical components of a proper name.
- For a label-like number or code (abstract number, page number, item/entry number, account digits) rather than a measured quantity, inspect what sits immediately before the digits. If a hyphen, dash, bullet, or dot leader separates the digits from a name or label in the surrounding layout, answer with the digits alone without that separator and do not treat it as a minus sign, range marker, or subtraction. If the same digits appear both separated and unseparated, prefer the rendering that occupies the requested field's value position.
- Keep a leading sign only when visible context marks the value as genuinely signed (a loss or deficit, temperature, offset, coordinate, or a field label indicating a negative value), and keep the sign attached to the digits. Retain punctuation that belongs to the field rather than the layout, such as units with their printed period, quotation marks around a slogan, a comma and suffix inside a personal name, and AM/PM markers. Confine this separator exclusion to a leading separator attached directly to identifier digits; do not strip other punctuation, trim trailing periods, or shorten names or multi-word answers.
- For a numeric value in a table cell, include a unit or symbol only when it is visibly printed with that value span. If the question or a column/row heading supplies the unit (for example, a percent sign in a heading) and the cell contains only the number, return the number without appending the heading/question unit; if the unit or symbol is attached to the value itself, keep it exactly. Treat this as a cell-boundary decision: do not strip symbols that are part of a name, currency figure, date, or other printed span, and do not append a unit merely because the question asks for that kind of quantity.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
