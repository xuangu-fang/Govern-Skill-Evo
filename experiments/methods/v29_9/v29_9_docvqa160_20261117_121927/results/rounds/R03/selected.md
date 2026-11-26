# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- When the requested value appears in more than one equivalent representation in the same answer area, return only the single representation that directly answers the question; do not append a parenthetical, numeric, or otherwise secondary restatement merely for completeness.
- If the question explicitly asks for a particular form, use that form; otherwise use the primary full value printed in the relevant answer field and keep any unit belonging to that single form. Preserve punctuation integral to the value itself, such as parentheses within a phone number; avoid duplicate equivalent representations without removing meaningful characters. For a count question, the count-span rule below takes precedence over the general full-value preference.
- For a count question ("how many ...") whose best candidate span contains both a quantity and the counted noun, return the quantity alone and omit the repeated object/category label when the document also prints that label nearby. Keep the printed count form (digit or word). Do not apply this to units or suffixes integral to the requested value (measurement unit, time-of-day marker, currency symbol, and similar); keep them. If the question asks for the full label or object name as part of the requested value, return the full requested span. Do not invent a count or drop an integral unit.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
- When the final answer is a phrase enclosed by quotation marks (for example, a tagline, slogan, or heading) and those marks merely enclose the phrase rather than belonging to the name or value, keep the phrase and render the enclosing marks as plain straight ASCII double quotation marks, using the same straight form for both opening and closing. Do not use curly or typographic quotation marks for these enclosing marks, and do not drop the enclosing marks in this situation.
- This is a character-level formatting rule for enclosing quotation marks only. Do not alter words, capitalization, or punctuation that is integral to the answer, such as a comma, period, hyphen, or an apostrophe inside a name or value; keep those exactly as printed.
