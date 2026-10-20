"""Shared execution context and explicit, read-only historical prompt rendering."""

from pathlib import Path
import re

from .facts import require


CONTEXT_PATH = Path(__file__).with_name("execution_context.md")


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


def legacy_diagnosis_system(background, templates):
    """Explicit old-protocol read only; templates are caller-supplied frozen originals.

    Current prompts never use these historical section markers. No automatic
    fallback to a stored response's prompt, and no parallel executable module.
    """
    old_grouping = actor_fields(templates["grouping"], background)
    start, end = "[Execution context]\n", "[Input data]"
    require(old_grouping.count(start) == 1 and old_grouping.count(end) == 1,
            "Invalid historical Grouping context")
    context = start + old_grouping.split(start, 1)[1].split(end, 1)[0]
    template = templates["diagnosis"]
    require(template.count("{{execution_context}}") == 1, "Invalid historical Diagnosis template")
    return template.replace("{{execution_context}}", context.rstrip())
