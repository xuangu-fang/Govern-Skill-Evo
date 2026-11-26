# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question: do not restate label text the question already names (e.g. drop a leading "Question 1."), and do not append an adjacent field such as an affiliation or company that is separate from the one asked for.
- When several candidate strings, dates, or taglines on the page look similar, do not default to the most prominent or first one; choose the candidate anchored to the exact entity, heading, or qualifier the question names (e.g. if the question ties a date or tagline to a specific named person, award, or section, read the span next to that name), and re-scan for other candidates of the same type before finalizing.
- In tables and forms, resolve the row by its explicit identifier (serial number, name, date, region) and the column by its header, then read the cell where that row and column actually intersect; re-check the identifier before answering, since adjacent rows often hold similar-looking values. For "most"/"fewest"/"highest"/"lowest" questions, first compare every row in the queried column to find the extremum, then read the label from that same row rather than from a nearby one. When the answer is itself a row label and the question pins it down by attributes spread across several columns (e.g. a region and a year that must both be satisfied), find the single row where every stated attribute holds and answer with that row's label, not a similar-looking label from a neighboring row.
- For short identifiers, figure/table numbers, and numeric fields, read the characters one at a time instead of inferring a plausible-looking value; when a glyph could be either a digit or a letter (`1` vs `I`, `0` vs `O`) or two digits look alike, choose the reading consistent with how the same field or list is numbered elsewhere on the page.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- For numeric answers, give the number plus only the units, currency, or percent symbols printed in that cell itself; drop the counted noun ("how many ...") and any unit or symbol that appears only in the question wording or a column header, and keep the printed form (a spelled-out word stays a word, a numeral stays a numeral).
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- Preserve interior punctuation and spacing as printed (including any space before parentheses), but render typographic curly quotation marks as plain straight quotes.
