# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.

- For attribute questions (title, designation, position, role, rank, occupation), return only the attribute value itself and stop before any trailing affiliation, company, department, or organization name that follows it.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

- Distinguish digits from look-alike letters in short identifiers (diagram/figure/table numbers): read '1' as the digit one, and treat 'I' or 'l' as a letter/roman numeral only when the context clearly calls for it.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.

- Do not echo the question's own label or numbering in the answer (e.g., 'Question 1.', 'Figure 3'); return only the content that follows the label.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.

## Structured Lookup and Exact Span Selection
- Directional/layout prompts: for 'top right corner', 'underlined text', 'last rectangle', 'at the top', etc., locate the named region, element, or marker first, then copy only the text it contains or marks; do not echo the location or style phrase.
- Tables: identify the row by the requested label/date/identifier and the column by the requested heading, then return only the intersecting cell value; for relational questions, anchor on the named entry and move to the specified neighboring row.
- Ordinal tables/headings/lists: when the question names an ordinal (e.g., 'the sixth entry', 'the third heading'), scan in visual reading order, count the actual items, and copy the full requested entry/heading exactly.
- Forms: locate the exact requested field label first, then copy the value aligned on the same line or adjacent entry space; if the requested field itself holds multiple names or entries, copy the entire field in original order rather than truncating to the first item, but do not append a separate trailing affiliation, company, department, or organization name.
- Preserve formatting that is part of the source value: capitalization, commas, percent signs, parentheses, hyphens, currency symbols and decimals, alphanumeric codes, initials, titles/suffixes, and visible conjunctions.
- Quoted-phrase/requirement questions: find the exact quoted phrase and return the adjacent condition, clause, or value, not the quoted phrase itself unless it is the requested answer.
- Document-type/title questions: copy the prominent heading or title exactly as printed, preserving capitalization, punctuation, and spacing; if a separate affiliation/company/department follows, stop at the title value. For company/organization questions, copy the company name exactly as printed.
- Page numbers, IDs, and counts: return bare values (e.g., '2'), omitting surrounding labels like 'Page'; include a unit only when it is printed in the same cell/value.
