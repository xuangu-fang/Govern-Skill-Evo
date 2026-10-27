"""Complete synthetic review cases, not model outputs or behavioral experiments.

Human-authored decisions are witnesses of expressibility, never unique answers.
All observations/actions below are invented test data and carry no empirical claim.
"""
from copy import deepcopy

from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23.memory import empty_memory


def run(ref, initial, events, success=False):
    state = {"observation": initial, "commands_ref": None}
    result = {"ref": ref, "task": "Synthetic offline decision fixture.", "initial": deepcopy(state), "steps": []}
    for i, (action, observation) in enumerate(events, 1):
        after = {"observation": observation, "commands_ref": None}
        terminal = success and i == len(events)
        result["steps"].append({"step": f"{ref}:{i}", "before": deepcopy(state), "action": action,
                                "after": after, "feedback": {"done": terminal, "won": terminal}})
        state = after
    status = "success" if success else "step_limit"
    result["outcome"] = {"status": status, "success": success, "end_reason": status}
    return result


def pair(initial, parent, candidate, p_success=False, q_success=False):
    return initial, parent, candidate, p_success, q_success


# Each history is an actual synthetic text edit plus explicit paired observations.
SPECS = [
    dict(id="A1", title="Conditional retry", focus=["S"],
         original=["Retry immediately after every failed action.\n"],
         revised=["Avoid repeating a failed action while its visible prerequisite is unchanged and no new feedback justifies retrying; permit retry after visible prerequisite repair.\n"],
         old="Preserve the task goal.\n", new="Retry immediately after every failed action.\n",
         episodes=[pair("The drawer is locked; opening has just failed.",
                        [("wait", "The drawer remains locked.")],
                        [("open drawer", "Opening fails; the drawer remains locked."), ("open drawer", "Opening fails again; still locked.")]),
                   pair("The drawer is locked; a matching key is visible.",
                        [("unlock drawer", "The drawer is unlocked."), ("wait", "The drawer remains unlocked.")],
                        [("unlock drawer", "The drawer is unlocked."), ("open drawer", "Drawer open; required item retrieved.")], q_success=True)],
         knowledge="Immediate retry guidance accompanied repeated failures while the lock was unchanged, and successful opening after visible unlocking. These observations distinguish prerequisites; they do not validate a general repair-detection strategy.",
         reason="`M1`, `H_A1/diff`, `H_A1/Q1:2` and `H_A1/Q2:2` distinguish unchanged from repaired prerequisites. Scope the retry condition while retaining recovery; the proposed condition remains unverified.",
         reject="Permanent prohibition of all retries or an invented retry-count optimum."),
    dict(id="A2", title="Reconstruct a broad prohibition", focus=["D", "S"],
         original=["Never return to a previously visited place.\n"],
         revised=["Avoid repeat searches when current and recent observations show no new information or task progress; permit returns needed for a currently visible task prerequisite.\n"],
         old="Allow task-relevant returns.\n", new="Never return to a previously visited place.\n",
         episodes=[pair("The alcove was just searched; no new information or task need is visible.",
                        [("search alcove again", "No new information.")], [("inspect visible new shelf", "A relevant item is visible.")]),
                   pair("The parcel is carried; its labelled destination is the previously visited desk.",
                        [("return to desk", "Parcel delivered.")], [("wait elsewhere", "Parcel still carried; desk delivery pending.")], p_success=True)],
         knowledge="The blanket return prohibition accompanied less uninformative repetition but also an undelivered parcel when a required destination had been visited. It does not validate a new classifier of productive returns.",
         reason="`M1` and `H_A2/diff` show the broad intervention. `H_A2/Q1:1` shows alternative progress, while `H_A2/P2:1` and `H_A2/Q2:1` expose the lost return. Redirect the restriction; the new distinction is a hypothesis.",
         reject="List arbitrary task exceptions or add an unrelated exhaustive-search requirement."),
    dict(id="A3", title="Widen permission", focus=["S"],
         original=["Use source A only; wait when A is unavailable.\n"],
         revised=["When A is unavailable, permit a currently visible alternative whose information meets the current task requirements; verify suitability before using it.\n"],
         old="Use A only.\n", new="When A is unavailable, allow visible B if it meets the required information quality.\n",
         episodes=[pair("A is unavailable; B visibly supplies the required exact reading.",
                        [("wait for A", "A remains unavailable.")], [("read B", "The exact required reading is obtained.")], q_success=True)],
         knowledge="Permission to use visible B when A was unavailable accompanied obtaining the required exact reading. This supports a conditional opportunity, not universal source interchangeability or a mandatory preference for B.",
         reason="`M1`, `H_A3/diff` and `H_A3/Q1:1` motivate widening permission when an alternative satisfies the visible requirement. Other alternatives remain untested; retain suitability checks.",
         reject="Always prefer B or discard the information-quality requirement."),
    dict(id="A4", title="Coordinate conflicting Updates", focus=["S", "C"],
         original=["Retry after completing preparation.\n", "Abandon an action after any failure.\n"],
         revised=["After preparation, recheck currently visible prerequisites and retry if ready.\n",
                  "Avoid retrying a failed action while its prerequisite remains unmet; permit retry after visible repair and a readiness check.\n"],
         old="Abandon an action after any failure.\n", new="Abandon an action after any failure.\nRetry after repairing its prerequisite.\n",
         episodes=[pair("Opening failed because the latch is engaged; latch release is visible.",
                        [("wait", "Latch still engaged; no opening attempted.")],
                        [("release latch", "Latch visibly released."), ("wait", "Latch released; opening still not attempted.")])],
         knowledge="A repair-and-retry clause was added alongside an unconditional abandonment clause. After visible repair no retry occurred. The joint instructions conflict, but the observation does not isolate which clause caused waiting.",
         reason="`M1`, `H_A4/diff` and `H_A4/Q1:2` motivate resolving the conflict between `u1` and `u2`. Coordinate conditional retry and readiness checking; the joint observation does not establish an isolated clause effect.",
         reject="Change only the retry clause while retaining unconditional abandonment."),
    dict(id="A5", title="Keep addresses the counterexample", focus=[],
         original=["Avoid repeating a failed action only while its prerequisite is unchanged and there is no new feedback; allow retry after visible repair.\n"],
         revised=None, old="Retry after repairing the prerequisite.\n", new="Never retry after any failure.\n",
         episodes=[pair("The earlier failed opening had a locked latch; it is now visibly unlocked.",
                        [("open", "Opened successfully.")], [("wait", "Still unlocked; task unfinished.")], p_success=True)],
         knowledge="A permanent retry prohibition accompanied waiting despite a visibly repaired prerequisite, whereas the earlier repair-conditioned guidance was followed by successful opening. This observation concerns a broader restriction than an unchanged-prerequisite condition.",
         reason="`M1`, `H_A5/diff` and `H_A5/Q1:1` concern permanent prohibition after visible repair. The current `u1` already permits that case; the historical counterexample does not require this modification. KEEP is not evidence of effectiveness.",
         reject="Ignore the counterexample with a generic insufficient-evidence statement."),
    dict(id="A6", title="Explore without inventing historical proof", focus=["D", "S"],
         original=["Exhaust the current branch before switching.\n"],
         revised=["When the most recent attempt adds no task-relevant information and a visible alternative can advance the goal, permit switching without exhausting the current branch; keep unfinished useful branches eligible for return.\n"],
         old="Exhaust the current branch before switching.\n", new="Permit switching to another visible branch.\nPermanently discard the previous branch after switching.\n",
         episodes=[pair("The latest shelf search yielded nothing; another visible shelf has a relevant clue.",
                        [("search same shelf", "No new information.")], [("inspect alternative shelf", "A useful clue is obtained.")]),
                   pair("One useful item remains on the current shelf; a second shelf is visible.",
                        [("take current item", "Useful item retained.")], [("switch shelf", "Previous useful item remains uncollected.")])],
         knowledge="Joint switching permission and permanent branch abandonment accompanied progress at a visible alternative and omission of an uncollected item elsewhere. The observations do not isolate switching effects or establish an optimal stopping threshold.",
         reason="`M1`, `H_A6/diff`, `H_A6/Q1:1` and `H_A6/Q2:1` motivate exploring a switch while preserving useful unfinished branches. The selected most-recent-attempt trigger is a new unverified choice, not a historically optimal threshold.",
         reject="Hide a threshold only in the Patch or claim an optimal ordering from joint edits."),
    dict(id="A7", title="Reject attribution to an unimplemented edit", focus=[],
         original=["When a failed action has an unmet visible prerequisite, repair it before retrying.\n"],
         revised=None, old="Preserve task completion.\n", new="Preserve the current task goal and completion.\n",
         episodes=[pair("Opening has failed; the latch is visibly engaged.",
                        [("open", "Opening fails; latch unchanged.")], [("open", "Opening fails; latch unchanged.")])],
         knowledge="Only goal wording changed; the intended repair-before-retry guidance was absent from the actual edit. Both executions repeated an opening with an engaged latch. This is not evidence of the proposed repair guidance's effect.",
         suspect="Repair-before-retry guidance caused repeated opening failures.",
         reason="The attribution in `M1` is contradicted by `H_A7/diff`: only goal wording changed. `H_A7/Q1:1` therefore cannot establish harm from the proposed repair rule. Current `P1:1` leaves the actionable proposal reasonable but unverified.",
         reject="Treat intended guidance as implemented or claim that missing intervention proves harmlessness."),
    dict(id="A8", title="Withdraw redundancy, not uncertainty", focus=["C"],
         original=["Preserve exact target identification.\n"], revised=[],
         parent="Preserve exact target identification.\n",
         old="Preserve exact target identification.\n", new="Preserve exact target identification.\nRetain the exact target identity.\n",
         episodes=[pair("A labelled target is visible.", [("identify target", "Exact target identified.")],
                        [("identify target", "Exact target identified.")], p_success=True, q_success=True)],
         knowledge="Repeating existing target-identification guidance accompanied the same identification behavior in these observations. The evidence does not establish a separate benefit from the duplicate wording.",
         reason="Parent already states the complete target-identification requirement; `P1:1` and `P2:1` show retained identification. Withdraw the duplicate proposal while leaving Parent coverage intact; this does not justify removing unique capabilities.",
         reject="Withdraw the only coverage of a necessary behavior or disguise an inconsistent Goal as success."),
]


