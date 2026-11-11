"""Current execution lists and qualified history are distinct in v29.2.

Only complete local P/Q references separated by slashes form a list. Historical
prefixes remain detectable, including history followed by a local list. The
caller still checks every extracted reference against its own evidence scope.
"""
import re

from src.skill_evolution.v27.contracts.grouping import references as parent_references

_LOCAL = r'[PQ]\d+(?::[A-Za-z0-9_]+)?'
_LIST = re.compile(r'\b' + _LOCAL + r'(?:/' + _LOCAL + r')+\b')
_HISTORY = re.compile(r'\b[A-Za-z0-9_-]+/(?:diff|' + _LOCAL + r')\b')


def references(value):
    lists = [match.span() for match in _LIST.finditer(value)]
    historical = {match[0] for match in _HISTORY.finditer(value)
                  if not any(start <= match.start() and match.end() <= end
                             for start, end in lists)}
    return (parent_references(value) |
            set(re.findall(r'\bQ\d+(?::[A-Za-z0-9_]+)?\b', value)) | historical)
