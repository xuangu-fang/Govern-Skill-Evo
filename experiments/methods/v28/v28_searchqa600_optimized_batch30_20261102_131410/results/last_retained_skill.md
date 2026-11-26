# Question Answering Skill

## Explicit answer labels
- When the context contains a quiz, flashcard, or answer-key line that repeats the question or clue closely and explicitly supplies the answer as a short label after the clue, use that explicit label as the primary answer and preserve its wording and extent, even if a shorter phrase is otherwise possible. Do not replace it with a longer title, a different related name, or a more explanatory phrase. If several labels conflict, use the label whose surrounding clue matches the question most closely.

## Requested answer type
- When the question wording identifies the kind of answer wanted (for example, "this type of X" or "these businesses/animals"), first identify the requested entity type and level of specificity, then answer with the specific subtype or category supported by the passages rather than a broader umbrella label or a named organization that merely contains that category.
- Keep this conditional: if the question asks for an organization, title, or broader class, provide that requested form rather than forcing a narrower category, and do not discard an explicitly requested subtype name.
- When the question uses only a bare demonstrative or list (such as "these" without a following category noun) to ask for the class containing named examples, and it does not explicitly request a subtype, answer with the base category noun that covers the examples rather than adding a narrowing modifier; keep the specific subtype when the question asks for "this type of" or otherwise requests the narrower kind.

## Character or work versus performer
- When a clue describes a referent by role names or by words that form work titles and the passages also mention a performer or other associated person, answer the character or work identified by those descriptions rather than the performer. Use a performer answer when the question asks for the performer or actor, including when it explicitly asks who played, starred as, or performed a role.
- When a clue pairs a role or occupation with a quoted title or phrase that contains a personal name, and a passage names a person with that name in that role, answer that person rather than another person associated with the quoted work. Apply this only when a passage supports the name-role match; questions asking for the character, work, or performer keep the rule above.

## Person-name form
- For a person-name answer, use the name form that the passage sentence or heading matching the clue uses for that person. Do not expand a surname or short name into a longer full name with additional given or middle names, and do not replace a nickname or familiar first name with a different formal given name. A surname alone is sufficient when the matching passage uses the surname alone; when the matching source pairs a given name or nickname with the surname, keep that pairing without adding further names. When several name forms occur, prefer the one in the heading or answer label that most closely matches the clue; a formal given name in a separate sentence does not override the nickname or familiar name used in that matching heading or label.

## List-of-details clues
- When the clue is only a list of character names, roles, or identifying details without an explicit interrogative, answer with the single work, organization, place, or named entity that contains or unifies those details rather than describing the listed characters. If the unifying entity is a title, give the title alone without a preceding category description; if it is a place or organization, give its name alone without adding a family, group, type, or other category descriptor, and do not replace the name with a descriptive sentence. If the question actually asks for the listed people or characters themselves, name those instead.

## Bare place-name clues
- When a clue is only a place name with no explicit interrogative and the passages repeatedly locate it with a state name or abbreviation, answer with the state name alone. Do not restate the place's definition or give a fuller address-like description. If the question explicitly asks what the place is, or asks for a county, city, or country, give that requested level instead.

## Category-level common-noun answers
- For a category-level common-noun answer such as a fruit, animal, coin, or object, match the grammatical number used in the passage sentence or label that directly defines or names the category; do not change a singular category label to plural merely because the question uses a plural phrase such as "these ...". Keep the plural when that answering passage presents the category as a plural set or the question asks for multiple separate items, and keep the singular when the passage defines the class with a singular noun or the question asks for an individual named item. When both singular and plural forms occur, choose the form used by the sentence or label that directly answers the clue; a singular attributive form inside a title or modifier does not override a plural count noun in that answering sentence or label, and a generic plural mention does not override a singular definitional label.

## Primary versus alternative answers
- When the passages give a typical or primary item together with occasional or rare alternatives, answer with the single primary item when the question does not ask for all possibilities; if the typical description names more than one usual option, choose the one most consistently emphasized as typical or representative across passages, and do not append a parenthetical, a co-ordinate alternative, or an exhaustive alternatives list to a concise answer. Plural wording such as "these animals" does not by itself require listing every possible or co-ordinate option.
- If the question explicitly asks for all, every, or a complete list, include the relevant alternatives instead; do not omit requested alternatives merely to make the answer shorter.

## Final answer element
- Before final submission, render the answer as a literal, well-formed `<answer>...</answer>` element with the answer text inside; do not use backticks around the tag name, omit the angle brackets, or leave tag text in the answer content.
- Explanation outside the final answer element remains permissible; this check applies to the final answer element itself.

## Minimal fill-in-the-blank answers
- For fill-in-the-blank and "this [category]" questions, submit the shortest grammatically complete phrase that supplies the requested entity. When the question already supplies the category and the remaining identifying term alone unambiguously names the requested entity, omit a redundant generic category noun or an unnecessary qualifier appended to that term, including a modifier repeated from the question; this can include using an identifying adjective or modifier alone when it unambiguously names the requested entity.
- Do not strip words that are integral to a proper name, title, or established multiword term when the remaining word alone would be ambiguous or incomplete; keep distinguishing words that form an established subtype name, and let disambiguation of the requested entity take precedence over raw brevity.

## Partial title or quoted phrase
- When the question supplies only part of a title or quoted phrase, separate the supplied part from the missing part. If the supplied words are a trailing modifier or prepositional phrase and the clue asks for the term they modify, answer the missing head term alone rather than repeating the full title or phrase. If the supplied words are the head noun of an established title and the question asks for the work, give the full established title. Do not answer with a different work that merely contains the same quoted words, and do not override an explicit quiz or answer-key label that directly appends the full answer to the repeated clue.
