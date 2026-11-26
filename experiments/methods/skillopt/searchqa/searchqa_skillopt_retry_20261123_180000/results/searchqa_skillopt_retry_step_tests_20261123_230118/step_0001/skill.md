# Question Answering Skill

## Answer Span and Form
- Determine the expected answer type before extracting. Return the shortest span that uniquely answers the clue, not an explanatory phrase or expanded noun phrase.
- Omit category labels, role descriptions, and unnecessary name expansions. If the clue already supplies the category, give only the specific member; if the source gives a concise answer form (a surname, single name, letter, or group name), use that form rather than adding surrounding words.
- Match the grammatical form requested by the clue. For nationality, language, or adjective answers, return the adjective rather than the country/place noun; for names, use the form the clue expects rather than automatically expanding to a fuller name.

## Clue Interpretation
- If the question is a declarative statement with a pronoun such as 'his', 'her', or 'this', answer the entity the pronoun refers to; do not answer True/False or merely restate the statement.
- If the question is a quoted fragment, ellipsis, or fill-in-the-blank, complete the known title or phrase. Match the full phrase/title implied by the clue rather than a document whose title only contains the visible words.

## Exact Relation Verification
- For relational clues (e.g., 'named for', 'written by', 'located in'), locate the passage where the exact relation is stated between the queried subject and the answer. Do not choose a nearby name that merely co-occurs in the same document or belongs to a different relation.
- When several names appear, prefer the one explicitly linked to the queried object and descriptor; if a passage mentions a name in another construction, treat it as a distractor.

## Context Reading and Disambiguation
- Treat the question as a Jeopardy-style clue: identify the single entity or phrase that satisfies all constraints in the clue (date, role, work, title, location, distinguishing descriptors), not just one.
- Use document titles (`[TLE] ...`) as a fast candidate list; the answer often appears as the subject of a relevant title or clearly in the passage best matching the clue.
- Pull distinctive/rare terms from the question (proper names, quoted phrases, numbers/years, unusual nouns) and choose the passage where several appear together. Ignore navigation, sidebars, related-idea lists, boilerplate, and unrelated archives; a passage matching every constraint beats many passages sharing only generic topic words.
- Prefer explicit, direct statements that name the answer. If the same fact is repeated across independent passages, treat that agreement as a strong confidence signal.
- Map question type to answer type: who = person, where = place, which/this X = the name of X.
- For 'this [country/play/movie/prison/work/etc.]' clues, return the entity being described and do not return a related nearby entity.
- When a clue combines two facts (e.g., 'emit vapor' AND 'show irritation'), choose the single term whose definition covers both senses rather than combining separate candidates.
- For translation or parenthetical-title clues, return the translated phrase/title itself (e.g., `My Crazy Life`), not the original-language phrase, a full sentence, or extra explanation.
- Canonical form details: preserve the spelling/capitalization used in reliable context; keep a leading article only when it is conventionally part of the proper name/title (e.g., `The New York Times`), otherwise omit it; preserve parentheticals or other name elements only when they are part of the established name (e.g., `(Lou) Gehrig`, `Lord Robert Baden-Powell`); prefer exact wording found in the supporting context over paraphrases.
