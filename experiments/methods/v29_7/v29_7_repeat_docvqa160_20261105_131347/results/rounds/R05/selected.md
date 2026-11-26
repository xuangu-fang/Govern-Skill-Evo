# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- In page-number and similar identifier lookups, separate the field label from its value before answering. When the question names the field and the image shows a label plus a value, return the value-only span: do not prepend the field label and do not carry surrounding footer or header boilerplate into the answer. Keep the full printed phrase only when the value alone would not answer the question — when the question asks for the literal printed wording, or when a printed qualifier is part of the identifier the question refers to; in that case retain the qualifier. Do not use the label-plus-value phrase merely because the value is printed inside such a phrase.
- For where questions, return the place name or location phrase itself, not the sentence-level preposition or article that introduces it. Strip a leading connector such as "at" or "in" when it merely links the location to the surrounding sentence, but preserve prepositions and articles inside the official name. If the requested location is printed as a complete address or formal name, return that complete value without adding explanatory words or sentence grammar.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- When a numeric answer corresponds to a table cell, return the value as printed in that cell rather than appending a unit or symbol that appears only in the question or in the column heading. In particular, if a question asks for a percentage and the matched cell contains a bare number while the percent sign is only in the header or question wording, return the bare number; if the percent sign is visibly attached to the number in the cell, keep it. Apply the same check to currency and other units: retain a symbol or unit that is part of the extracted value or needed to identify it, but do not duplicate the question's unit into an otherwise bare value. Keep the numeric precision and separators exactly as printed.
- For date questions, determine the answer's granularity from the question and the queried label. If the question asks for a year, return the year alone. If it asks for a birth date or a full historical date, preserve the complete date value at that label. For a general date or deadline, return the date expression supported at that label; do not append a year or another component that appears only in a separate heading, neighboring line, or broader page context. Retain the year when it is integral to the same date string or needed to identify the requested date.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
