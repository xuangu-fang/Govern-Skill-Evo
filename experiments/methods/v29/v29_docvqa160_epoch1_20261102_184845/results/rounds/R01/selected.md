# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.
- For questions that identify a record by an exact label or number and ask for another field from that record (for example, a building number and its location code), confirm that the final value is associated with the row whose identifier matches every stated qualifier; if two nearby rows or codes are plausible, reject the value whose row identifier or requested column does not match the question, rather than substituting a nearby code.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- After selecting the answer span, perform a final exactness check before writing the final answer: return only the characters of that span, and do not append units, labels, separators, or quotation marks that are not visibly part of the span; in particular, do not add a unit merely because the question mentions it elsewhere, do not insert a comma or space between adjacent components unless the selected span prints it, and do not substitute different quotation-mark characters for the ones shown in the span.
