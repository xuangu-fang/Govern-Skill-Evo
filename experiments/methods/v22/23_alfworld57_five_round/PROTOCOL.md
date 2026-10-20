# V22 ALFWorld 57 tasks, five formal continual rounds

Authorized 2026-10-16. Profile v22.unified_dsc.v6, P1 v22.p1_shared_input.v1,
typed references v22.typed_references.v1. Sparse revision inherits 22 then 21.
Task order: native train Manifest 39, then native val Manifest 18; batches
12+12+12+12+9. Preserve native IDs, entries, split, game hashes, prior contacts.
Both splits have explicit `development` purpose; former Selection is used for
optimization. Test is excluded. Environment seed 42, classification alias seed
200; no task-order randomization, API has no extra seed parameter. Initial
No Skill/empty Memory; no Stage 0. Eight Actor workers, 50 steps per episode.

Five sequential semantic stages use existing v6 Prompt/Schema/validators; even
R1 Fusion is a model call on empty Memory. Valid branches can omit subsequent
stages per existing contract. Output caps stay at 32768 for classification,
Diagnosis, Fusion and Editor; 65536 for Memory. Temperature 1, thinking enabled,
medium reasoning, no streaming, semantic read timeout 600s; Actor existing
16384 output, 300s read timeout, last two action/observation pairs. Official
endpoint and deepseek-flash for both roles are bound before first request.

Retain 400000 whole serialized-message Unicode character admission limit.
Before semantic dispatch also require UTF-8 bytes + 8192 framing token reserve
+ requested output <= conservatively 1000000 context tokens. Byte bound is an
admission upper bound, not a tokenizer or billing estimate. Context evidence:
https://api-docs.deepseek.com/quick_start/pricing/ (checked 2026-10-16: 1M).
Never delete historical basis, truncate input, alter Prompt or repair output.

Technical recovery budget deliberately preserves existing zero semantic retries
and zero episode retries. Actor retains six bounded same-request HTTP attempts
for existing retryable statuses; no network-exception retry. A contract/JSON/
length error or capacity failure stops at the saved stage. Completed calls and
checkpoints remain available and cannot be overwritten or resampled. No automatic
restart after a failed run. This is a frozen stop protocol, not an unbounded
repair mechanism. On failure drain already dispatched episodes and preserve raw
HTTP, usage, failed responses and latest atomic publication. No later round can
start without prior valid Skill+Memory joint publication.

Gate ACCEPT iff Candidate successes strictly exceed Parent on the same complete
comparable batch, else RETAIN. Valid no-change retains Parent without invented
Candidate results. RETAIN still learns actual paired edit responses; never adopts
the rejected Skill as wholesale correctness. Memory validated before publication.
No manual intervention for legal but poor model semantics. No independent Pilot,
historical probe, reviewer agent or extra output fields.

Resource evidence: bound prior budget_evidence.json, prior_contact_inventory.json
and earlier exposure inventory. Historical 08 R2 had 474 paired steps; prior
Memory calls have exhausted 65536 reasoning tokens or returned complete outputs
between roughly 17k and 56k. Five rounds can have up to 114 episodes, 5700 Actor
logical requests, 25 semantic calls. This is a ceiling, not a prediction. At the
historical 474/20 mean steps, 114 episodes would be about 2702 steps; task mix,
new skills and model randomness may change this substantially. Tokens, latency,
unknown usage and failed costs are measured; no fixed monetary cost promised.
