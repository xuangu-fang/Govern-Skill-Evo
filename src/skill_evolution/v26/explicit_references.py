"""Preconditioner-only prose citations; stored IDs and evidence scope stay unchanged."""
import re

from .facts import require, text
from .contracts.memory import run_references
from .memory_view import historical_references, knowledge_only


NAMESPACES = ('Memory', 'Group', 'Evidence', 'Update', 'Check')
MARKER = re.compile(r'(?<!\w)(?:' + '|'.join(NAMESPACES) + r')\s*:')
SPAN = re.compile(r'(?<!`)`([^`\n]+)`(?!`)')


def permissions(payload, checks, *, memory_contract):
    """Only model-visible references, including inherited Group provenance."""
    groups = {g['group_id'] for g in payload['grouping']['groups']}
    inherited = {r for u in payload['plan']['updates'] for r in u['basis']}
    current = {r for run in payload['runs'] for r in run_references(run)}
    historical = historical_references(knowledge_only(payload['memory'], memory_contract=memory_contract))
    return {
        'Memory': {e['id'] for e in payload['memory']['entries']},
        'Group': groups & inherited,
        'Evidence': current | historical,
        'Update': {u['id'] for u in payload['plan']['updates']},
        'Check': {c['id'] for c in [*payload['plan']['checks'], *checks]},
    }


def parse(value, allowed, *, location):
    """Return typed exact IDs, never interpreting bare IDs or ordinary code spans.

    Namespace prefixes are reserved in output prose. Once used they must form a
    complete single-backtick citation; broken markers must not silently vanish.
    """
    text(value, location)
    refs = []

    def check(match):
        body = match[1]
        if not MARKER.search(body):
            return match[0]
        namespace, separator, ref = body.partition(':')
        require(separator and namespace in allowed and ref in allowed[namespace],
                f'{location}: invalid or unavailable explicit reference {body!r}')
        refs.append((namespace, ref))
        return ' ' * len(match[0])

    remainder = SPAN.sub(check, value)
    require(not MARKER.search(remainder),
            f'{location}: explicit references require one complete single-backtick marker')
    return refs
