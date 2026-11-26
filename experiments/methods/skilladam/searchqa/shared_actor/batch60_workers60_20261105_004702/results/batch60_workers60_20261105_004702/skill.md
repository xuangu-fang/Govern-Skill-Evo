# Question Answering Skill

## Workflow

1. **Pin down the target.** Read the clue and decide what the blank actually
   refers to: a person, place, work, character, term, or quantity. Names,
   epithets, dates, and plot details in the clue are pointers; the answer is
   the entity they point at, not every entity they mention.
2. **Infer the answer type from the clue's grammar.** Phrasings such as
   "this X" / "these Xs" / "he" / "a type of Y" state the category the answer
   must belong to. Answer with an item of exactly that type. When the clue asks
   for a term or name ("this term for ...", "this word meaning ..."), give the
   bare term and do not attach the instance the clue mentioned: `Transit`, not
   `Transit of Venus`. When the clue has no blank and is just a name or a list
   of names, say what they share in the fewest words that fit — usually one
   category word, or the work the names come from, never a description of it:
   `Senators`, not `Fellow Democratic U.S. Senators from Massachusetts`;
   `Kings`, not `Kings of Spain`; `Barney Miller`, not `Barney Miller
   characters`; `U2`, not `U2 tribute band` — the shared thing itself, never
   with a trailing category noun. For `Hamburg` or `Dijon & Bordeaux`, give the
   shared category rather than a descriptive phrase or the country they sit
   in. When the clue is nothing but an honorific and a name ("Sultan Haji
   Hassanal Bolkiah"), answer with the one entity that identifies the person
   instead of repeating the honorific: `Brunei`, not `Sultan of Brunei`.
3. **Draft the shortest identifying name.** Your answer is the word that fills
   the slot the clue sets up, so a generic noun the clue already supplied is
   not part of it: "this market that features a lengthy period of price drops"
   -> `Bear`; "higher in this vitamin than oranges" -> `C`; "this state
   university at Superior" -> `Wisconsin–Superior`; "this island off North
   Carolina" -> `Roanoke`. Otherwise write the plain name with no descriptive
   qualifiers and no alternative spellings, expansions, or translations
   appended, and keep a designator only when it belongs to the entity's own
   established name (`Padre Island`, `Gorky Park`) or when the compound is
   itself the entity's title, as with a named dish (`Grasshopper pie`, not
   `Grasshopper`).
4. **Test the candidate against the clue.** Substitute it back into the clue
   and confirm every stated detail holds and that the candidate is the entity
   being described rather than a related one (the character rather than the
   actor, the work rather than its author, the city rather than the country).
5. **Output only the candidate** as the text of the `answer` element.

## Error Avoidance

- **No parentheticals or alias expansions.** Give one form, not the name plus
  its expansion, translation, or incidental alternatives.
  - `Hydropower`, not `Hydropower (hydroelectric power)`
  - `LPGA`, not `LPGA (Ladies Professional Golf Association)`
  - `Sheep`, not `Sheep or goats (occasionally cattle, hogs, horses, mules, or donkeys)`
- **No filler modifiers and no clue echoes.** Drop adjectives that do not
  discriminate, and never repeat a word the clue already supplied.
  - `Chewing gum` (or the specific gum type), not `Modern chewing gum`
  - `Laundries`, not `Chinese hand laundries`
  - `Amazon`, not `Amazon River`; `Roanoke`, not `Roanoke Island`
  - `Transit`, not `Transit of Venus` — the answer need not restate the clue's subject
  - `Bull Moose`, not `Bull Moose Party` — the clue already said "party"
  - `Balloon`, not `Hot air balloon` — the shorter word is the whole answer
- **Resolve the referent before answering.** When a clue paraphrases a title
  or describes a role, the answer is the figure inside that title, not the
  performer who played it or the author who wrote it.
- **Write plain ASCII spellings.** Drop diacritics and accent marks from
  names, since reference answers usually record them that way.
  - `Vaclav Havel`, not `Václav Havel`
  - `Jean-Honore Fragonard`, not `Jean-Honoré Fragonard`
