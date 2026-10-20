"""Bind pre-execution questions without inventing metrics or outcome predictions."""

from src.adapters.alfworld.skill_runtime import digest, object_digest


def observation_plan(parent, diagnosis, requirements, editor, candidate, actual_diff):
    targets = [{"id": "goal:" + goal["id"], "role": "target", "behavior": goal["behavior"],
                "proposal_ids": [p["id"] for p in requirements["proposals"] if goal["id"] in p["goal_ids"]]}
               for goal in requirements["goals"]]
    targets += [{"id": f"preserve:{i}", "role": "preserve", "behavior": row["behavior"],
                 "proposal_ids": []} for i, row in enumerate(requirements["preserve"])]
    return {"schema_version": "v22.observation_plan.v1",
            "bindings": {"parent": object_digest(parent), "diagnosis": object_digest(diagnosis),
                         "requirements": object_digest(requirements), "editor": object_digest(editor),
                         "candidate": object_digest(candidate), "diff": digest(actual_diff.encode("utf-8"))},
            "targets": targets,
            "expectations": [{"proposal_id": p["id"], "trigger": p["trigger"],
                              "expected_effect": p["expected_effect"], "uncertainties": p["uncertainties"]}
                             for p in requirements["proposals"]],
            "interactions": requirements["interactions"],
            "boundary_checks": requirements["boundary_checks"],
            "editor_unresolved_expectations": editor["unresolved_expectations"],
            "scope": "Questions inherited from pre-execution artifacts; no added causal claims, task scores or outcomes."}
