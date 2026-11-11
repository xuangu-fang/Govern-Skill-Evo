"""v29.2 citation syntax shared by Preconditioner and Replay.

Outside code spans, a namespace followed by colon and whitespace is prose, even
when the following word happens to be an ID. Compact namespace:ID expressions
are citations and require exactly one enclosing backtick on each side. Inside
code spans, reserved namespace prefixes must form an exact authorized citation.
Each caller supplies its own permissions. Diagnosis retains its existing rules.
"""
import re

from src.skill_evolution.v27.facts import require, text

_NAMES = r'(?:Memory|Group|Evidence|Update|Check)'
_PREFIX = re.compile(r'(?<!\w)' + _NAMES + r'\s*:')
_COMPACT = re.compile(r'(?<!\w)' + _NAMES + r'[ \t]*:(?=\S)[^\s`]*')
_CODE = re.compile(r'(`+)([^`]*)(`+|$)')
_EXACT = re.compile(r'(' + _NAMES + r'):([^\s`]+)')


def parse(value, allowed, *, location):
    """Return typed IDs; keep syntax failures separate from permission failures."""
    text(value, location)
    refs, spans = [], []

    def fail(offset, token, reason):
        require(False, f'{location}: text character {offset + 1} (1-based), '
                       f'token {token[:100]!r}: {reason}')

    for match in _CODE.finditer(value):
        spans.append((match.start(), match.end()))
        opening, body, closing = match.groups()
        if not _PREFIX.search(body):
            continue
        exact = _EXACT.fullmatch(body)
        if opening != '`' or closing != '`' or exact is None:
            fail(match.start(), match[0],
                 'explicit references require one complete single-backtick marker '
                 'with no internal whitespace, for example `Update:u1`')
        namespace, ref = exact.groups()
        if namespace not in allowed or ref not in allowed[namespace]:
            fail(match.start(), match[0], 'invalid or unavailable explicit reference')
        refs.append((namespace, ref))

    for match in _COMPACT.finditer(value):
        if not any(start <= match.start() < end for start, end in spans):
            fail(match.start(), match[0],
                 'bare explicit reference requires one complete single-backtick marker; '
                 'ordinary prose labels use a space after the colon')
    return refs
