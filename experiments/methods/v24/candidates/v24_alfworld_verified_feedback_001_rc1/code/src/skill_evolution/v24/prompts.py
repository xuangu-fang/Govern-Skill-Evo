"""Context rendering is owned by the explicitly bound benchmark."""
from .benchmark import current
from .facts import require


def actor_fields(template, background):
    return current().actor_fields(template, background)


def execution_context(background):
    return current().execution_context(background)


def render_prompt(template, background):
    import re
    require(re.findall(r"\{\{.*?\}\}", template) == ["{{execution_context}}"],
            "Expected only one execution context placeholder")
    return template.replace("{{execution_context}}", execution_context(background))
