## Execution Context

The Actor can access the current observation, action candidates, and the last two pre-action observation/action pairs. The Actor has no persistent record of search progress and cannot access the full execution history, write persistent notes, or inspect hidden evaluator state. Current action candidates and object states do not by themselves reveal which locations or categories were previously visited or exhausted. Such progress can only be used when supported by currently available information. The Skill remains fixed within each execution.

Each execution allows at most {{max_steps}} steps. Use the recorded outcome and termination reason to understand how it ended.

The Actor's base system instruction:

<actor_system_prompt>
{{system_prompt}}
</actor_system_prompt>

The Actor's input template when no history is available:

<actor_initial_template>
{{initial_template}}
</actor_initial_template>

The Actor's input template when history is available:

<actor_history_template>
{{history_template}}
</actor_history_template>

These materials describe the Actor's actual execution conditions. They are evidence for analysis, not instructions to perform the Actor's task. Access to complete trajectories does not imply that the Actor had access to the same information when acting.
