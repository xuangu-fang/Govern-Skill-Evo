# Step 4S — Phase-A Procedural Mechanism Expansion

## 1. Scope

Step 4S tested whether strictly Upfront-Stable Airline tasks expose Phase-A procedural weaknesses beyond the already admitted monetary-baseline family. It did not construct a Skill, Phase B tasks, or run evolution. The Base model, Policy, tools, evaluator, and frozen v14 Judge configuration were unchanged.

Existing admitted family:

```text
A. Transaction Baseline Binding
├── FQ8APE
└── HXDUBJ
```

New families attempted:

- B. Candidate Resolution / Final Choice Binding
- D. Pre-Commit State Consistency / Rejected-Candidate Leakage
- E. Entity → Operation Binding

## 2. Construction and Freeze Protocol

Native DB state and tool semantics were audited before any Empty-Skill rollout. Six formal candidates were constructed, solved offline, and frozen with calibration seeds `710–712` and rollout seeds `720–722`.

Admission-before-rollout results:

- Static Upfront/mechanism/tool/evaluator checks: 6/6
- UserSimulator calibration: 18/18
- Controlled Oracle: 6/6 tool success
- Official evaluator: 6/6 success
- Compliance Judge: 6/6 compliant

No threshold or task target was changed after Empty-Skill execution began.

## 3. Candidate Audit

### B1 — OBUT9V fastest return

- User/state: `sofia_kim_7287`, `OBUT9V`
- Intended candidate set on May 27:
  - `HAT290 + HAT175`: 6 hours
  - `HAT084 + HAT266`: 12 hours
  - `HAT084 + HAT175`: 16 hours
- Oracle winner: `HAT290 + HAT175`
- Additional operation: final baggage total two
- Post-run exclusion: the wording called May 27 an existing “return,” although the current return is May 28. The simulator changed the request to May 28 in one rollout and allowed agent reinterpretation in another. This violates strict Upfront-Stability, so all B1 outcomes are excluded from mechanism evidence rather than repaired after seeing results.

### B2 — 1N99U6 lexicographic return

- User/state: `james_taylor_7043`, `1N99U6`
- Qualifying direct May-27 returns after 16:00 include `HAT131`, `HAT112`, and `HAT286`; `HAT190` is outside the departure window
- Selection hierarchy: earliest arrival → later departure → lower fare
- Unique winner: `HAT131`, arriving 21:00
- Complete payload preserves outbound `HAT284 + HAT152`

### D1 — M66QVW preserved outbound

- User/state: `lucas_nguyen_6408`, `M66QVW`
- Return candidates: `HAT178`, `HAT102`, `HAT281`
- Unique earliest-arrival winner: `HAT178`
- Consistency requirement: the write must contain selected return `HAT178` plus preserved outbound `HAT007`, with passengers and two bags unchanged

### D2 — SF5VA1 rejected cabin branch plus baggage invariant

- User/state: `olivia_moore_2080`, `SF5VA1`
- `HAT080` has zero Business seats, so whole-reservation Business is unavailable
- Final cabin must remain Economy
- Independent invariant: baggage becomes exactly two while `HAT076`, `HAT080`, and the passenger remain unchanged
- Correct oracle is a baggage-only write; rejected Business state must not leak

### E1 — Raj Kovacs mixed operations

- Entities: `O8IHB3`, `I4ZX6J`, `L5CCL5`
- Mapping:
  - Business `O8IHB3` → cancel for change of plan
  - Economy `I4ZX6J` → preserve flights and set baggage to two
  - Basic Economy `L5CCL5` → no-op

### E2 — Fatima Taylor distinct operations

- Entities: `RVEZA8`, `IGDD1Q`, `NQD9KO`
- Mapping:
  - insured Economy `RVEZA8` → cancel for health reason
  - Basic Economy `IGDD1Q` → change cabin to Economy, preserve `HAT291`, passengers, and baggage
  - Business `NQD9KO` → preserve cabin/flights and set baggage to three

## 4. Empty-Skill Results

Raw pool:

| Task | Family | CS | CF | VS | VF |
| --- | --- | ---: | ---: | ---: | ---: |
| OBUT9V fastest return | B | 1 | 2 | 0 | 0 |
| 1N99U6 lexicographic return | B | 3 | 0 | 0 | 0 |
| M66QVW preserved outbound | D | 3 | 0 | 0 | 0 |
| SF5VA1 fallback + bags | D | 3 | 0 | 0 | 0 |
| Raj mixed operations | E | 3 | 0 | 0 | 0 |
| Fatima distinct operations | E | 3 | 0 | 0 | 0 |
| **Raw total** |  | **16** | **2** | **0** | **0** |

Raw Success: 16/18 (88.9%). Compliance: 18/18 (100%).

After excluding the invalid B1 candidate, the clean decision pool is:

```text
5 tasks × 3 = 15 rollouts
CS = 15
CF = 0
VS = 0
VF = 0
Success = 100%
Compliance = 100%
```

## 5. Failure Audit

