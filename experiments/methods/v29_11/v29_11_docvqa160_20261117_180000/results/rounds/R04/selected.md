# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Treat the answer as the requested value, not as surrounding form text. When the question names the field, return the value without prefixing its label or appending a numeric/word equivalent, conversion, or explanatory gloss.
- For questions that ask for a count or cardinality (wording such as how many ...), return the count alone: the number or number word as printed, without repeating the counted object or category named in the question. Do not include the counted noun merely because a nearby document phrase contains the count and the noun together. This count-only rule does not apply when the question asks for a measured value whose unit conventionally belongs to the answer: retain that unit or time designation. Multiword names and explicitly requested lists remain subject to the existing multi-part-content rule.
- If the document shows two parallel renderings of the same value, return the primary entry for the field; if one entry visibly contains both renderings, return only the rendering that answers the question's form and omit the redundant other.
- Keep genuinely requested multi-part content together, such as a full official name with its short form in parentheses or a list the question explicitly asks for.
- For a tagline, slogan, title, or other quoted phrase, keep the complete wording together and include its enclosing quotation marks when they are visible, but render those delimiters as ordinary straight double quotation marks rather than curly or typographic variants. Do not add quotation marks when none are visible, do not substitute a shorter paraphrase, and do not add a label or explanation around the phrase. This convention applies to quotation marks that delimit the requested text, not when exact typography is itself the requested information.
- Copy names, numbers, and dates exactly from the document whenever possible.
- Prefer direct extraction over paraphrase.
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span.
