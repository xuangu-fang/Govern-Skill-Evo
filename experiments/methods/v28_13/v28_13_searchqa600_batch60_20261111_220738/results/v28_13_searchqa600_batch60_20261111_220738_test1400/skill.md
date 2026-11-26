# Question Answering Skill

## Workflow

1. **Answer a bare list or place pair with the shared label.** When the question is a short list of related names or place names with no explicit question word, return the supported label, not a relationship sentence, in-universe setting, or descriptive phrase. For a fictional-character list, give the work title ('Inspector Luger,Wojo,Fish' -> 'Barney Miller', not '12th Precinct'). For a real-person pair, give their shared place/state/nationality, or, if none is shared, the most specific shared affiliation ('Princess Caroline & Princess Stephanie' -> 'Monaco'). For a pair of place names introduced by 'In', give the shared language/nationality adjective ('In Dijon & Bordeaux' -> 'French', not 'France').

## Error Avoidance

- **Stop at the open-slot label.** When a clue asks for a concise label or already supplies the category, relation, or descriptive wording, answer with the label that fills the requested slot alone and stop. Do not add a generic noun, qualifying modifier, middle initial, acronym expansion, formal expansion, formal-title modifier, leading ordinal, or parenthetical codename/explanation; do not repeat clue-side wording unless needed to identify the answer. Retain words needed to identify the requested thing or avoid ambiguity.
  - 'hydroelectric' not 'Hydroelectric power' (clue: 'this ... electricity source')
  - 'laundries' not 'Chinese hand laundries' (clue: 'the alliance of these Chinese businesses')
  - 'George Bush' not 'George H. W. Bush' (clue: names 'George Bush' and the election announcement)
  - 'a balloon' not 'speech balloon' (clue: 'Term for the circle that encloses a comic strip character's dialogue')
  - 'Bull Moose' not 'Bull Moose Party' (clue: asks for a nickname)
  - 'SCTV' not 'SCTV Network' (clue: calls it a comic "network")
  - 'a balloon' not 'a hot air balloon' (clue: asks what a chair back is shaped like)
  - 'The Polar Express' not 'Express' (boundary: clue quotes only 'Express'; the shorter form would not identify the answer)
- **Include a quoted component when the complete fixed phrase is the requested term.** When the clue quotes one word of a recognized multiword idiom and asks for that idiom, return the full fixed phrase, including the quoted component. Example: for '"Turning" this type of "evidence"...' return 'turning state's evidence', not 'state's evidence'. This is an exception to omitting supplied category words; outside a fixed phrase, keep the shorter open-slot label.
- **Give only the missing or distinctive title/category label.** When the clue supplies part of a quoted title or a category word, return only the missing or distinctive label; do not repeat the supplied part or append a cued category/formal suffix.
  - 'Diana' not 'Dirty Diana' (clue: 'Dirty _____')
  - 'Pershing' not 'Pershing missile' (clue: cues the category)
  - 'Grambling' not 'Grambling State University' (clue: 'Louisiana univ.')
  - Boundary: if the clue asks for a complete established name, give the full name; retain honorifics and first names that are part of the established answer, and keep any word needed to identify it (e.g. 'The Polar Express').
- **Return the requested term or short name alone.** When a clue gives the defining relation and asks for a term or named entity, answer with the requested term or established short name; do not append the relation or an unneeded category word. Retain a word when the shorter form would not identify the answer.
  - 'a transit' not 'transit of Venus' (clue: 'the term for the rare passing in front of the sun that Venus did')
  - 'the Amazon' not 'Amazon River' (clue: the river described by its Maranon and Ucayali branches)
  - 'Padre Island' not 'Padre' (boundary: the shorter form would not identify the answer)

- **Retain a standard honorific.** When the passages consistently give an honorific such as 'Sir' or 'Lord' as part of the person's standard name and the clue does not supply a shorter name, include it; do not add merely descriptive role titles like 'President' or 'Governor' when the answer is the bare name.
  - 'Sir Isaac Newton' not 'Isaac Newton' (clue: Royal Society president)
  - 'Lord Robert Baden-Powell' not 'Robert Baden-Powell' (clue: Boy Scout founder)
- **Match supplied spelling for names and terms.** Reproduce the form used by the clue and passages; do not add diacritics from outside knowledge when the supplied text uses the plain form. If the source itself gives diacritics, retain them.
  - 'Vaclav Havel' not 'Václav Havel' (clue: supplied plain spelling)
- **Answer with the associated person for a bare slogan or catchphrase.** When the question is only a well-known slogan or catchphrase and does not explicitly ask to complete it or fill a 'this ...' slot, give the person chiefly associated with it, not a paraphrase or the missing words. If the clue asks for the brand or item (for example, 'Choosy moms choose this') or explicitly asks for the quoted words or hit, fill that requested slot instead.
  - 'William Henry Harrison' not '1840 campaign slogan for William Henry Harrison and John Tyler' (clue: 'Tippecanoe and Tyler too')
  - 'Darrell Waltrip' not 'racing boys!' (clue: 'Boogity boogity boogity! Let's go raci')

- **For terse geography clues, answer the containing place named by the clue's grammar.** When a clue places a feature in a region ('Mount Kosciusko in New South Wales'), says a place is home to a feature, or asks what contains a resource ('...That contains 70% of Earth's fresh-water resources'), return the containing country/state/continent rather than a superlative description or the contained feature/subarea. Examples: 'Australia' not 'Australia's highest mountain'; 'California' not 'Ancient Bristlecone Pine Forest'. If the clue explicitly asks for the feature ('this mountain', 'this forest', 'this palace'), fill that feature slot instead.
