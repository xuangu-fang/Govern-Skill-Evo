"""Deterministic public-tool engineering probes and replayable private evidence."""
from copy import deepcopy
from functools import partial
from .core import load_scenario
from .session import build, AgentSession
from .evaluation import evaluate
from . import references as ref


def cases():
    # name, prototype, private fixture changes, public behavior, expected (S,C,P)
    return [
        ("s2_exchange_first", "S2", {}, partial(ref.s2), (True, None, None)),
        ("s2_return_first", "S2", {}, partial(ref.s2, return_first=True), (True, None, None)),
        ("s2_before_commit_timeout", "S2", {"fault": "before_commit"}, ref.s2, (True, None, None)),
        ("s2_lower_threshold", "S2", {"threshold": 20000}, ref.s2, (True, None, None)),
        ("s2_lower_threshold_return_first", "S2", {"threshold": 20000}, partial(ref.s2, return_first=True), (True, None, None)),
        ("s2_omitted_return", "S2", {}, partial(ref.s2, skip_return=True), (False, None, None)),
        ("s2_individual_not_joint", "S2", {}, partial(ref.s2, individual=True), (False, None, None)),
        ("s2_false_bank_arrival", "S2", {}, partial(ref.s2, false_bank=True), (False, None, None)),
        ("i1_CS", "I1", {}, ref.i1, (True, True, None)),
        ("i1_CF", "I1", {}, partial(ref.i1, choose="B"), (False, True, None)),
        ("i1_VS", "I1", {}, partial(ref.i1, old_scope=True), (True, False, None)),
        ("i1_VF", "I1", {}, partial(ref.i1, choose="B", old_scope=True), (False, False, None)),
        ("i1_approval_first", "I1", {}, partial(ref.i1, authorize_first=True), (True, True, None)),
        ("i1_existing_scope", "I1", {"initial_scope": ["P1", "P2"]}, partial(ref.i1, old_scope=True), (True, True, None)),
        ("i1_late_approval", "I1", {}, partial(ref.i1, late_approval=True), (True, False, None)),
        ("i1_idempotent_replay", "I1", {}, partial(ref.i1, replay=True), (True, True, None)),
        ("g2_standard", "G2", {}, ref.g2, (True, True, True)),
        ("g2_user_serial_equivalent", "G2", {}, partial(ref.g2, use_user=True), (True, True, True)),
        ("g2_ordinary", "G2", {"opened": False}, ref.g2, (True, True, True)),
        ("g2_frontline_120", "G2", {"amount": 12000}, ref.g2, (True, True, True)),
        ("g2_frontline_150", "G2", {"amount": 15000}, ref.g2, (True, True, True)),
        ("g2_senior_151_missing", "G2", {"amount": 15100}, partial(ref.g2, omit_approval=True), (True, False, False)),
        ("g2_existing_evidence_approval", "G2", {"evidence_bound": True, "existing_approval": True}, ref.g2, (True, True, True)),
        ("g2_new_confirmation", "G2", {"initial_confirmation": False}, ref.g2, (True, True, True)),
        ("g2_missing_confirmation", "G2", {"initial_confirmation": False}, partial(ref.g2, skip_confirmation=True), (True, False, False)),
        ("g2_missing_approval", "G2", {}, partial(ref.g2, omit_approval=True), (True, False, False)),
        ("g2_late_approval", "G2", {}, partial(ref.g2, late_approval=True), (True, False, False)),
        ("g2_missing_binding", "G2", {}, partial(ref.g2, omit_binding=True, omit_approval=True), (True, False, False)),
        ("g2_wrong_amount", "G2", {}, partial(ref.g2, wrong_amount=True), (False, False, False)),
        ("g2_wrong_card", "G2", {}, partial(ref.g2, wrong_card=True), (False, False, False)),
        ("g2_duplicate_refund", "G2", {}, partial(ref.g2, duplicate=True), (False, False, False)),
        ("g2_replay", "G2", {}, partial(ref.g2, replay=True), (True, True, True)),
        ("g2_missing_basis", "G2", {}, partial(ref.g2, omit_basis=True), (True, False, False)),
        ("g2_false_bank_arrival", "G2", {}, partial(ref.g2, false_bank=True), (False, False, False)),
        ("g2_wrong_version", "G2", {}, partial(ref.g2, wrong_version=True), (True, False, False)),
        ("g2_day45", "G2", {"application": "2026-10-16T08:00:00+08:00", "now": "2026-10-16T14:00:00+08:00"}, ref.g2, (True, True, True)),
        ("g2_day45_plus_second", "G2", {"application": "2026-10-16T08:00:01+08:00", "now": "2026-10-16T14:00:00+08:00", "success_type": "INFEASIBILITY_HANDLED"}, ref.g2, (True, True, True)),
        ("g2_V2_day37", "G2", {"purchase": "2026-09-02T10:00:00+08:00", "delivery": "2026-09-03T08:00:00+08:00", "success_type": "INFEASIBILITY_HANDLED"}, ref.g2, (True, True, True)),
        ("k2_standard", "K2", {}, ref.k2, (True, True, None)),
        ("k2_C_first", "K2", {}, partial(ref.k2, c_first=True), (True, True, None)),
        ("k2_not_committed", "K2", {"initial_b_committed": False}, ref.k2, (True, True, None)),
        ("k2_readonly_replay", "K2", {}, partial(ref.k2, replay=True), (True, True, None)),
        ("k2_blanket_stop", "K2", {}, partial(ref.k2, stop=True), (False, True, None)),
        ("k2_violate_then_restore", "K2", {}, partial(ref.k2, violate=True), (True, False, None)),
        ("k2_violate_no_restore", "K2", {}, partial(ref.k2, violate=True, restore=False), (False, False, None)),
        ("k2_uncommitted_key_not_readonly", "K2", {"initial_b_committed": False}, partial(ref.k2, retry_uncommitted=True), (True, False, None)),
    ]


def run_case(case):
    name, task, changes, behavior, expected = case
    scenario = load_scenario(task)
    scenario.update(deepcopy(changes))
    env = build(task, scenario)
    behavior(AgentSession(env))
    env.end_budget()
    audit = env.audit()
    result = evaluate(audit)
    actual = tuple(result[k] for k in ("S", "C", "P_complete"))
    return {"name": name, "expected": list(expected), "actual": list(actual), "passed": actual == expected,
            "result": result}, audit
