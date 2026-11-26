"""Shared case-level scheduling and restart journal; no request retries."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile


WORKERS = 4
REQUEST_TIMEOUT_SECONDS = 300
CONNECT_TIMEOUT_SECONDS = 10
REQUEST_ATTEMPTS = 6
RETRY_POLICY = 'six_attempts_temporary_format_feedback_v1'
EXECUTION_CONFIG = {
    'scheduler': 'thread_pool_per_case', 'workers': WORKERS,
    'result_order': 'completion', 'request_timeout_seconds': REQUEST_TIMEOUT_SECONDS,
    'connect_timeout_seconds': CONNECT_TIMEOUT_SECONDS,
    'request_attempts_total': REQUEST_ATTEMPTS,
    'retry_policy': RETRY_POLICY, 'transport': 'direct_http_no_inner_retries',
    'retry_delay_seconds': 2,
    'actor_resume': 'persistent_round_attempts_and_tool_progress',
    'resume': 'results.jsonl_by_task_id',
}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.execution.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_results(path):
    if not path.exists():
        return []
    rows, seen, valid_bytes = [], set(), 0
    with path.open('rb') as handle:
        for line in handle:
            # A killed append can leave a partial final line. Only complete
            # newline-terminated records count as committed work.
            if not line.endswith(b'\n'):
                break
            row = json.loads(line)
            if row['id'] != row['record']['task_id'] or row['id'] in seen:
                raise ValueError('Invalid or duplicate OfficeQA journal ID')
            rows.append(row)
            seen.add(row['id'])
            valid_bytes += len(line)
    if path.stat().st_size != valid_bytes:
        with path.open('r+b') as handle:
            handle.truncate(valid_bytes)
    return rows


def run_batch(items, execute, directory, *, identity, workers=WORKERS):
    """Collect completed cases durably; rethrow infrastructure errors after drain.

    items are (task_id, task) pairs. A directory identifies one fixed evaluation
    batch/Skill/configuration, not a whole training run. Requests are retried by
    the per-case Actor; this scheduler never restarts a failed case automatically.
    """
    if type(workers) is not int or workers <= 0:
        raise ValueError('workers must be a positive integer')
    items = list(items)
    ids = [uid for uid, _ in items]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate batch cases')
    signature = {'schema': 1, 'ids': ids, 'identity': identity}
    # Normalize tuples and other ordinary JSON containers before comparison.
    signature = json.loads(json.dumps(signature, ensure_ascii=False))
    directory = Path(directory)
    with _locked(directory):
        manifest = directory / 'run.json'
        path = directory / 'results.jsonl'
        if manifest.exists():
            if json.loads(manifest.read_text()) != signature:
                raise ValueError('OfficeQA resume identity differs; use a separate batch directory')
        else:
            if path.exists():
                raise ValueError('OfficeQA journal has no run identity')
            atomic_json(manifest, signature)
        rows = _read_results(path)
        done = {row['id'] for row in rows}
        if not done <= set(ids):
            raise ValueError('OfficeQA journal contains unexpected task IDs')
        pending = [(uid, item) for uid, item in items if uid not in done]
        error = None
        with path.open('a', encoding='utf-8') as handle, ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(execute, item): uid for uid, item in pending}
            for future in as_completed(futures):
                try:
                    record = future.result()
                except Exception as exc:
                    # Save other successful cases; failed cases remain pending
                    # for an explicit restart, rather than becoming zero scores.
                    if error is None:
                        error = exc
                    continue
                uid = futures[future]
                if record['task_id'] != uid:
                    raise ValueError('OfficeQA result task ID differs')
                row = {'id': uid, 'record': record}
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
                rows.append(row)
        if error is not None:
            raise error
        return [row['record'] for row in rows]
