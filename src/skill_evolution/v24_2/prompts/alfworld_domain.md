# ALFWorld domain guidance

The module templates select sections by their headings. The cleaning example illustrates how to read evidence; it supplies no evidence for a current Update.

Three sentences are retained verbatim from SkillAdam: “Focus on actions, environment feedback, and the causal chain.” ([trajectory interpretation](../../../../external/SkillAdam/skilladam/benchmarks/alfworld/prompts/trajectory_compress_system.md)), “There is no partial credit.” ([metric](../../../../external/SkillAdam/skilladam/benchmarks/alfworld/prompts/metric_interpretation.md)), and “Prefer operational guidance grounded in repeated trajectory evidence.” ([writing policy](../../../../external/SkillAdam/skilladam/benchmarks/alfworld/prompts/skill_writing_policy.md)). The remaining text adapts these sources, the [failure types](../../../../external/SkillAdam/skilladam/benchmarks/alfworld/prompts/failure_types.md), and the V24.2 Actor protocol. This preamble is for reviewers.

## Household goal

Read the goal for the requested object, how many distinct objects are needed, any required treatment or examination, and the destination when one is specified. Distinguish ordinary placement, placement after heating, cooling or cleaning, examination under a light, and delivery of two objects. Use the task type to identify the prerequisites that matter in this episode. For example, placing one object can complete one task and leave a two-object task unfinished.

## Decision and feedback

Focus on actions, environment feedback, and the causal chain.

Locate the earliest observable decision relevant to the explanation. During search, distinguish revisiting a location after its state changed from cycling through the same locations without progress. During acquisition, check whether the requested object was visible and reachable, whether the Actor selected the right object, and what happened when it tried to take it. For a required treatment, distinguish skipping the operation, choosing an unsuitable appliance or command, and attempting the operation without confirmed success. At delivery or examination, check the required destination, object state, quantity, or light condition against the recorded feedback.

## Cleaning example

For example, two failed cleaning tasks may call for different explanations. An Actor that carried the untreated object straight to its destination bypassed the treatment stage. An Actor that reached the sink and repeatedly received ineffective feedback reached that stage but failed to complete the operation. Use only the distinctions supported by the supplied steps.

## Actor-visible evidence

Read each run in step order. To judge an action, use its explicit `before` state when present. When omitted, the complete pre-action state (observation and `commands_ref`) equals `initial` for the first step or the immediately preceding step's `after` in the same run. Each step's own `after` is the result of its action, even when the observation repeats. Resolve Parent and Candidate runs separately.

At a decision, the Actor has the task, current observation, current action candidates, and at most the two most recent pre-action observation/action pairs. The Skill is fixed within the episode. Use the information available at that step to interpret the choice, and the subsequent environment feedback to establish its observed effect. A listed command identifies an available choice. The executed action and its feedback establish what was attempted and what followed. Treat a missing command-list reference as unavailable evidence.

When assessing search or recovery, establish what changed: the current location, a receptacle opening, an object being acquired, a treatment being confirmed, or a placement succeeding. Preserve progress that is supported by the trace. A necessary revisit can be appropriate after a state change. A location missing from the recent history has unknown visit status.

## Task completion

Use the recorded environment success flag for whole-task completion. There is no partial credit. A confirmed intermediate action can still locate a behavioral change. For example, a successful cleaning action followed by placement at the wrong destination establishes progress on treatment and failure on the whole task. Use the recorded termination reason to distinguish normal step-limit failure from an interrupted or technically incomplete execution.

## Reusable correction

Prefer operational guidance grounded in repeated trajectory evidence. A single clear case can support a scoped correction. State the observable condition, the action choice it changes, and any supported exception. A reusable object-location prior or search preference needs evidence that the relationship transfers; one object found in one receptacle supports an observation about that episode.

## Skill wording

Express the authorized behavior in terms the Actor can apply across episodes. Keep necessary object roles, appliance types, action conditions, and priorities. Omit case IDs, game paths, raw observation dumps, literal instance numbers from individual episodes, gold actions, provider details, metrics, and Gate terminology from the deployed Skill.
