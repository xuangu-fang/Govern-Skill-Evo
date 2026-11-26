"""LMB prose references: bare mathematical object names are not citations.

Exact IDs in structured fields are validated by their caller. Prose recognizes
qualified execution steps, round-qualified history and typed namespace markers.
"""
import re

from src.skill_evolution.v27.facts import require
from .explicit_references import parse

POLICY = 'v27_1_explicit_prose_references_v1'
_LOCAL = r'[PQ]\d+(?::[A-Za-z0-9_]+)?'
_STEP = re.compile(r'\b[PQ]\d+:[A-Za-z0-9_]+\b')
_LIST = re.compile(r'\b' + _LOCAL + r'(?:/' + _LOCAL + r')+\b')
_HISTORY = re.compile(
    r'\b(?:[A-Za-z0-9_-]+_)?R\d+/(?:diff|' + _LOCAL + r')\b'
    r'|\b[A-Za-z0-9_-]+/[PQ]\d+:[A-Za-z0-9_]+\b')
_RANGE = re.compile(r'\b(P\d+|Q\d+):(\d+)\s*[-–—]\s*(?:(P\d+|Q\d+):)?(\d+)\b')


def references(value):
    """Extract explicit execution syntax, without inferring citations from P12."""
    refs = {m[0] for m in _STEP.finditer(value)}
    lists = list(_LIST.finditer(value))
    for match in lists:
        # An unqualified P1/P2 is also a polynomial quotient. A step-qualified
        # list explicitly declares execution syntax for all its members.
        if ':' in match[0]:
            refs.update(match[0].split('/'))
    refs.update(m[0] for m in _HISTORY.finditer(value)
                if not any(a.start() <= m.start() and m.end() <= a.end() for a in lists))
    for match in _RANGE.finditer(value):
        prefix, start, end_prefix, end = match.groups()
        require(end_prefix in (None, prefix), 'Cross-execution step range')
        start, end = int(start), int(end)
        require(0 <= start <= end <= 10000, 'Invalid step range')
        refs.update(f'{prefix}:{i}' for i in range(start, end + 1))
    return refs


def validate_prose(value, allowed, *, location):
    """Use the same permission boundary for output validation and Plan routing."""
    typed = parse(value, allowed, location=location)
    # A validated Update/Memory ID has its declared type, even when its text
    # resembles a step or historical path. Do not parse that marker twice.
    for namespace, ref in typed:
        value = value.replace(f'`{namespace}:{ref}`', ' ')
    refs = references(value)
    require(refs <= allowed.get('Evidence', set()), f'{location}: unavailable execution reference')
    return refs | {ref for namespace, ref in typed if namespace == 'Evidence'}
