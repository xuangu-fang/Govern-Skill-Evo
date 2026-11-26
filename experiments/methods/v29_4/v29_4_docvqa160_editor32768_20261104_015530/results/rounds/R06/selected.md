# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- For a question that asks for a person's title, role, position, or similar status, return the title/role designation as its own answer span and exclude an adjacent employer, organization, department, or other affiliation; include affiliation information only when the question asks for the organization, the full title, or the combined affiliation, and do not truncate rank words or qualifiers that visibly belong to the requested designation.
- For an address or venue-location question, return the span that the document places under the requested address label. If the document separates a street line from city/state/postal-code fields, do not concatenate those separate fields unless the question explicitly asks for the complete or mailing address. If the components are printed as one continuous address line, keep that full line. Preserve the printed punctuation and do not omit a component that the question specifically requests.
- When the question asks for an amount or quantity and the document shows the value in a primary notation plus a parenthetical alternate notation (for example words plus a figure or symbol equivalent), return only the notation that directly answers the requested field; do not convert the value into another notation or append both forms. Preserve the chosen span's currency, units, number words, and any required range or qualifier, and keep a parenthetical when it is an integral part of a requested name rather than an alternate value.
- Copy a unit, currency symbol, percent sign, or other notation only when it is visibly attached to the selected value in the document. When the question itself supplies the unit, such as "What %" or "How much", but the document cell or span contains only the number, return the number as printed instead of appending the question's unit. Do not strip a unit, currency marker, or qualifier that is visibly part of the selected span, and preserve the value's printed digits and separators.
- Prefer direct extraction over paraphrase.
- When the answer contains quotation marks around a term or a listed expression, keep those quotation marks as part of the selected span but render them as standard straight double quotation marks rather than curly or smart quotation marks, which are treated as different characters; apply the same convention to each quoted expression when the span contains more than one. Do not add quotation marks for emphasis and do not remove quotation marks that are part of the selected span. This concerns only the quotation characters of the selected expression and does not authorize adding a label, heading, or surrounding sentence outside it.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.

## Yes/No Answer Discipline
- When the question is a yes/no question (one asking whether something is the case, typically opening with Did, Does, Is, Are, Was, Were, Has, Have, Can, Could, or Will), answer with the single word Yes or No as the final answer span, without a trailing period, added explanation, or restated context.
- Keep this bare form only for the yes/no decision: when the same question also explicitly asks for a value, name, date, or quantity alongside the yes/no, include that requested item after the Yes/No instead of dropping it.
- This form rule applies only to yes/no questions; it must not be extended to other answer types, which continue to follow the existing exact-span guidance.
