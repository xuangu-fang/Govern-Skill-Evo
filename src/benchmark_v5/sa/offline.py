"""Offline evidence checks; no transport, model calls, or Skill updates."""
from functools import lru_cache
from itertools import product

from .environment import Environment, replay
from .evaluation import evaluate, learning_observation
from .fixtures import development, training_fixture, training_plan
from .rules import World, hypotheses


class Client:
    """Pass only this callable into public-information policies, not an Environment."""
    def __init__(self, call):
        self.call = call
        self.sequence = 0

    def __call__(self, name, **arguments):
        if name not in ("read_status", "read_recipes", "read_log"):
            arguments["operation_id"] = f"op{self.sequence}"
            self.sequence += 1
        result = self.call(name, arguments)
        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(f"{name}: {result['error']}")
        return result


def complete_batch(client, allocations, batch_id):
    s = client("read_status")
    orders = {o["id"]: o for o in s["orders"]}
    ready = max(orders[k]["release"] for k in allocations)
    if ready > s["now"]:
        client("wait_until", minute=ready)
    client("draft_batch", batch_id=batch_id, allocations=allocations)
    result = client("start_batch", batch_id=batch_id)
    while result["phase"] in ("SETUP", "READY"):
        result = client("advance")
    return result


def finish(client):
    s = client("read_status")
    receipt = {key: dict(quantity=sum(x["quantity"] for x in rows),
                         completed_at=max(x["at"] for x in rows))
               for key, rows in s["completed"].items() if rows}
    client("read_log")
    client("finish", receipt=receipt)


def execute_plan(case, plan, world=None):
    env = Environment(case, world)
    client = Client(env.call)
    for index, allocation in enumerate(plan):
        result = complete_batch(client, allocation, f"b{index}")
        if result["phase"] == "INTERRUPTED":
            break
    finish(client)
    return env.audit()


def feasible_plan(case, world):
    """Maintainer truth solver. Enumerates legal partial batches, NOT an S0 agent.

    Earliest start for a chosen batch dominates delay in this stable world;
    waiting for future releases is included when a batch uses such material.
    """
    orders = case["orders"]
    settings = [(o["fixture"], o["profile"]) for o in orders]
    groups = sorted(set(settings))
    # Earliest deadline first is only search ordering; all legal choices are explored.
    groups.sort(key=lambda s: min(o["due"] for o, k in zip(orders, settings) if k == s))

    @lru_cache(None)
    def solve(remaining, now, setting, previous):
        if not any(remaining):
            return ()
        if any(q and orders[i]["due"] < now for i, q in enumerate(remaining)):
            return None
        for target in groups:
            choices = [range(min(q, case["capacity"]) + 1) if s == target else (0,)
                       for q, s in zip(remaining, settings)]
            quantities = sorted(product(*choices), key=lambda a: (-sum(a), a))
            for allocation in quantities:
                quantity = sum(allocation)
                if not 0 < quantity <= case["capacity"]:
                    continue
                indices = [i for i, q in enumerate(allocation) if q]
                start = max([now] + [orders[i]["release"] for i in indices])
                setup, process = world.durations(setting, target, quantity, previous, 6)
                end = start + setup + process
                if end > case["shift_end"] or any(end > orders[i]["due"] for i in indices):
                    continue
                tail = solve(tuple(q-a for q, a in zip(remaining, allocation)), end, target, True)
                if tail is not None:
                    return ({orders[i]["id"]: allocation[i] for i in indices},) + tail
        return None

    plan = solve(tuple(o["quantity"] for o in orders), 0, tuple(case["initial"]), False)
    return list(plan) if plan is not None else None


def public_policy(call, strategy):
    """Deterministic heuristics get tool responses only; no world/model family input.

    Re-read after every batch, including real release/remaining/setting changes.
    This does not claim to enumerate every possible adaptive strategy.
    """
    client = Client(call)
    recipe_minutes = client("read_recipes")["recipe_minutes"]
    index = 0
    while True:
        s = client("read_status")
        pending = []
        for order in s["orders"]:
            left = order["quantity"] - sum(x["quantity"] for x in s["completed"][order["id"]])
            if left:
                pending.append({**order, "left": left})
        if not pending or s["now"] >= s["shift_end"]:
            break
        ready = [o for o in pending if o["release"] <= s["now"]]
        if not ready:
            client("wait_until", minute=min(o["release"] for o in pending))
            continue
        if strategy == "setting_first":
            ready.sort(key=lambda o: ([o["fixture"], o["profile"]] != s["setting"], o["due"]))
        else:
            ready.sort(key=lambda o: o["due"])
        if strategy == "buffered_setting":
            # White-box red-team heuristic, not fitted business truth: estimate each
            # batch at 1.5x published recipe time and a change at one recipe time.
            # Prefer current setup only when this rough two-batch lookahead fits.
            current = next((o for o in ready if [o["fixture"], o["profile"]] == s["setting"]), None)
            if current is not None and s["now"] + 4 * recipe_minutes <= ready[0]["due"]:
                ready.remove(current)
                ready.insert(0, current)
        seed = ready[0]
        amount = min(seed["left"], s["capacity"])
        if strategy == "one_carrier":
            amount = 1
        allocation = {seed["id"]: amount}
        if strategy != "separate_orders" and strategy != "one_carrier":
            others = pending if strategy == "wait_to_fill" else ready
            for o in sorted(others, key=lambda o: o["due"]):
                if o["id"] != seed["id"] and (o["fixture"], o["profile"]) == (seed["fixture"], seed["profile"]):
                    added = min(o["left"], s["capacity"] - sum(allocation.values()))
                    if added:
                        allocation[o["id"]] = added
        result = complete_batch(client, allocation, f"b{index}")
        index += 1
        if result["phase"] == "INTERRUPTED":
            break
    finish(client)


