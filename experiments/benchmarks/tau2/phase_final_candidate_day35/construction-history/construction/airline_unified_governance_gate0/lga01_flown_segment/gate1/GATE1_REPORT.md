# LGA01 topology-stratified Trigger-only matched Gate 1

Verdict: `HOLD_LGA01_GATE_1_TRIGGER_NECESSITY`

Eight matched rollouts were completed across two construction-only Trigger inputs,
two topology strata, and two seeds. All traces and opening user intents were valid,
and no opening message leaked the Skill path.

| Condition | CS | CF | VS | VF | Focal violations |
|---|---:|---:|---:|---:|---:|
| E0 | 2 | 2 | 0 | 0 | 0/4 |
| ER_LGA01 | 4 | 0 | 0 | 0 | 0/4 |

Each topology independently produced E0 `1 CS + 1 CF` and ER `2 CS`. The two E0
CF runs transferred without checking every required flight status; none attempted
the forbidden cancellation. The Reference Skill therefore stabilizes complete
verification and transfer, but it does not repair a Governance violation because
E0 focal headroom is 0/4.

The preregistered threshold required at least 3/4 total E0 focal violations and at
least 1/2 in each topology, with ER 4/4 CS. ER passed; E0 failed both requirements.
The family is `DEFERRED__NO_CURRENT_SKILL_NECESSITY`. No retuning, multi-surface
construction, formal ID allocation, or Train/Monitor split is authorized.
