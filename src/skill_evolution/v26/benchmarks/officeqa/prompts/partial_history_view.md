## Exact prefixes in partial citation contexts

In v2, a partial citation's request_messages may be an object:
{"officeqa_history":"SOURCE_REF","prefix_messages":N,"suffix":[...]}.
Expand SOURCE_REF's request_messages first, take exactly its first N messages,
then append suffix in order. Expand shared initial-message pointers as above.
SOURCE_REF is an earlier, already supplied source_records key from the same
execution, task, role and historical namespace. References can form a backward
chain; they never fetch an archive, an uncited step or a paired execution.

This reconstructs only this citation's original formal request context. A longer
source context does not extend this citation's boundary. Reusing a prefix does
not merge actions, observations or repeated events: preserve every message's
position, multiplicity, role and exact content. The cited record's own call,
observation or assistant and all original evidence IDs remain separate and
unchanged. Prefix references describe storage, not new evidence, pairings,
causal conclusions or permission to cite additional steps. Apply the same
Verifier/Repair rules after reconstruction; do not emit the encoding in output.
