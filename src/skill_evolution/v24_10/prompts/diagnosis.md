# Diagnosis

Read the complete batch of ALFWorld Parent executions and propose changes to the Skill that the Actor could use on another episode. A change may improve completion or remove substantial, avoidable work from a successful route. Your output is the Original Plan. The Preconditioner will receive the Parent, the Plan and the complete runs selected by its references. Candidate executions and historical Memory are unavailable at this stage.

## Locate the opportunity

Read the goal and the outcome of each run, then follow what happened to the outstanding requirements. A useful starting question is what the Actor did immediately after an apparently reasonable action. Did that action establish a prerequisite, reveal a new option, leave the situation unchanged, or undo earlier progress? In a successful run, identify the observation that let the Actor proceed. In a failed run, trace the unmet requirement back to the earliest choice at which the Skill could plausibly have helped.

Consider the opportunities that the batch actually presents. These can include choosing between available commands, recognizing a newly satisfied condition, continuing after an uninformative observation, or leaving a phase in time to finish the task. A return to a previously visited place can advance a different requirement. Use the actions and subsequent observations to decide what work was repeated and what work was necessary. A normal step limit establishes that the run ended before completion. A technical interruption leaves completion unresolved. Neither outcome alone identifies a decision to edit.

Read the goal for the target object, quantity, required state or interaction, and destination, as applicable. Once the Actor finds an object, trace which requirements its actions and the environment's responses establish and which remain open. Did it select the requested object? What feedback confirms a required change of state? Which interaction or placement would satisfy the remaining goal? Follow the requirements of this episode. For example, examining an object under a light can be the final interaction.

At a discrepancy, check whether the Parent leaves the choice open, favors an action that works against the goal, gives competing priorities, or already directs the appropriate action. A comparable successful decision can help distinguish these explanations. Propose an Update when you can identify how revised wording would change a priority at a choice the Actor could make.

For example, suppose the goal names a mug, the menu offers commands to take either a mug or a cup, and the Actor takes the cup. If the Parent clearly prioritizes the named object, that single error gives no reason to repeat the instruction. If a general instruction to take any available object also applies, check whether it leaves both commands equally acceptable. Clarifying which instruction takes precedence may then change the choice.

## Reconstruct the Actor's choice

Use the step's pre-action state. When a step omits `before`, use the preceding step's `after` in that run, or the run's `initial` state at the first step. Resolve `commands_ref` through the supplied `command_sets`. A missing menu leaves the availability of an alternative unknown. Distinguish the goal in the initial observation, the goal and step count in later requests, the current observation and command list, and up to two preceding observation/action pairs. Older observations, earlier menus, feedback fields, the eventual outcome and your notes on the whole run do not travel with the Actor. It chooses one command from the current list on each turn.

At a motivating step, identify the recorded command, an available alternative or set of alternatives, and the cue by which the Actor could choose between them. Read the relevant Parent passages together. Does the Parent already order those options? Does one passage authorize an action that another passage discourages at the same step? Would following the advice as written still admit the recorded choice? Describe the smallest difference a revision would make. An observed departure from a clear instruction can be worth investigating, especially if it recurs. Repeating the instruction verbatim gives the next Actor the same decision.

Separate what you observed from what you predict. A later discovery can explain a detour in hindsight. To propose a different route, identify information available before the discovery that would favor the alternative. When several options are indistinguishable with respect to the hidden target, a consistent ordering can still be a useful hypothesis if the current runs show costly switching and the ordering can be reconstructed from the visible options. State which choice it resolves and what remains uncertain. Never promise the location of an unseen object or the outcome of an unexecuted action.

## Follow the proposed behavior through the run

For a recurring preference, take its actual wording to a later recorded opportunity. Rebuild that window independently. What does the wording favor now, after one reasonable action has left work outstanding? Can the Actor still identify the relevant object, task phase or option? Which visible change would release the preference? A rule can avoid immediately undoing the previous action and still permit a longer cycle. Check whether the proposed difference addresses the work you cited. If only the first choice is supported, limit the proposal to that choice or explain the remaining uncertainty.

For example, a reviewer can mark every location visited in an episode. At a later decision the menu may list several reachable locations, with visits to each outside the visible history. Which observation or command distinguishes their visit status now? A proposed preference for an unvisited location needs an answer at the time it applies. A weaker preference can be worth proposing if it distinguishes visible options, changes the Parent's choice and addresses an evidenced cost. Apply the same test to any proposed rule about prior progress, sequence or elapsed work. This example supplies a way to examine evidence, not a search policy to add to the Skill.

For a one-time change, examine its opportunity and the next phase. Check whether the observation after the recorded action established the intended progress and whether the proposed wording would interfere with a remaining requirement. Use a comparable successful choice or another boundary case when one is available. Explain material differences between the cases. One well-observed case can support a scoped proposal. Do not manufacture recurrence, require a successful twin, or turn a case-specific discovery into a default.

## Write the Original Plan

Prioritize by the requirement at stake, the extent or recurrence of the avoidable work, the clarity of the behavioral difference from Parent, and the evidence for transfer. Give independent decisions separate IDs. Keep a trigger with its own action, prerequisite and exit when separating them would authorize a different behavior. There is no target number of Updates. Use `no_change` when the batch supports no actionable difference.

Put the task-visible condition, changed preference, its strength, and any necessary continuation or exception in `text`. Use wording the Editor could implement without access to your thought process. Keep run-specific objects, episode discoveries and score claims out of that instruction. Use `reason` to explain why the selected differences matter, citing recorded decisions and acknowledging a consequential gap. In each Update's `basis`, include the exact supplied run or step references for the motivating choice and any continuation, success or counterexample on which its scope depends. A run mentioned only in `reason` may never reach the reviewer.

Return one English JSON object with exactly `decision`, `reason` and `plan`. For `revise`, supply a nonempty goal and at least one Update with a unique ID, complete nonempty text and nonempty basis. For `no_change`, give the reason and a null plan. Use only references available in this request. If given validation feedback, return the complete corrected object.

{"decision":"revise","reason":"...","plan":{"goal":"...","updates":[{"id":"u1","text":"...","basis":["P1:3"]}]}}
{"decision":"no_change","reason":"...","plan":null}
