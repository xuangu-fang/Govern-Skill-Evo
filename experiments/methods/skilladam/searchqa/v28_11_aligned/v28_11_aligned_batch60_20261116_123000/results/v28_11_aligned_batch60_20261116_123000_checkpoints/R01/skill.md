# Question Answering Skill

## Workflow

1. **Read the answer type off the question.** Pointer phrases ("this country", "these animals", "this type of chewing gum", "this adjective") state what kind of thing is wanted. The answer must be a specific instance of that type.
2. **Locate the best supporting passage.** Prefer the passage sharing the most distinctive details with the question (dates, numbers, titles, proper names). Drop passages that overlap only on a generic word.
3. **Extract, then narrow.** When a passage lists several candidates, take the one stated first or without hedging; when the question asks for "this type of X", name the specific type instead of repeating "X".
4. **Fill only the slot the question left open.** If the question already supplies part of the answer ("these Chinese ___", "this ___ author"), answer with the missing element alone and do not echo the supplied words.
5. **Emit the shortest canonical form.** A name, title, term, or bare noun phrase — no definition, no parenthetical expansion, no trailing qualifier, no generic filler the question already implies.
6. **Re-read the question against the answer.** The answer should complete the clue's sentences and satisfy exactly what was asked. If it contains the question's own wording, or is a longer paraphrase of a shorter name, shorten it.

## Answer Form Rules

- **Answer the named thing, not its description or category.** Answer "France", not "the country named in the 1918 treaty"; never answer "capital cities" when the clue itself lists capital cities.
- **Answer the primary item, not the full list.** From "catgut makers usually use sheep or goat intestines, but occasionally cattle, hogs, horses", answer "sheep" — not the enumeration.
- **No padding.** No parenthetical expansions or definitions ("LPGA", not "LPGA (Ladies Professional Golf Association)"); no generic filler the clue already implies ("hydroelectric", not "hydroelectric power"; "laundries", not "Chinese laundries" when the clue says "these Chinese businesses").
- **Character or title beats performer.** When a clue plays on the words of work titles ("in '84 he's a destroyer, in '82 he was just a barbarian" = Conan the Destroyer / Conan the Barbarian), answer the character or the title, not the actor.
