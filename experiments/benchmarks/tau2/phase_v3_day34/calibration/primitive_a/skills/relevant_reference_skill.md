# CALIBRATION ONLY — Primitive A Reference Skill

## Dynamic dependent-state handling

- After a mutation changes or replaces an object that later actions depend on,
  do not use identifiers or dependent attributes cached before the mutation.
- Re-read the committed state through the normal observation tool, resolve the
  current downstream target from that fresh state, and only then perform the
  dependent action.
- If the refreshed state does not expose one unambiguous valid target, stop and
  resolve the ambiguity instead of guessing or reusing the old target.

This Skill is an offline calibration control. It must not enter Parent Skill,
Diagnosis, Editor, evolution memory, task metadata, or Learner-visible input.