def materialize(spec):
    """Produce complete current input, Replay evidence, Memory and one reviewed decision."""
    cid = spec['id']
    runs, pairs = [], []
    for i, (initial, p, q, ps, qs) in enumerate(spec['episodes'], 1):
        runs.extend([run(f'P{i}', initial, p, ps), run(f'Q{i}', initial, q, qs)])
        pairs.append({'parent': f'P{i}', 'candidate': f'Q{i}'})
    diff = actual_diff(spec['old'], spec['new'])
    evidence = ['diff', *[s['step'] for r in runs for s in r['steps']]]
    learned = {'entries': [{'revises': [], 'knowledge': spec['knowledge'], 'evidence': evidence}]}
    replay = {'parent': spec['old'], 'diff': diff,
              'plan': {'goal': 'Improve task progress while preserving necessary capabilities.',
                       'updates': [{'id': 'u1', 'text': spec['new']}], 'checks': []},
              'command_sets': {}, 'runs': runs, 'pairs': pairs, 'memory': empty_memory()}
    if cid == 'A7':
        # The intended repair requirement is genuinely absent from the actual Diff.
        replay['plan']['updates'][0]['text'] = spec['original'][0]
    sources = {f'H_{cid}/diff': {'parent': spec['old'], 'diff': diff,
                               'execution_context': {'synthetic': True, 'visible_information': 'recorded state'}}}
    sources.update({f'H_{cid}/{r["ref"]}': {'run': deepcopy(r), 'command_sets': {}} for r in runs})
    history = {'entries': [{'id': 'M1', 'knowledge': spec.get('suspect', spec['knowledge']),
                            'evidence': [f'H_{cid}/{r}' for r in evidence]}], 'sources': sources}
    # Current evidence keeps complete decision states and a preservation example.
    current = [deepcopy(runs[0]), deepcopy(runs[-1])]
    for i, r in enumerate(current, 1):
        r['ref'] = f'P{i}'
        for j, step in enumerate(r['steps'], 1): step['step'] = f'P{i}:{j}'
    updates = [{'id': f'u{i}', 'text': value, 'basis': ['G1', 'P1:1', 'P2:1']}
               for i, value in enumerate(spec['original'], 1)]
    checks = [{'id': 'c1', 'update_ids': [u['id'] for u in updates],
               'question': 'Does task progress improve while necessary capabilities remain available?'}]
    payload = {'parent': spec.get('parent', 'Preserve task completion and necessary recovery.\n'),
               'plan': {'goal': 'Improve task progress while preserving necessary capabilities.',
                        'updates': updates, 'checks': checks},
               'command_sets': {}, 'runs': current,
               'grouping': {'groups': [{'group_id': 'G1', 'members': ['P1', 'P2'],
                   'decision_problem': spec['title'], 'shared_basis': 'P1:1 and P2:1 expose relevant choices.',
                   'important_differences': ['Compare the recorded prerequisites and outcomes.']}]},
               'memory': history}
    adjustments = []
    for i, u in enumerate(updates):
        if spec['revised'] is None:
            change, to = 'KEEP', None
        elif spec['revised'] == []:
            change, to = 'Withdraw this redundant proposal; preserve the equivalent requirement in Parent.', []
        else:
            change = spec['revised'][i].strip()
            to = {'patch': actual_diff(u['text'], spec['revised'][i])}
        adjustments.append({'target': u['id'], 'focus': spec['focus'], 'change': change,
                            'reason': spec['reason'], 'to': to})
    return {'id': cid, 'synthetic': True, 'payload': payload, 'replay_payload': replay,
            'replay_output': learned, 'output': {'adjustments': adjustments,
                                               'checks': [] if spec['revised'] == [] else None},
            'unacceptable': spec['reject']}


def cases():
    return [materialize(spec) for spec in SPECS]
