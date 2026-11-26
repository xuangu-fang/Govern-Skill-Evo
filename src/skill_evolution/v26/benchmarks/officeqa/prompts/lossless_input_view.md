## OfficeQA lossless input representation

If `_officeqa_encoding` is present, it is an encoding header, not task evidence.
Its `messages` table contains complete original messages. Replace each object
`{"officeqa_message":"mN"}` in an initial or cited request message array with
that table's message at the same position. Text, role and scope are unchanged.
Identical system messages can be shared; user messages are shared only within
the same execution or an explicitly paired pair whose entire initial user
sequence is identical. Different Skills and different page contents stay distinct.

In a complete run (initial + attempts + outcome), repeated `request_messages`
are omitted. Round n's formal context is exactly initial.messages followed, in
order, by each earlier round's complete assistant message and all that round's
tool observation messages. These reconstructed messages have the same evidence
scope as before. They exclude temporary format repairs and failed generations;
they are not the full raw HTTP audit. Assistant content, tool calls, tool order,
arguments, returned text, truncation markers, errors and outcomes are retained.
For an isolated initial, round or tool citation, only its already supplied
context is available; its request_messages are retained. Do not infer additional
rounds, sibling tools or observations from a pointer or from a missing full run.

Pairs stay explicit and runs stay adjacent Parent/Candidate. Each side has its
own timeline; equal round numbers do not imply equal contexts. Repeated calls
and observations remain separate events. Scores remain post-execution evidence.
Table keys are not evidence IDs: cite the original run/round/tool references.
Decode for interpretation, not in your response. The existing output contract,
evidence permissions and learning requirements are unchanged.
