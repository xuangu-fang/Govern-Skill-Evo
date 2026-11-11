## Multi-Knowledge Memory representation v1

Each active Memory entry has `id` and a nonempty `knowledge` array. Each Knowledge
has its own `text` and `evidence`; there is no entry-level evidence field and no
Knowledge ID. Interpret each text with its own supporting evidence and conditions.
Other Knowledge in the entry does not automatically support that text.

Historical knowledge remains revisable interpretation. Sources are the recorded
facts. When using the compact v3 view, references from all Knowledge jointly select
its existing detail windows; this does not merge their claims or evidence bindings.
Use Memory IDs and the original fact references, not invented Knowledge IDs.
This representation does not change D/S/C decisions or the Preconditioner output.
