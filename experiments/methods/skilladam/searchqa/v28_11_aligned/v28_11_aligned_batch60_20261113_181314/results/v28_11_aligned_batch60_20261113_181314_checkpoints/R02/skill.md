# Question Answering Skill

## Workflow

1. **Parse what the clue asks for.** Jeopardy-style clues name the answer's kind via "this/these X" (X tells you whether to answer a person, city, term, title, type of business, etc.). Many clues also build a familiar phrase or pun ("a letter to ___", "Bridge to ___", "King of the ___"); when so, supply the plain missing word(s), not a related proper noun named in the clue.
2. **Find the one passage that satisfies all constraints** (dates, quantities, roles, "first/last", relationships). The intended answer normally appears there verbatim or as a close paraphrase. If several passages seem relevant, prefer the one matching the most constraints.
3. **Extract the concise answer.** Take the shortest noun phrase or proper name from that passage that denotes exactly the requested thing. When the clue asks for "the term for ...", give the generic term itself rather than a specific named instance of it.
4. **Check before answering:** the candidate must (a) satisfy every constraint and (b) be the kind the clue asked for — the character rather than the actor, the type of business rather than the organization, the term rather than the named event. If not, revisit the passage.

## Answer Format

- Output only the bare term or name.
- Person: give first name + last name (retain a common middle initial); do not reduce to just a surname, and do not add ranks or titles.
- Do not wrap the answer in explanatory prose ("usually called ...", "the three main ...", a full sentence).
- Do not offer alternatives ("X or Y", "sometimes X").
- Keep the grammatical number used by the passage's primary statement (singular vs plural).
