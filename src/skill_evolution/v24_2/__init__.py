"""ALFWorld direct diagnosis, per-Update editing and event-based selection."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = Path(__file__).with_name('prompts')
STAGES = ('diagnosis', 'preconditioner', 'editor', 'replay')
DOMAIN_GUIDE = PROMPTS / 'alfworld_domain.md'


def system_prompt(stage):
    """Resolve the module's domain excerpts, leaving quoted Actor templates verbatim."""
    chunks = re.split(r'^## (.+)\n', DOMAIN_GUIDE.read_text(), flags=re.MULTILINE)
    sections = dict(zip(chunks[1::2], (body.strip() for body in chunks[2::2])))
    template = (PROMPTS / (stage + '.md')).read_text()
    return re.sub(r'^\{\{domain: ([^{}\n]+)\}\}$', lambda match: sections[match[1]],
                  template, flags=re.MULTILINE)