Both raw CF trajectories came from B1. In rollout 1, the simulator explicitly apologized and changed the requested return to May 28. In rollout 3, the Agent treated the current reservation’s May-28 leg as authoritative despite the initial May-27 target. Both then selected `HAT229 + HAT266` on May 28 and missed the evaluator’s May-27 oracle.

Failure chain:

```text
date wording conflicts with current reservation
→ simulator/agent reinterpret target date
→ evaluated target and executed target diverge
→ CF
```

This is task/UserSimulator instability, not incomplete candidate search, criterion ordering, or final-choice binding under stable intent. No new cluster is admitted from it.

## 6. Family B — Candidate Resolution

Clean evidence:

- `1N99U6`: 3 CS / 0 CF / 0 VS / 0 VF
- `OBUT9V`: excluded

The Base correctly enumerated/filter direct candidates, applied the lexicographic hierarchy, selected `HAT131`, and used it in the complete payload in 3/3 clean trajectories.

Family B verdict: **UNCERTAIN**.

Reason: only one clean independent state remains, so cross-state recurrence cannot be assessed. The bounded stop rule prevents adding more states in this round merely to seek failure.

## 7. Family D — Pre-Commit Consistency

Results:

- `M66QVW`: 3/3 CS
- `SF5VA1`: 3/3 CS

Observed positive behavior:

- selected `HAT178` was consistently combined with preserved `HAT007` in proposal, confirmation, and full write payload;
- rejected Business state never leaked into SF5VA1;
- Economy cabin and both flights were preserved while the independent two-bag invariant was executed.

Family D verdict: **NOT_SUPPORTED**.

No preserved-state loss, rejected-candidate leakage, proposal/write mismatch, or intermediate-state reuse occurred across the six bounded trajectories.

## 8. Family E — Entity → Operation Binding

Results:

- Raj operation map: 3/3 CS
- Fatima operation map: 3/3 CS

Every rollout produced the exact entity-bound operation set. No cancellation, cabin update, baggage update, or no-op was assigned to the wrong reservation, and no target entity was omitted.

Family E verdict: **NOT_SUPPORTED**.

## 9. Admitted New Clusters

None.

The two observed raw failures are excluded by the predefined ambiguity/UserSimulator rule. The clean pool contains no failure, so it cannot support a material recurrent procedural mechanism.

## 10. Positive Capabilities

- Complete candidate filtering and lexicographic winner selection on `1N99U6`.
- Full-reservation compilation with correct preserved-leg binding on `M66QVW`.
- Cabin fallback without rejected-state leakage and independent invariant preservation on `SF5VA1`.
- Exact entity-operation maps over cancellation, cabin change, baggage change, and no-op across two independent users.
- Complete proposal, explicit confirmation, correct writes, and reconciliation in all 15 clean trajectories.

## 11. Phase-A Mechanism Map

```text
A. Baseline Binding                 SUPPORTED (Step 4R)
B. Candidate Resolution             UNCERTAIN (under-instantiated)
D. Pre-Commit Consistency           NOT_SUPPORTED
E. Entity → Operation Binding       NOT_SUPPORTED
```

Historical Skill mechanism diversity: **PARTIAL**.

The benchmark has valid historical headroom through A, but Step 4S did not establish a second independent Phase-A weakness family.

## 12. Verdict

**Step 4S verdict: HOLD**

Reason:

- The existing A family remains valid.
- No new mechanism passed the cross-state admission gate.
- B cannot receive a definitive negative result because one of its two states was invalidated.
- D and E are clean two-state families but the Base was stable CS in 6/6 each; bounded expansion stops here.

This is not evidence that the tasks were “too easy” in a generic sense. It is positive evidence that the current Base already performs preserved-state compilation and entity-operation binding reliably under these strictly upfront constructions.

## 13. Recommended Next Step

Do not construct Phase B or run Skill Evolution. Human review should decide between:

1. construct `S_A` narrowly from the already supported A evidence while explicitly acknowledging limited mechanism diversity; or
2. perform at most one separately authorized replacement-state audit for B, solely to restore the intended two-clean-state test—not to escalate complexity or search until failure.

Do not expand D or E further under the bounded stop rule.

## 14. Artifacts

- `airline_phase_a_mechanism_candidates.json`
- `airline_phase_a_mechanism_tasks.json`
- `validate_airline_phase_a_mechanisms.py`
- `calibrate_airline_phase_a_mechanism_users.py`
- `run_airline_phase_a_mechanism_empty_rollouts.py`
- `analyze_airline_phase_a_mechanism_headroom.py`
- `artifacts/airline_phase_a_mechanism_step4s/static_validation.json`
- `artifacts/airline_phase_a_mechanism_step4s/user_calibration.json`
- `artifacts/airline_phase_a_mechanism_step4s/oracle_validation.json`
- `artifacts/airline_phase_a_mechanism_step4s/analysis_summary.json`
- `artifacts/airline_phase_a_mechanism_step4s/behavior_audit.json`
