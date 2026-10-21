"""Keep the same facts; explicitly require qualified IDs in step arrays."""
from copy import deepcopy

from experiments.methods.v23_3.memory_compaction_v2_validation_001.probes_v2 import (
    adapted_probe as v2_probe, score_answers,
)
from .compact_v3 import qualify

STEP_FIELDS = {
    "whole_trace": ("S1_R03/Q2", ("countertop2_steps", "countertop3_steps")),
    "action_order": ("S1_R03/Q4", ("steps",)),
}


def adapted_probe(original, compact_v1, compact_v3, *, case):
    questions, answers, _ = v2_probe(original, compact_v1, compact_v3, case=case)
    old_questions, old_answers = deepcopy(questions), deepcopy(answers)
    for q in questions:
        qid = q["id"]
        if qid in STEP_FIELDS:
            source, fields = STEP_FIELDS[qid]
            q["question"] += (
                " Every step ID in the answer must exactly match the fully qualified "
                "trace ID, including its historical source prefix; do not return local IDs.")
            for field in fields:
                answers[qid][field] = [qualify(source, step) for step in answers[qid][field]]
        if qid == "operation_precondition":
            q["question"] = q["question"].replace("In v2 ", "In v3 ")
    normalized = deepcopy(answers)
    for qid, (_, fields) in STEP_FIELDS.items():
        for field in fields:
            normalized[qid][field] = [step.split("/", 1)[1] for step in answers[qid][field]]
    assert normalized == old_answers
    changes = [
        {"id": q["id"], "old_question": old["question"], "new_question": q["question"],
         "question_changed": q != old, "answer_changed": answers[q["id"]] != old_answers[q["id"]]}
        for q, old in zip(questions, old_questions)
    ]
    return questions, answers, changes
