# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.
- For questions that identify a record by an exact label or number and ask for another field from that record (for example, a building number and its location code), confirm that the final value is associated with the row whose identifier matches every stated qualifier; if two nearby rows or codes are plausible, reject the value whose row identifier or requested column does not match the question, rather than substituting a nearby code.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- When the answer is a standalone label, heading, or table-cell value, return that value as a self-contained span: do not add a leading article or other grammatical scaffolding unless it is visibly printed as part of the label, and preserve any article that is visibly part of the requested label.
- When the answer is a short alphabetic label or heading, read its letters in order and verify that exact sequence against the visible text before finalizing; do not transpose adjacent letters or substitute a visually similar letter, and return the printed spelling rather than replacing a visibly printed string with a more familiar word or a corrected spelling.
- When the requested answer is an identifier-like code or multi-digit number, perform a final character-by-character comparison of the candidate against the visible source, checking each digit in sequence and rechecking visually similar characters; do not substitute a plausible but different digit or digit sequence.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- After selecting the answer span, perform a final exactness check before writing the final answer: return only the characters of that span, and do not append units, labels, separators, or quotation marks that are not visibly part of the span; in particular, do not add a unit merely because the question mentions it elsewhere, do not insert a comma or space between adjacent components unless the selected span prints it, and do not substitute different quotation-mark characters for the ones shown in the span.
