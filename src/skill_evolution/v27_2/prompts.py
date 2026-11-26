"""Read a versioned method prompt and verify its quoted Actor contract."""
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27_1.lmb import protocol

DIRECTORY = protocol.ROOT / 'docs/methods/v27_2/prompts'


def render(name, background):
    prompt = (DIRECTORY / f'{name}.md').read_bytes().decode('utf-8')
    start, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(start) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(start)[1].split(end)[0] == protocol.actor_base_protocol(),
            f'{name}/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, f'{name}/Actor runtime differs')
    return prompt
