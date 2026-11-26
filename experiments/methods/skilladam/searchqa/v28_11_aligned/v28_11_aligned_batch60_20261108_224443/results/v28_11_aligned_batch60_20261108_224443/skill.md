# Question Answering Skill

## Workflow

1. Read the question, then scan the context. The answer string is almost
   always present verbatim in the context; locate and copy it rather than
   recalling from general knowledge.
2. Decide the expected answer type and surface form from the clue: person,
   place, work title, animal, concept, etc., and singular vs plural or
   character vs actor. A clue phrased "one of these [X]" asks for the
   singular form of X.
3. Extract the shortest phrase from the supporting passage that answers the
   clue, keeping the passage's exact wording.
4. Emit only that phrase inside `<answer>`.

## Error Avoidance

- Use the minimal canonical form; never append or prepend qualifiers,
  expansions, parentheticals, or a category noun to a correct core answer.
  When the clue already names the category ("this vitamin", "this market"),
  give only the distinguishing word, not the full phrase.
  - 'Sheep' not 'Sheep or goats (occasionally cattle, hogs, horses, mules, or donkeys)'
  - 'LPGA' not 'LPGA (Ladies Professional Golf Association)'
  - 'Hydroelectric' not 'Hydroelectric power'
  - 'Anastasia' not 'Anastasia Romanov'
  - 'Hallmark' not 'Hallmark Cards'
  - 'Roanoke' not 'Roanoke Island'
  - 'a transit' not 'transit of Venus'
  - 'C' not 'vitamin C'   (clue: "higher in this vitamin than oranges")
  - 'the bear' not 'bear market'   (clue: "this market that features a lengthy period of price drops")
  - 'The Outcasts' not 'The Outcasts of Poker Flat'   (clue: "these exiles 'of Poker Flat'")
  - 'Bull Moose' not 'Bull Moose Party'   (clue: "nicknamed this after Teddy Roosevelt joined")
  - 'a balloon' not 'hot air balloon'   (clue: "a back often shaped like one of these")
  - 'licorice' not 'Black Licorice'   (clue: "named for this black candy")
  - 'hockey' not 'ice hockey'   (clue: "a power play in this sport")
- When the clue asks for "this/these [category]" (e.g., "these Chinese
  businesses"), answer with the category word from the passage, not the name
  of an organization built around it.
  - 'laundries' not 'Chinese Hand Laundry Alliance'
- When a clue describes a role via film titles ("he's a destroyer... he was
  just a barbarian"), answer the character named in the titles, not the actor
  who played him.
  - 'Conan' not 'Arnold Schwarzenegger'
- When the clue is only a proper name, a list of names, or a declarative
  fragment that names or describes a landmark, natural feature, or
  record-holder with no explicit question, answer the larger place (country,
  state, continent) named in the passage — not the honorific or role built
  around the name, not the landmark itself, not a descriptive phrase about
  it, and not the generic class of features.
  - 'Spain' not 'King of Spain'   (clue: "Ferdinand VII, Juan Carlos")
  - 'Brunei' not 'Sultan of Brunei'   (clue: "Sultan Haji Hassanal Bolkiah")
  - 'Australia' not "Australia's highest peak"   (clue: "Mount Kosciusko in New South Wales")
  - 'California' not 'Ancient Bristlecone Pine Forest'   (clue: "Home to the world's oldest living things, a grove of 4,000-year-old bristlecone pine trees")
  - 'Antarctica' not 'Glaciers and icecaps'   (clue: "...That contains 70% of Earth's fresh-water resources")
