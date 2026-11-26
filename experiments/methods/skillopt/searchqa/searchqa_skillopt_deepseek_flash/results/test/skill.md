# Question Answering Skill

## Answer Span and Form
- Answer with the shortest span that directly satisfies the question. Do not append category labels, explanatory phrases, roles, or other qualifiers; do not turn a group name into a tribute-band label or repeat a category noun already present in the question.
- If the question supplies the category or descriptive frame ('this vitamin', 'this Romanov', 'this rock group', 'this French ...'), answer only the specific name/letter/token and omit the repeated category or extra name part.
- For person names, use the shortest unambiguous form demanded by the clue. Do not add first names, surnames, titles, or role labels merely because they are available; add a name part only when needed to identify the person or when the question explicitly asks for the full name.
- Preserve the exact word form used by the supporting answer when it is grammatical: adjective vs. noun/demonym, singular vs. plural, abbreviation vs. expanded phrase. Do not normalize to a different form after finding the right concept.

- For definitional, glossary, flashcard, dictionary, list, or fill-in-the-blank clues, match the definition or slot text and answer the single headword/common word that fills it (e.g., 'cry of a sheep or goat' -> bleat; 'hasty ___ ... tapioca ___' -> pudding). Do not substitute a synonym, the quoted adjective, the definition words, or the full collocation; a near-verbatim or all-caps restatement of the clue often signals the adjacent term.
- Prefer an exact contiguous span from the context over a constructed description.

## Exact Clue Binding and Distractor Rejection
- Identify the exact subject-predicate relation in the question before answering (who/what is named for, higher in, played, wrote, etc.). The answer must satisfy the whole relation, not merely share a name or keyword with the clue.
- Do not choose an entity just because it appears in a prominent document or near the clue. Check that the supporting sentence talks about the question's subject and the requested relation.
- For quoted, truncated, or title-fragment clues, complete or match the exact phrase/title from the context; do not substitute another high-salience document that shares a keyword.
- When multiple candidates are plausible, prefer the one supported by the sentence that most precisely matches all question constraints. For counterpart or equivalence clues (Greek vs. Roman, X's counterpart, 'known to the Y as'), answer the entity on the side the question names and reject the analogous entity from the other side even if it is more prominent. For clues with several numeric or career anchors (tenure length, hit total, record, team), require a single candidate whose supporting text contains them together; do not let a more prominent adjacent name capture the answer.

## Core Strategy and Evidence Selection

- Normalize noisy question formatting before matching: ignore stray ampersands, HTML entities, duplicated trailing fragments, and other OCR artifacts, then answer the clean core clue. If the question lists alternatives ("Of A, B, C, or D ..."), evaluate each named option and return only the one listed option that satisfies the full clue.
- Treat the question as a clue/trivia item over multiple [DOC] passages: it paraphrases one passage, and the answer is a named entity or short phrase stated there.
- Infer the expected answer type from the wording (person, place, title, work, term, publication, quantity, etc.) and answer that entity rather than restating the clue. For possessive/attribution clues (e.g., "his 1882 drama", "this newspaper's crossword editor"), resolve the relation to the missing entity.
- Extract distinctive anchors — proper names, dates, numbers, quoted or unique phrases, titles, roles — and scan passage titles and snippets for the one that contains the most or all of them. Commit to the best-matching passage; do not average over irrelevant decoys.
- If the context includes a Jeopardy-style archive, flashcard, or Q/A document formatted as "descriptive clue | Answer" or "Q: ... A: ...", use the exact matching pair as a high-confidence shortcut, then cross-check against another passage when possible. Extract only the clean answer token after the final "|" or after "A:", ignoring trailing annotations and commentary such as "right:", "Wrong:", scorer names, host/contestant chatter, and explanatory notes. If the archive snippet omits the answer, use other passages to complete the same clue; when a lone forum/comment snippet conflicts, trust the explicit paired answer and independent repetition over that single opinion.
- Scan all provided passages for direct mentions of the requested entity; do not rely on a single passage when several are available. Treat titles and headings as high-value evidence: they may contain the answer or key clue terms.
- Use repetition and agreement across independent passages as a strong confidence signal. When passages repeat the same fact with minor spelling, formatting, or OCR differences, treat the consistent entity as the answer rather than being distracted by the variations.
- Ignore passages that match only broad topic words or incidental keywords; web-style contexts include many distractors.
- Emit only the concise answer inside `<answer>...</answer>`: no sentence, no restatement of the clue, no parenthetical explanation, no reasoning. For translation clues, give only the translated phrase or title.

## Verification Before Answering
- Before finalizing, re-read the chosen passage to confirm that every clue element (place, date, role, work title, etc.) is satisfied and that the candidate's type matches the clue.
- Prefer the candidate supported by all clue constraints and by the most independent mentions; if several candidates fit partially, discard the weaker ones.
