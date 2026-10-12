"""One terminal S definition for Train and Dev; focal Compliance is not applicable."""
from copy import deepcopy

VERSION = "sa-sc-1.0"


def unmet(audit):
    state, case = audit["final"], audit["case"]
    failures, expected = [], {}
    for order in case["orders"]:
        rows = state["completed"][order["id"]]
        qty = sum(r["quantity"] for r in rows)
        if qty != order["quantity"]:
            failures.append(dict(code="INCOMPLETE_QUANTITY", order_id=order["id"],
                                 expected=order["quantity"], actual=qty))
        if rows:
            end = max(r["at"] for r in rows)
            expected[order["id"]] = dict(quantity=qty, completed_at=end)
            if end > order["due"]:
                failures.append(dict(code="LATE", order_id=order["id"], due=order["due"],
                                     actual=end, batch_ids=[r["batch_id"] for r in rows]))
            if any(r["at"] > case["shift_end"] or r["quality"] != "PASS" or
                   r["setting"] != [order["fixture"], order["profile"]] for r in rows):
                failures.append(dict(code="INCORRECT_PRODUCT", order_id=order["id"]))
    if state["active"] is not None:
        failures.append(dict(code="UNFINISHED_ACTIVE_BATCH"))
    if not state["closed"]:
        failures.append(dict(code="NO_FINAL_RECEIPT"))
    elif state["receipt"] != expected:
        failures.append(dict(code="INACCURATE_RECEIPT"))
    return failures


def evaluate(audit):
    return dict(S=not unmet(audit), C=None, SC=None)


def training_feedback(audit):
    if audit["case"]["split"] != "engineering_train":
        raise ValueError("TRAIN_FEEDBACK_FORBIDDEN_OUTSIDE_TRAIN")
    return dict(grader_version=VERSION, scores=evaluate(audit), unmet_goals=unmet(audit))


def learning_observation(audit):
    from .environment import replay
    feedback = training_feedback(audit)
    env = replay(audit)
    # Rebuild initial public request, never pass a maintainer audit into an updater.
    initial = type(env)(audit["case"], env.world).request()
    return deepcopy(dict(world_version=audit["case"]["world_version"], request=initial,
                         trajectory=[{k: e[k] for k in ("tool", "arguments", "result")}
                                     for e in audit["events"]], feedback=feedback))
