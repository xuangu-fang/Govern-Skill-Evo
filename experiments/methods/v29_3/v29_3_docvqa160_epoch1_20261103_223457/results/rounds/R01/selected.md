# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question: one complete requested value, not a collection of equivalent representations. For an amount, measurement, date, or number, return the single directly stated span that answers it and keep only the unit or currency wording belonging to that span. Do not append a separate converted amount, alternate unit, restated numeral, or explanatory equivalence unless the question explicitly asks for multiple representations. Treat a visible clause marked as an equivalent or conversion (for example, 'equivalent to' or a second currency amount) as outside the requested answer unless the question asks for that equivalence. If several representations appear, select the one best supported by the question's wording and nearby label rather than concatenating them. Preserve terse numeric extraction when the question or document uses the number alone, and do not strip required identifiers or qualifiers that are part of the requested value.
- When the question identifies an element by a label, number, or caption marker (such as a table, figure, or section identifier) and asks for that element's title, name, or value, answer with the title, name, or value itself and exclude the retrieval label or caption prefix unless the question explicitly requests the label too. Do not treat an adjacent label as part of the answer merely because it is next to the requested content. Preserve the full requested title or name, including internal qualifiers that belong to it. Use the question's requested entity and the visible label/content structure to decide this boundary.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
