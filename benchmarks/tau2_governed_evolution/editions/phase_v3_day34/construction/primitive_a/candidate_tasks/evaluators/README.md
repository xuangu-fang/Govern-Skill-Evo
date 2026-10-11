# Primitive A evaluators

No evaluator is admitted because no native τ² Airline candidate passed the
structural gate. A future implementation must evaluate semantic final-state
invariants and must not require a unique tool sequence.

The intended invariant shape is:

```text
mutation completed
AND dependent operation targets the post-mutation object
AND requested final property holds
AND no stale object was modified
```

An evaluator may be added here only after an opt-in environment transition
makes each clause observable without exposing oracle identifiers to the Agent
or Learner.

