# Archived input cost audit

Read-only actual archives, no API or ALFWorld. 08 observations are old grouped_update.v1, not v3 measurements. 15 contains true v3 Diagnosis/Editor inputs, but inherited classifier.

All numbers are read from frozen messages and provider usage; no API/environment executed.

| Archive/stage | System chars | User chars | Compact messages chars | Actual input tokens | Runs / steps | History fields chars |
|---|---:|---:|---:|---:|---:|---:|
| 08_r1_classification | 3006 | 124863 | 140036 | 41019 | 10 / 240 | 0 |
| 08_r1_diagnosis | 4742 | 160478 | 182565 | 53888 | 10 / 240 | 0 |
| 08_r1_main_editor | 4968 | 166833 | 189655 | 55814 | 10 / 240 | 6 |
| 08_r1_post_gate_learning | 7214 | 263628 | 298551 | 88334 | 20 / 415 | 6 |
| 08_r2_classification | 3006 | 116495 | 131044 | 38531 | 10 / 235 | 0 |
| 08_r2_diagnosis | 4742 | 150867 | 172176 | 51174 | 10 / 235 | 0 |
| 08_r2_fusion | 7757 | 222018 | 250924 | 75663 | 10 / 235 | 65234 |
| 08_r2_main_editor | 4968 | 222337 | 248412 | 75228 | 10 / 235 | 65234 |
| 08_r2_post_gate_learning | 7214 | 356496 | 398816 | 119314 | 20 / 474 | 65234 |
| 08_r2_classification_failed | 3006 | 116495 | 131044 | 38531 | 10 / 235 | 0 |
| 08_r2_fusion_failed | 7757 | 222018 | 250924 | 75663 | 10 / 235 | 65234 |
| 08_r2_learning_failed | 7214 | 356496 | 398816 | 119314 | 20 / 474 | 65234 |
| 15_r1_classification | 3006 | 82606 | 93586 | 27619 | 8 / 104 | 0 |
| 15_r1_diagnosis | 5036 | 105214 | 120984 | 36049 | 8 / 104 | 0 |
| 15_r1_main_editor | 5170 | 110704 | 127034 | 37704 | 8 / 104 | 8 |

R1 Fusion is program identity, not a semantic call. R2 learning recovery is byte-identical in messages to failed request; failure was output truncation (16,384 limit), not input overflow.

## Key repeated/oversized inputs
- The same ordered full Parent runs and complete command sets go to Diagnosis, Fusion, and Editor; current v3 still routes the same effective_consumption_payload to Fusion and Editor. This is role redundancy, not necessarily same-message duplicate content.
- Learning repeats grouping at root and update_context.grouping, and source group snapshots expand member execution identities again. Event source directory repeats run/step already encoded in aliases.
- current_run_facts repeats run identities/status plus useful deterministic counts; a compact view can share identity fields without removing counts.
- command_sets deduplicates identical complete lists, but repeated command strings appear across distinct lists. Literal string interning can preserve every action opportunity.
- Full ordered observation/action evidence is retained; repeated observation strings can be interned without merging events or dropping timestamps/step order.
- In 08 Memory, actual_update is repeated per basis. v3 already shares it under historical_updates, but all retained basis sources and all history updates are still consumed each time.

## Existing experiment scope restriction
The current v3 learning builder requires split=train and purpose=learning (compact_learning.py:56-57), and classification requires train: task IDs (grouped_representation.py:72). Input capacity alone does not authorize Train+Selection mixing; do not relabel Selection as Train to bypass this protocol.

## Source references
- grouped_update.py:90-101 update_payload shares current evidence; :164-195 _unified_messages uses full effective view for Fusion/Editor/Learning.
- grouped_representation.py:34-96 classifier keeps ordered actions/observations and complete shared command lists; :155-185 grouping is copied and expanded into sources.
- compact_learning.py:22-95 all paired current trajectories; :98-127 source resolver; :130-166 response provenance closure.
- effective_memory.py:53-128 all active Effect/basis consumed; :188-242 inherited basis/limits; no consumption length bound.
- compact_learning_view.py:70-132 shares historical sources and removes command lists/fingerprints. Important: historical action opportunity cannot be inferred from omitted command candidates.
- continual_runner.py:211-214 400k-like plan budget checked only after per-stage input is assembled; no automatic shortening.

results.json contains SHA256 and exact artifact paths, field/subfield decomposition, run/command/source counts, exact duplicated string estimates and call-message integrity checks.
Repeated-string potential is not measured net savings: reference/schema overhead must be accounted for in a separate prototype. Actual output-token anomalies (e.g. R1 provider completion above requested max) are retained as provider data rather than silently corrected.
