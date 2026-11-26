# DocVQA Skill

## Visual Evidence Discipline
- Read the document carefully before answering.
- Prefer the smallest exact text span that answers the question.
- When several nearby strings look similar, choose the one whose surrounding labels or layout best match the question.

## Exact Answer Discipline
- Copy names, numbers, and dates exactly as the document prints them, but write punctuation in its plain form: a hyphen for an en or em dash, a straight apostrophe for a curly one, and no added quotation marks around a span that the document does not print inside quotes. Typographic variants otherwise cause single-character mismatches.
- Prefer direct extraction over paraphrase: give the value exactly as the document prints it. For "how many / how much" questions, give the printed count rather than restating the question's noun phrase. Do not prefix the answer with the label the question already names (no "label = value" form), and when the question itself specifies the unit, give the number alone if the document prints only the number. Keep any unit or symbol the document prints together with the value (a percent sign or currency symbol shown on the number).
- Before finalizing, compare the answer against nearby alternatives and keep the best-supported exact span. Confirm that the characters you are about to emit are actually printed on the page: an answer assembled out of the question's own words, or a plausible-sounding phrase you cannot point to in the image, is a guess — go back and find the document's printed wording instead.
