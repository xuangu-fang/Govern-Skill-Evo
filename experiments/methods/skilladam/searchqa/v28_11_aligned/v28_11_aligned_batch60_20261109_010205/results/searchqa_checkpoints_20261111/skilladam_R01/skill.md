# Question Answering Skill

Answer Jeopardy-style questions using the supplied context passages.

## Workflow

1. Identify the grammatical slot the question asks for — the entity after "this" / "these" (e.g. "this U.S. territory", "these Chinese businesses", "this type of chewing gum"). Decide what kind of entity belongs there.
2. Search the context for the sentence that fills that slot. Prefer the passage that repeats the question's distinguishing details (dates, proper nouns, numbers).
3. Extract the answer exactly as the target entity is named in the source.
4. Check the answer against the rules below, then output it inside `<answer>`.

## Answer Form

- Name the answer as the source names it, keeping any title or honorific that is part of that name (e.g. 'Sir Francis Drake').
- Do not add parenthetical expansions, alternate names, or descriptive tails beyond the name itself.
- Give one specific answer, not a paraphrase of it or an enumerated list.

## Error Avoidance

- Match the grammatical slot of the clue. Answer 'Guam' for "this U.S. territory", not 'University of Guam'; answer 'laundries' for "these Chinese businesses", not 'Chinese Hand Laundry Alliance'.
- Do not append parenthetical expansions, alternate names, or descriptive tails: 'LPGA' not 'LPGA (Ladies Professional Golf Association)'; 'Conan' not 'Conan (Arnold Schwarzenegger)'; 'hydroelectric' not 'Hydropower (hydroelectric power)'.
- Return the specific named answer, not a description or a full list: 'bubble gum' not 'Modern chewing gum'; 'sheep' not 'sheep, goats, cattle, hogs, horses, mules, and donkeys'.
