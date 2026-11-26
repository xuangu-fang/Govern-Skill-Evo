# Question Answering Skill

## Workflow

1. **Parse what the clue asks for.** Jeopardy-style clues name the answer's kind via "this/these X" (X tells you whether to answer a person, city, term, title, type of business, etc.). Many clues also build a familiar phrase or pun ("a letter to ___", "Bridge to ___", "King of the ___"); when so, supply the plain missing word(s), not a related proper noun named in the clue. If the clue is just one or more proper names with no other structure (no verb, question, or description), the answer is frequently the broader place those names belong to — e.g., their state or country — rather than a relationship word or a nearby named person.
2. **Find the one passage that satisfies all constraints** (dates, quantities, roles, "first/last", relationships). The intended answer normally appears there verbatim or as a close paraphrase. If several passages seem relevant, prefer the one matching the most constraints.
3. **Extract the concise answer.** Take the shortest noun phrase or proper name from that passage that denotes exactly the requested thing. When the clue asks for "the term for ...", give the generic term itself rather than a specific named instance of it.
4. **Check before answering:** the candidate must (a) satisfy every constraint and (b) be the kind the clue asked for — the character rather than the actor, the type of business rather than the organization, the term rather than the named event. If not, revisit the passage.

## Answer Format

- Output only the bare term or name.
- Do not repeat the class noun the clue uses to label the answer. When the clue already names the class ("this vitamin", "this market", 'this comic "network"', "this spice company", "the Progressive party ... nicknamed this"), give only the distinguishing name and drop that class word: "C" not "Vitamin C"; "trains" not "passenger trains"; "SCTV" not "SCTV Network"; "McCormick" not "McCormick & Company"; "Bull Moose" not "Bull Moose Party". A class word that sits inside a quoted title or a person's name is part of that name and stays.
- For a film/book/song title, give the primary (usually original-language) title; do not tack on a translated subtitle or alternate title: "Il Postino", not "Il Postino: The Postman". Keep every word that carries the title's own meaning ("All's Well That Ends Well", "The King and I", "High School Musical").
- Person: give first name + last name (retain a common middle initial); do not reduce to just a surname, and do not add ranks or titles.
- Do not wrap the answer in explanatory prose ("usually called ...", "the three main ...", a full sentence).
- Do not offer alternatives ("X or Y", "sometimes X").
- Keep the grammatical number used by the passage's primary statement (singular vs plural).
