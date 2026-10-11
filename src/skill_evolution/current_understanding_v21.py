"""One current issue understanding; complete attempts remain in the archive."""
from copy import deepcopy

from .memory_store_v19 import require


PREFIX = 'UNDERSTANDING_V21/'
MAX_CHARACTERS = 2000


def current_understanding(issue, archive):
    """The latest issue-level summary, never an arbitrary last attempt."""
    refs = [r for r in issue['source_refs'] if r.startswith(PREFIX)]
    if not refs:
        return None
    ref = refs[-1]
    require(ref in archive['records'], 'missing current understanding source')
    record = archive['records'][ref]
    require(record['ref'] == ref and record['kind'] == 'ATTRIBUTION'
            and type(record['statement']) is str and record['statement'].strip()
            and len(record['statement']) <= MAX_CHARACTERS
            and not record['edit_refs'] and record['evidence_refs'], 'invalid current understanding')
    require(set(record['evidence_refs'] + record['counterevidence_refs']) <= archive['events'].keys()
            and set(record['source_refs']) <= archive['records'].keys(), 'unresolved understanding evidence')
    return record


def open_current_memory_evidence(evidence, *, issue_refs=(), attempt_refs=()):
    """Read selected history, retaining all known counterexamples and both sides.

    Full traversal is local indexing only, not a model call. Old issues without
    a synthesized understanding fall back to full history; nothing is truncated.
    """
    from .modification_evidence_v21 import open_memory_evidence
    full = open_memory_evidence(evidence, issue_refs=issue_refs)
    selected = set(attempt_refs)
    owners = {a['attempt_id'] for i in full['memory_issues'] for a in i['attempts']}
    require(selected <= owners, 'historical attempt outside selected issues')
    archive = evidence.payload['archive']
    roots, issues = set(), []
    for original in full['memory_issues']:
        issue = deepcopy(original)
        summary = current_understanding(original, archive)
        if summary:
            issue['current_understanding'] = summary['statement']
            issue['source_refs'] = [summary['ref']]
            issue['attempts'] = [a for a in issue['attempts'] if a['attempt_id'] in selected]
        roots.update(issue['source_refs'])
        roots.update(r for a in issue['attempts'] for r in a['source_refs'])
        issues.append(issue)
    if not any('current_understanding' in i for i in issues):
        view = full
    else:
        counters = {r for s in full['source_records'].values() for r in s['counterevidence_refs']}
        # A paired label decline is adverse history even if an older updater
        # cited it as evidence rather than tagging it as counterevidence. A later
        # favorable synthesis must not silently remove those original pairs.
        declines = {pid for pid, pair in full['pairs'].items() if any(
            full['trajectories'][pair['parent']]['supervision'][axis]
            and not full['trajectories'][pair['candidate']]['supervision'][axis]
            for axis in ('success', 'compliant'))}
        # Selected attempts retain joint edit dependencies via their own source
        # records. Fallback issues also retain edit-only links from full history.
        for issue in issues:
            edits = {e for a in issue['attempts'] for e in a['edit_refs']}
            roots.update(r for r, s in full['source_records'].items() if edits & set(s['edit_refs']))
        view = open_memory_evidence(evidence, source_refs=roots, event_refs=counters, pair_refs=declines)
        view['memory_issues'] = issues
        view['issue_source_refs'] = {i['issue_id']: sorted(
            set(full['issue_source_refs'][i['issue_id']]) & view['source_records'].keys()) for i in issues}
    view['known_counterevidence_refs'] = sorted({r for s in full['source_records'].values()
                                                for r in s['counterevidence_refs']})
    return view
