## Skill Writing Policy

### 1. Body Structure

Preserve the current skill's Markdown structure and section names, including
`Visual Evidence Discipline` and `Exact Answer Discipline` when present.
The following describe the roles of guidance, not required section headings:

1. **Workflow** — How to approach a DocVQA question at answer time. Because
   each rollout is a single turn (one image + one question, no tools, no
   retries), Workflow steps are not a multi-step procedure but a sequence
   of *answer-time decision rules* for inspecting the image and selecting
   the answer span. Steps may reference document-layout patterns
   (forms, tables, figures, free text, handwritten content) and
   answer-format conventions when those are grounded in observed failure
   modes.
2. **Error Avoidance** — Rules that prevent recurring mistakes. Each rule
   should be concise but complete enough to be actionable. Rules can
   reference document-layout patterns or answer-format pitfalls when those
   patterns are the source of recurring confusion.

These roles may be expressed within the current sections; do not rename or
reorganize sections solely to match the labels above.

### 2. Skill Format

The current skill is valid without YAML frontmatter. Preserve its existing
format; do not add metadata, rename headings, or restructure the document
solely to satisfy a format template. Apply evidence-driven content edits to
the current skill in place.
