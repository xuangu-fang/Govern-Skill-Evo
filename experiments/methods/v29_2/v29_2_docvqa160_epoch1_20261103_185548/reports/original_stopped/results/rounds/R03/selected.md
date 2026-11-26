# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, use the surrounding labels or layout to identify the entry that best matches the question.
- For questions asking for a value tied to a named table column, list row, grid coordinate, or contact field, first match the exact identifier and field label from the question to the same row/entry and contact block, then read the requested value.
- If similar values are nearby, reject a value from an adjacent row, a different contact field (for example, telephone versus fax), or a secondary office or person block unless the question asks for that secondary entry.
- Return only the verified value, without an explanation.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Return one selected exact numeric or named span as the final answer, not multiple encodings of the same value.
- When the question already names the field or attribute it asks for (for example, a quantity of a named substance, an arrival or departure time, a designation, a nationality, or a state), return only that entry's value, ending at the value's edge. Do not repeat the field name, row label, column header, or the question's quoted substance, product, or attribute wording that located the entry, even if printed beside the value; treat such appended label text as extra answer content. Preserve the full requested value when its own components carry meaning: keep multiword names, name suffixes, printed parenthetical abbreviations, and other printed components belonging to the selected name; keep the printed unit or representation the question asks for; and keep quotation marks or punctuation only when they delimit the requested answer itself (for example, a quoted tagline). Apply these boundaries and the existing exact-copy, spacing, punctuation, unit, and no-alternate-encoding rules to the retained value only. Where existing guidance does not specify whether adjacent printed label text belongs to the answer, this scope rule governs.
- When a requested amount or name appears in more than one form, such as a symbol, written-out words, a currency conversion, or a parenthetical abbreviation, identify the field, cell, or entry that answers the question and return only the value exactly as printed there.
- Do not append restatements, conversions, or alternate forms from elsewhere unless the question explicitly asks for them. If the question asks for a specific representation or unit, use that representation from the document.
- Keep a parenthetical abbreviation only when it is printed as part of the selected name. Copy the chosen span's internal spacing and punctuation exactly as printed, including whether a space appears before a parenthetical abbreviation; do not insert or remove a space to match conventional prose.
- When multiple printed encodings exist, choose the answering entry's exact printed value as the selected span rather than treating every alternate encoding as a separate candidate.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
