# Question Answering Skill

## Workflow

1. **Name the answer slot.** Decide what kind of thing the question asks for:
   the head noun after "this"/"these" ("this U.S. territory", "these animals",
   "this type of chewing gum") or the gap a definition leaves open. Treat that
   head noun as a hard constraint on the answer.
2. **Classify the clue.**
   - *Description or definition*: the answer is whatever the description
     defines.
   - *"this X" / "these Xs"*: the answer is an X. A related organization,
     institution, work, or title that merely contains X is not an X.
   - *Named trio* ("A, B, C"): the three items share one property; answer with
     the conventional single-noun label for that property, not a descriptive
     sentence.
   - *Multiple choice* ("of 2, 5, or 10"): answer with one listed option,
     nothing else.
3. **Draft the shortest complete answer.** Pick the specific term the clue
   points to rather than a generic restatement of the question, then strip
   everything that is not the answer: no parenthetical alternatives, no "or"
   lists of other possibilities, no extra qualifiers. For a person, give the
   name as the person is usually known, not a fully expanded formal name, and
   answer with the part of the name the clue did not supply: when the clue
   names only the forename, answer with the surname alone; when the clue
   writes out the full name, give that exact form back, adding no middle
   initials or extra forenames.
   Do not re-attach the category the clue already named: when the clue says
   "this island", "this company", or "this term", and the distinctive word is
   a complete recognizable name on its own, answer with that word alone. Keep
   the category word only when the distinctive part is an adjective that
   cannot stand alone ("Roman Empire", "drip irrigation") or when the answer
   is a work's title ("Gorky Park").
4. **Verify against the slot.** Say "The answer is a ___", filling the slot
   from step 1 with your draft. If the sentence reads wrong, the draft is the
   wrong kind of entity or the wrong level of generality — redraft. Then run
   the category check: if a word in your draft is exactly the category word
   the clue already supplied for the slot ("this market" -> market, "this
   vitamin" -> vitamin), delete that word and answer with the distinguishing
   remainder ("bear", "C"). Put the word back only when the whole phrase is
   the established name ("South Sea Bubble", "Roman Empire", "Ace Hardware").
5. **Emit** only the final string inside `<answer>...</answer>`.

## Error Avoidance

- Answer the slot, not the surrounding entity. A clue asking for a territory
  wants the territory, not the university located in it; a clue asking for a
  type of business wants the business type, not the name of the businesses'
  alliance.
- Exactly one answer form. A parenthetical or slash alternative ("X (also Y)")
  breaks exact match even when one form is right, and so does an appended
  example or hedge list ("X or Y, occasionally Z").
- Name the specific variety when the clue asks for a type or kind; answering
  with the generic category plus an adjective misses the target.
- Match the conventional form. Prefer the short form the answer is normally
  called (a plural noun for a class of cities, the standard one-word term for
  a technology or a sport — "hockey", not "ice hockey") over a longer phrase
  that means the same thing. For a person,
  use the customary short or nickname form — don't stack every forename, and
  don't substitute a formal given name for a common nickname. For a place, a
  company, or a term, give the distinctive name on its own rather than naming
  the category again: "Roanoke" not "Roanoke Island", "Hallmark" not
  "Hallmark Cards", "transit" not "Transit of Venus" — but keep the category
  in "Roman Empire" and "drip irrigation", where the distinctive word cannot
  stand alone. Trimming stops at the complete conventional name: keep a
  regnal numeral ("Richard III"), a title that belongs to the familiar name
  ("Sir Isaac Newton"), and the second half of a compound proper name
  ("Funk & Wagnalls"). These identify which entity is meant; they are not
  extra qualifiers. By the same measure, never attach the relation or the
  kind of item to an answer that is already complete: for a list of people
  who were all someone's spouses, answer with that person's name alone, not
  the name plus "'s wives"; for a list of characters, answer with the work's
  title alone, not the title plus "characters".
