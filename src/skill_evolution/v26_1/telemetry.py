"""Durable elapsed wall time per invocation that reserved at least one new send."""
from contextlib import contextmanager
import json
from pathlib import Path
import time
import uuid
from src.adapters.officeqa.execution import atomic_json


def reserved(root):
    root=Path(root)
    if (root / 'rounds').is_dir():
        count=0
        for rd in (root / 'rounds').glob('R*'):
            if (rd / 'cost_summary.json').exists():
                summary=json.loads((rd / 'cost_summary.json').read_text())
                count+=summary['actor_reserved_http_attempts']+summary['method_reserved_http_attempts']
            else: count+=reserved(rd)
        return count
    count=sum(1 for _ in root.rglob('request_started.json'))
    for path in root.rglob('actor_state.json'):
        state=json.loads(path.read_text())
        count+=sum(len(r['attempts']) for r in state['rounds'])
    return count


@contextmanager
def invocation(root, kind):
    root=Path(root); before=reserved(root); start=time.monotonic()
    try: yield
    finally:
        after=reserved(root)
        if after>before:
            atomic_json(root/'timing_sessions'/f'{uuid.uuid4()}.json',
                        {'kind':kind,'elapsed_seconds':time.monotonic()-start,
                         'new_reserved_requests':after-before})
