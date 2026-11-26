# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that contains the complete requested value, keeping the document's own wording, units, currency, and qualifiers. Do not shorten a written amount, name, or label into a symbol, abbreviation, or acronym when that changes the entry or drops required content.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Table and Labeled-Layout Lookup
- For questions about a table, list, or labeled layout that identify a row or record by an explicit label (such as a numbered building, a study phase or year, a named person, or a numbered sector), first locate the entry whose identifier matches the question, then return only the value in the column or attribute the question names.
- Do not take a value from a nearby row, a similarly numbered record, or an adjacent column. When labels and cells are visually close, answer from the intersection of the matching row label and the requested column heading.
- Keep the selected value in its original format and units. Apply this row-and-column procedure only when the question and the visible layout present such a structure.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- When the question requests a single value (such as an amount, name, count, date, identifier, or code), return exactly one answer unit inside the answer element. Do not append a second equivalent representation, a spelled-out duplicate, a currency conversion, or a parenthetical alternative unless the question itself asks for multiple values or forms.
- If the same requested value appears in more than one notation, answer with the single form in the field, line, or entry tied to the question's named entity or attribute, and do not merge two forms into one answer.
- Use explanatory parentheses only when they belong to the requested printed label or are needed to keep a qualifier; do not add an explanatory parenthetical of your own. Parentheses that are part of the printed value itself, such as those in a phone or fax number, must be copied as printed. If a requested name itself carries a parenthetical acronym or qualifier, copy it as one continuous literal string with the printed spacing and quotation marks, without inserting a space before the parenthesis or substituting a different quotation style.
