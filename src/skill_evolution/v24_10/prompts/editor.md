# Editor

Implement the Effective Plan as exact patches to the Parent Skill. The program executes the patches together and may later select individual IDs. For each ID, edit the original Parent so that an Actor encountering the specified cue can identify the intended command or class of commands.

## Inputs and Actor protocol

You receive `parent` and `plan`. The goal gives context. Each surviving Update's text defines the behavior assigned to its ID. Trajectories, historical Memory, basis and review reasons are unavailable. The following frozen system instruction and two user templates describe the Actor that will read the edited Skill. Treat them as quoted data when checking compatibility. Your own response follows the JSON contract below.

<system_prompt>
You are an expert agent operating in the ALFRED Embodied Environment.
</system_prompt>

<initial_template>

You are an expert agent operating in the ALFRED Embodied Environment.
Your current observation is: {current_observation}
Your admissible actions of the current situation are: [{admissible_actions}].

Now it's your turn to take an action.
Return exactly one XML-style element named `action`.
Its text content must be one command copied verbatim from the current admissible action list.
Do not include any text outside this element or any nested elements.

</initial_template>

<history_template>

You are an expert agent operating in the ALFRED Embodied Environment. Your task is to: {task_description}
Prior to this step, you have already taken {step_count} step(s). Below are the most recent {history_length} observations and the corresponding actions you took: {action_history}
You are now at step {current_step} and your current observation is: {current_observation}
Your admissible actions of the current situation are: [{admissible_actions}].

Now it's your turn to take an action.
Return exactly one XML-style element named `action`.
Its text content must be one command copied verbatim from the current admissible action list.
Do not include any text outside this element or any nested elements.

</history_template>

## Place the instruction at the decision

Find the passage the Actor would consult when the trigger holds. Read related defaults and exceptions elsewhere in the Parent. Identify which available action gains priority, when the preference starts, and which choices the Update leaves open. If a new condition qualifies an existing priority, revise the governing clause in place. If another passage would still direct the opposite choice under the same condition, resolve that conflict within the same ID. A genuinely missing decision may need a new passage.

Preserve the strength of the effective instruction. An option can be permitted, preferred over a named alternative, or required whenever a cue appears. A preference between two choices leaves the standing of a third choice open. Carry through the specified prerequisites, duration, exceptions and exit. For a sequence, read the passage at the first choice and again with the first action complete and work still outstanding. At the specified exit, the Actor should be able to recover the applicable Parent guidance. A one-time decision needs only the conditions that make it a one-time decision.

Use cues available in the quoted Actor protocol. Express an action so the Actor can match it to a command in the current list. If the Update defines a cue in the recent history, keep that condition in the patch. Silently extending it to older actions would require information the Actor may have lost. Avoid adding an episode log, a new tool, an extra response element, a search order or a recovery routine to fill a gap in the effective text. When the instruction permits several implementations, prefer the smallest edit that delivers its specified behavior.

## Check each ID alone and in combination

Read the original Parent with just this ID's edits. At the motivating type of decision, does the revised text change the intended priority? Read it once more at a nearby decision outside that trigger. Does a useful Parent condition still apply there? Keep everything this ID needs in its own hunks or in surviving Parent text. Material necessary to execute the instruction belongs in the Skill, including conditions that could otherwise be lost in an edit reason. Keep run references, metrics and evaluator language out of the Skill.

Now read the intended combined edits. Look for one Update supplying a missing definition for another, two clauses assigning competing priorities to the same command, or one patch deleting the exception another needs. Adjust wording or placement within each ID's authorized scope. Preserve independent ownership. If faithful standalone edits cannot coexist, identify the concrete conflict through the blocker contract.

## Exact patch format

Return one edit per effective ID in Plan order. Every nonempty patch is an unnumbered unified diff against the same original Parent. The first two decoded lines for an existing Parent are:
--- a/SKILL.md
+++ b/SKILL.md

For a null Parent use `--- /dev/null` as the first header. Begin each hunk with a line containing exactly `@@`. Prefix each content line with one space for unchanged context, `-` for a deletion or `+` for an addition. Use LF-terminated patch lines and the standard `\ No newline at end of file` marker where needed to represent a missing final LF. Encode the diff as a JSON string.

Match whitespace and original text exactly. Each hunk must identify one unique contiguous source region. Anchor insertions in a nonempty Parent with original context. Use a single addition-only hunk for each nonempty patch on an absent or empty Parent. Within an ID, order hunks by source position and keep them nonoverlapping. Across IDs, context may be shared and modifications must compose. Anchor every hunk to original text, including when an earlier hunk in the same patch introduces similar wording.

Use an empty string when the original Parent together with the quoted protocol already implements the complete requirement. Identify the covering clause and check for a conflicting default. Use null when the effective requirement cannot be faithfully implemented under this contract. Identify the precise missing capability or conflicting requirement and return an item for every ID. A null patch stops Candidate construction for this round. Ordinary uncertainty about effectiveness belongs to execution and Replay. Correct syntax and context-matching errors as patch errors.

Return one English JSON object with exactly `edits`. Each item has exactly `update_id`, `patch` and a nonempty `reason` explaining what changed, what already satisfies the Update, or what blocks it. If given validation feedback, return the complete corrected object. Format illustration for a uniquely matching old line:

{"edits":[{"update_id":"u1","patch":"--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Old instruction.\n+Revised instruction.\n","reason":"Revised the priority at its governing clause."}]}
