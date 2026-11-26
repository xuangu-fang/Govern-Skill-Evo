# Question Answering Skill

## Workflow

1. **Fix the answer type from the clue's grammar.** "this state / city / country" wants a place name; "he / she / this author / this actor" wants a person; "this term / word / adjective" wants the dictionary form of the word; "the number of ..." wants a numeral; "this novel / film / song" wants a title; a bare clue with no question in it - a single name, or a comma-separated list of names - asks for a different term, never the clue's own word: for one name, what it is or where it is; for a list, the one thing the names all share (the category, group, show, or work they come from). The committed type constrains every later step.
2. **Collect every constraint in the clue** - dates, roles, works, places, superlatives, "formerly", "only", stated letter counts. A candidate qualifies only if it satisfies all of them; this is what separates look-alike entities.
3. **Commit to one entity.** When the clue's own wording reproduces part of a known title or name, answer that titled entity rather than the person associated with it: adjectives in the clue that match a pair of titles point at the character in those titles, not at the actor who played him.
4. **Write the answer in canonical minimal form** (below), then stop. Nothing else goes inside the answer element.

## Answer Shape

Give the shortest form that still names the entity exactly.

- **One answer, no alternatives or examples.** A clue about "these animals" wants the general answer, not the whole list of possibilities.
  - `sheep` - not `sheep or goats (occasionally cattle, hogs, horses, mules, or donkeys)` (clue: "Catgut comes from these animals")
- **No label, no restatement of the clue, no explanation.** A bare list clue gets the one shared thing as a short phrase, never a description of what the listed items are.
  - `capitals` - not `World capitals: Minsk (Belarus), Monrovia (Liberia), Manama (Bahrain)` (clue: "Minsk, Monrovia, Manama")
  - `What's Happening!!` - not `the main characters of What's Happening!!` (clue: "Roger Thomas, Dwayne Clemens, Freddie 'Rerun' Stubbs")
- **Never repeat a generic noun the clue already supplied.** If the clue calls it "this party", "this company", "this network", "this market", "this vitamin", the answer is the distinctive word alone.
  - `Bull Moose` - not `Bull Moose Party` (clue: "...called it the Progressive party, but it was nicknamed this after Teddy Roosevelt joined")
  - `McCormick` - not `McCormick & Company` (clue: "This spice company that owns Schilling...")
  - `SCTV` - not `SCTV Network` (clue: "...winners in 1983 for writing for this comic 'network'")
  - `U2` - not `U2 tribute band` (clue: "Rock group Achtung Babies")
  - Exception: keep the head noun when the distinctive word is only a modifier that cannot stand alone as the name.
    - `pituitary gland` - not `pituitary` (clue: "In 1931 chemists discovered a growth hormone in this gland")
    - `Lake Superior` - not `Superior` (clue: "The Great Lakes are Huron, Ontario, Michigan, Erie & this one whose name implies greatness")
- **No words the clue did not require.** Drop adjectives, era words, and qualifiers that are not part of the name. A bare-list clue takes a bare category noun with no nationality or source qualifier.
  - `kings` - not `Spanish monarchs` (clue: "Ferdinand VII,Juan Carlos")
- **Answer the term the clue defines, not an example of it.** A definitional clue with no proper-noun target wants the class term.
  - `antiperspirant` - not `witch hazel` (clue: "An astringent applied under the arms to curtail sweating")
- **Fill exactly the slot the clue marks.** Find the marked blank - an explicit "this / these ___" slot or a stem the clue builds on ("multi-this", "gets rid of its F") - and answer that slot alone: not a neighboring noun from the sentence's preamble, and not a larger compound that swallows the requested piece.
  - `lingual` - not `multilingual` (clue: "...one who speaks many languages, can also be called multi-this, from the Latin for 'tongue'")
  - `[the candy]` - not `[the company named in the preamble]` (clue: "The company was founded to provide chocolate coating for these chewy yellowish-brown candies")
- **Do not over-specify a name.** `Anastasia` - not `Anastasia Romanov`, when the clue asks which Romanov a role portrayed.
- **People:** first name + surname. Keep a middle initial, or an honorific where it is part of the person's standard name.
  - `Dwight D. Eisenhower`, `Sir Francis Drake` - not `Eisenhower`, `Drake`
- **Works, places, organizations and products:** the name as commonly published - keep a leading `The` that belongs to the title (`The Divine Comedy`), drop a subtitle or explanatory tail the clue did not require (`Studio 60`, not `Studio 60 on the Sunset Strip`), and drop a trailing type word (`River`, `Island`, `Cards`, `Company`, `Network`, `Party`) when the bare name alone still identifies the entity; keep it when it is part of the proper name (`Padre Island`, `Tower of London`).
  - `Amazon`, `Hallmark`, `Roanoke` - not `Amazon River`, `Hallmark Cards`, `Roanoke Island`
- **Numbers:** numerals only (`5`, not `five eyes`).

## Failure Avoidance

- If the answer contains a word that is not part of the entity's name - a category word, an explanation, a parenthetical, a second candidate - delete it before answering.
- After trimming, re-check the answer against every constraint from step 2, then output it and stop.
- Never restate the question and never append a justification inside the answer element.
