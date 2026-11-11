"""Deterministic Actor prompt rendering, also used to audit recorded requests."""


def visible_commands(commands):
    """Preserve order, whitespace and duplicates; hide only the exact help action."""
    return [command for command in commands if command != "help"]


def render_messages(observation, admissible, goal, history, *, system_prompt,
                    initial_template, history_template):
    actions = "\n ".join(f"'{action}'" for action in visible_commands(admissible))
    if not history:
        user = initial_template.format(current_observation=observation, admissible_actions=actions)
    else:
        offset = len(history) - min(2, len(history))
        lines = [f"[Observation {offset + i + 1}: '{entry['observation']}', Action {offset + i + 1}: '{entry['action']}']"
                 for i, entry in enumerate(history[-2:])]
        user = history_template.format(
            task_description=goal, step_count=len(history), history_length=min(2, len(history)),
            action_history="\n".join(lines), current_step=len(history) + 1,
            current_observation=observation, admissible_actions=actions)
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]
