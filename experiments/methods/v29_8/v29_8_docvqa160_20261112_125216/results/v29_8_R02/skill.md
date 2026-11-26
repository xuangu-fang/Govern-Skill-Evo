# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- For questions asking for a count (for example, "how many" or "number of"), return only the count token—the numeral or number word as printed—and omit the counted object or category. Do not append a noun phrase from a nearby caption, table header, or label when the count alone fully answers the question. Retain a unit or measurement qualifier when the question asks for a quantity or amount rather than the number of discrete objects, because dropping it would make the answer incomplete. Do not shorten other answer types; when a requested name, title, phrase, or measurement requires more than a count token, keep the span as long as needed to be exact.
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- When the requested answer is itself a quoted slogan, tagline, or title, return the enclosed words verbatim in ordinary straight double quotation marks, not curly or smart quotation marks; quote style is formatting, not content. Do not add quotation marks merely because the question quotes a field name or label. If the answer span is not itself quoted in the document, return the plain span without decorative quotation marks.
