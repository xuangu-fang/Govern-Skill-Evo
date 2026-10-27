# R06: fresh Diagnosis followed by fixed-Plan Preconditioner

Authorized scope: regenerate Diagnosis using the same archived R06 current facts,
freeze its first structurally valid Plan, and run Preconditioner with that Plan and
the unchanged R06 Memory. Review Goal / Updates / Checks consistency manually.

- Current facts and background come from the original R06 Diagnosis input at
  `artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001`.
  The decoded Diagnosis user payload must equal the archived payload exactly.
- Use the current V23.4 production Diagnosis and Preconditioner prompts. Do not
  add case-specific hints or change production algorithms or prompts in this run.
- Diagnosis receives current facts only, without Memory. Memory is copied exactly
  from `semantic_generation_003/config/cases/R06.json`.
- Freeze sources, inputs, prompts, model and transport settings before calling.
  Freeze the first structurally valid Diagnosis output, derived Preconditioner
  input and messages before the Preconditioner call. Normal production evidence
  selection determines which current runs reach Preconditioner.
- At most two logical stages, each with an initial request plus three technical
  restarts under the previously authorized retry policy. Do not retry a valid
  output because its semantic quality is poor. A valid Diagnosis with no Plan
  stops the handoff. An all-withdrawn effective result is not converted to Keep.
- No Editor, Actor, Replay, or additional reviewer model is called. Keep prior
  experiment archives unchanged. Audit recorded requests, hashes and compiler
  results offline; distinguish structural validity from manual semantic findings.
- Assess whether Goal commits to unverified procedure, Updates support Goal,
  Checks agree with surviving Updates, and Preconditioner change / patch remain
  consistent. Report unresolved issues without editing generated outputs.

Commands: run this directory's Python module with `prepare`, `R06 diagnosis`,
`freeze-plan`, `R06 pc`, then `audit`. Use the existing tau2 Python environment.
