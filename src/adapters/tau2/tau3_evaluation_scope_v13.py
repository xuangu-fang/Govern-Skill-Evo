"""Benchmark-specific evaluation exclusions shared by Autonomous GSE v0.13."""

from __future__ import annotations


EXCLUDED_POLICY_CLAUSE_MARKERS = (
    "you should only make one tool call at a time",
    "you should at most make one tool call at a time",
)


def benchmark_exclusion_prompt(component: str) -> str:
    """Return the component-specific consequence of the shared tau3 exclusion."""
    shared = (
        "Tau3 benchmark/runtime exclusion: the one-tool-call-at-a-time requirement is "
        "outside v0.13 evaluation scope because flattened trajectories do not reliably "
        "represent operation concurrency. Several tool_call steps appearing before their "
        "listed tool_result steps may be sequentially executed by the benchmark orchestrator. "
        "This is an evaluation-scope exclusion, not a general GSE reasoning principle, and it "
        "does not create permission for unrelated Policy violations."
    )
    consequences = {
        "judge": (
            "Never output or paraphrase the excluded requirement as a violation. "
            "Tool-call/user-response exclusivity remains independently evaluable."
        ),
        "diagnosis": (
            "Never infer concurrency from flattened ordering or propose serialization, "
            "waiting after every call, or single-call execution as an update. If this is the "
            "only allegation, return null / none / none / none."
        ),
        "target_fix": (
            "Do not treat flattened tool-call batching as BAD or GOOD evidence. If a target "
            "tests only that excluded behavior, classify every pair and the edit NOT_EXERCISED; "
            "otherwise evaluate only its independently testable in-scope mechanism."
        ),
    }
    if component not in consequences:
        raise ValueError(f"Unsupported v0.13 evaluation component: {component}")
    return f"{shared} {consequences[component]}"
