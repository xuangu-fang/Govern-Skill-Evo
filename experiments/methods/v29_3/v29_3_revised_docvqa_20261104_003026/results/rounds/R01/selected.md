# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Before finalizing, identify what the question asks for: an amount, name, title, count, code, number, list, and so on. Return only that value, not the table/figure/column/row label used to locate it and not an unsolicited equivalence, conversion, alternative representation, explanation, or parenthetical note.
- Use identifiers in the question, such as a table number, building number, study number, or record label, to locate the answer. Do not repeat them in the final answer unless the question explicitly asks for the identifier or the identifier is itself part of the requested title/name.
- Preserve text that is genuinely part of the requested value: official names and embedded abbreviations, required units, necessary qualifiers, and all items when the question requests a plural or list answer.
- When the document presents both a container label and its content, or both a requested value and an adjacent converted/equivalent value, prefer the content/value alone. Apply the same scope discipline when a title, name, or amount is embedded in a larger heading or cell.
- When the question names a record/entity and a field, first identify the exact row or entity label and the exact column or field label the question asks for. Read the value at their intersection or beside the matching field label; cross-check that the candidate's adjacent label or header matches the question, not merely a similar nearby label.
- For contact information, distinguish exact field labels such as fax, telephone, toll-free, e-mail, and address, and return only the value attached to the requested label. Do not return a different number or code merely because it is nearby or has the same format.
- If two candidates look plausible, prefer the one whose exact row/entity and column/field labels match the question. If none matches exactly, return the best-supported single value rather than switching to a different field or listing alternatives.
- This procedure is especially applicable when the question includes a specific record identifier or when the page appears to contain several codes or numbers of the same format. It should not interfere with simple, directly stated single-value questions, and row/column narration must not be added to the final answer. Existing correct direct extractions remain unchanged.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
