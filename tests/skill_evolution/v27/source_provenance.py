"""Verify the historical source manifest plus explicitly reviewed later changes."""
import difflib
import hashlib
import json
from pathlib import Path

MANIFEST = Path('docs/methods/v27/draft_20261030_001/source_manifest.json')
RECONCILIATION = Path('docs/methods/v27/actor_49152_20261031/reconciliation.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    root = Path(root)
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def local(name):
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()), 'Source path escapes repository')
        return path

    original = local(MANIFEST).read_bytes()
    sources = json.loads(original)['sources']
    audit = json.loads(local(RECONCILIATION).read_text())
    require(audit['schema'] == 'v27_reviewed_source_changes_v1', 'Unknown provenance schema')
    require(audit['historical_manifest_sha256'] == digest(original), 'Historical manifest changed')
    changes = audit['changes']
    require(set(changes) <= set(sources), 'Reviewed change outside historical sources')
    report = {}
    for name, historical_hash in sources.items():
        current_hash = digest(local(name).read_bytes())
        if name not in changes:
            require(current_hash == historical_hash, f'Unreviewed source change: {name}')
            report[name] = {'status': 'unchanged', 'sha256': current_hash}
            continue
        change = changes[name]
        require(change['historical_sha256'] == historical_hash, f'Historical identity differs: {name}')
        before = local(change['historical_snapshot']).read_bytes()
        after = local(change['reviewed_snapshot']).read_bytes()
        require(digest(before) == historical_hash, f'Historical snapshot changed: {name}')
        require(digest(after) == change['reviewed_sha256'] == current_hash,
                f'Current source differs from reviewed snapshot: {name}')
        expected_diff = ''.join(difflib.unified_diff(
            before.decode().splitlines(True), after.decode().splitlines(True),
            fromfile='historical/' + name, tofile='reviewed/' + name))
        require(local(change['diff']).read_bytes() == expected_diff.encode(), f'Reviewed diff changed: {name}')
        require(bool(change['reason'].strip()) and bool(change['v27_impact'].strip()), 'Missing review rationale')
        report[name] = {'status': 'reviewed_source_change', 'historical_sha256': historical_hash,
                        'current_sha256': current_hash, 'evidence': str(RECONCILIATION)}
    return {'historical_manifest': str(MANIFEST), 'historical_manifest_sha256': digest(original),
            'sources_checked': len(report), 'unchanged': len(report) - len(changes),
            'reviewed_changes': len(changes), 'sources': report}
