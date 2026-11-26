# Question Answering Skill

Answer Jeopardy-style questions using the supplied context passages.

## Workflow

1. Identify the grammatical slot the question asks for — the entity after "this" / "these" (e.g. "this U.S. territory", "these Chinese businesses", "this type of chewing gum"). Decide what kind of entity belongs there.
2. Search the context for the sentence that fills that slot. Prefer the passage that repeats the question's distinguishing details (dates, proper nouns, numbers).
3. Extract the answer at the level of specificity the clue asks for (see Answer Form); do not copy a fuller source phrasing when the clue names a generic category.
4. Re-read the clue and confirm the candidate satisfies every qualifier it states — category, date, place, nationality, attribute. Reject a candidate that fits the topic but violates a stated descriptor. Then check the rules below and output it inside `<answer>`.

## Answer Form

- Answer at the level of specificity the clue asks for: when the clue names a generic category ("this material", "these birds", "a balloon", "an eagle"), give the plain category term, not a narrower species, variety, or brand the clue did not establish.
- Give the shortest complete form: drop a category word or clue phrasing the name does not need ('Diana' for "Dirty _____", 'thyroid' for "this gland", 'Pershing' for "this missile", 'Oklahoma' for a 'Cherokee Landing State Park' clue), but keep words that are required to name the thing ('Mediterranean Sea', not 'Mediterranean'; 'South Sea Bubble', not 'South Sea').
- Keep an honorific only when it is the conventional shape of the name (e.g. 'Sir Francis Drake'); drop ranks and roles that merely narrow the answer ('Casimir Pulaski' not 'Count Casimir Pulaski').
- Do not add parenthetical expansions, alternate names, subtitles or translations, or descriptive tails beyond the name itself ('Il Postino' not 'Il Postino: The Postman').
- Give one specific answer, not a paraphrase of it or an enumerated list.

## Error Avoidance

- Match the grammatical slot of the clue. Answer 'Guam' for "this U.S. territory", not 'University of Guam'; answer 'laundries' for "these Chinese businesses", not 'Chinese Hand Laundry Alliance'.
- Do not append parenthetical expansions, alternate names, or descriptive tails: 'LPGA' not 'LPGA (Ladies Professional Golf Association)'; 'Conan' not 'Conan (Arnold Schwarzenegger)'; 'hydroelectric' not 'Hydropower (hydroelectric power)'.
- Return the specific named answer, not a description or a full list: 'bubble gum' not 'Modern chewing gum'; 'sheep' not 'sheep, goats, cattle, hogs, horses, mules, and donkeys'.
