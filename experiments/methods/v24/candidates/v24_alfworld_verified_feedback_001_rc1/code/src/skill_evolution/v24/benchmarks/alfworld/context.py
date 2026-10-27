from src.skill_evolution.v24.resources import resource

import re

from src.skill_evolution.v24.facts import require

CONTEXT_PATH = resource("v23/execution_context.md")


def actor_fields(template, background):
    # Substitute only original placeholders; never reinterpret Actor template text.
    return re.sub(r"\{\{(max_steps|system_prompt|initial_template|history_template)\}\}",
                  lambda m: str(background[m[1]]), template)


def execution_context(background):
    return actor_fields(CONTEXT_PATH.read_text(encoding="utf-8"), background).rstrip()


def render_prompt(template, background):
    require(re.findall(r"\{\{.*?\}\}", template) == ["{{execution_context}}"],
            "Expected only one execution context placeholder")
    return template.replace("{{execution_context}}", execution_context(background))