def observed_batches(observation):
    """Consume only an exported Train projection, never an audit's world or state."""
    logs = next(e["result"] for e in reversed(observation["trajectory"]) if e["tool"] == "read_log")
    setups = {r["batch_id"]: r for r in logs if r["kind"] == "setup"}
    result = []
    for r in logs:
        if r["kind"] == "processing":
            s = setups[r["batch_id"]]
            result.append(dict(batch_id=r["batch_id"], before=s["before"], after=r["setting"],
                quantity=sum(r["allocations"].values()), previous_batch=s["previous_batch"],
                recipe_minutes=r["recipe_minutes"], setup=s["end"]-s["start"], process=r["end"]-r["start"]))
    return result


def compatible(observations):
    return [w for w in hypotheses() if all(w.durations(o["before"], o["after"], o["quantity"],
        o["previous_batch"], o["recipe_minutes"]) == (o["setup"], o["process"]) for o in observations)]


def validate():
    train = execute_plan(training_fixture(), training_plan())
    projection = learning_observation(train)
    observations = observed_batches(projection)
    candidates = compatible(observations)
    if candidates != [World()]:
        raise AssertionError("REFERENCE_WORLD_NOT_IDENTIFIED_IN_DECLARED_FAMILY")
    counts = [len(compatible(observations[:i])) for i in range(len(observations)+1)]
    ablations = {
        "without_joint_changes": [o for o in observations if not
            (o["before"][0] != o["after"][0] and o["before"][1] != o["after"][1])],
        "without_falling_transition": [o for o in observations if not
            (o["before"][1] == "high" and o["after"][1] == "low")],
    }
    traces = {"authorized_history": train}
    rows = []
    for case in development():
        plan = feasible_plan(case, World())
        if plan is None:
            raise AssertionError("INFEASIBLE_FIXTURE: " + case["id"])
        audit = execute_plan(case, plan)
        if not evaluate(audit)["S"]:
            raise AssertionError("REFERENCE_PLAN_FAILED: " + case["id"])
        key = case["id"]
        traces[key+"__reference"] = audit
        scores = {}
        for strategy in ("earliest_due", "setting_first", "separate_orders", "wait_to_fill", "one_carrier", "buffered_setting"):
            env = Environment(case)
            public_policy(env.call, strategy)
            traces[key+"__"+strategy] = env.audit()
            scores[strategy] = evaluate(env.audit())
        # A wrong but plausible pre-experience law; not an LLM baseline.
        guessed = World(fall_minutes=4)
        guessed_plan = feasible_plan(case, guessed)
        if guessed_plan is not None:
            guessed_audit = execute_plan(case, guessed_plan)
            traces[key+"__wrong_hypothesis"] = guessed_audit
            scores["wrong_hypothesis"] = evaluate(guessed_audit)
        else:
            scores["wrong_hypothesis"] = None
        rows.append(dict(case_id=key, reference_plan=plan, reference=evaluate(audit), policies=scores))
    for trace in traces.values():
        replay(trace)
    policy_totals = {name: sum(row["policies"][name] is not None and row["policies"][name]["S"]
                              for row in rows) for name in rows[0]["policies"]}
    return dict(version="sa-offline-0.1", classification="synthetic_white_box_engineering_not_model_results",
        model_calls=0, fixtures=len(rows), trace_count=len(traces), all_replayed=True,
        policy_successes=policy_totals,
        decision="engineering_anchor_only_current_fixtures" if any(
            value == len(rows) for name, value in policy_totals.items() if name != "wrong_hypothesis")
            else "candidate_pending_real_agent_calibration",
        identifiability=dict(family_size=len(hypotheses()), history_batches=len(observations),
            survivor_counts=counts, survivors=[w.record() for w in candidates],
            ablation_survivors={k: len(compatible(v)) for k, v in ablations.items()},
            scope="Declared 64 models only; not arbitrary functions or real-factory identification"),
        outcomes=rows), traces, projection
