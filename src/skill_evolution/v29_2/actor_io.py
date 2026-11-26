"""v29.2-only batch I/O; reuse the existing Actor execution and scoring rules."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid

from src.skill_evolution.v29.benchmarks.docvqa import actor, protocol as p
from src.skill_evolution.v29.storage import read, save, freeze


def read_skill(path):
    return Path(path).read_bytes().decode('utf-8')


def _recover_partial_body(case, skill, folder):
    """Keep incomplete HTTP evidence without treating it as a scored response.

    Only the final, started, unfinished slot is eligible. Moving its body out
    of the completed-response path lets the unchanged Actor mark the outcome
    unknown and consume that slot under its existing six-request budget.
    """
    attempts = folder / 'attempts'
    slots = sorted(path for path in attempts.iterdir() if path.is_dir()) if attempts.exists() else []
    if not slots:
        return
    slot = slots[-1]
    body = slot / 'http_response.txt'
    if not body.exists() or (slot / 'http_status.json').exists():
        return
    with actor.locked(folder):
        p.require(len(slots) <= 6 and [path.name for path in slots] ==
                  [f'{i:03}' for i in range(1, len(slots) + 1)], 'Invalid attempt sequence')
        p.require(not any((folder / name).exists() for name in ('result.json', 'trajectory.json')) and
                  not any((slot / name).exists() for name in ('response.json', 'error.json')),
                  'Incomplete HTTP evidence conflicts with a completed or classified request')
        config = p.actor_config(); messages = p.messages_for_case(case, skill)
        freeze(folder / 'signature.json', actor._signature(case, skill, config, messages), read_only=True)
        freeze(slot / 'request.json', actor.request_record(messages, config), read_only=True)
        marker = read(slot / 'request_started.json')
        p.require(type(marker.get('attempt')) is int and marker['attempt'] == len(slots) and
                  isinstance(marker.get('at'), str), 'Invalid attempt marker')
        # Do not conceal invalid earlier requests by repairing the final slot.
        for i, prior in enumerate(slots[:-1], 1):
            _, failure = actor._attempt(prior, i, messages, config)
            p.require((prior / 'error.json').exists() and failure is not None and failure.retryable,
                      'Incomplete response follows a non-retryable request')
        archived = slot / 'http_response.incomplete.txt'
        p.require(not archived.exists(), 'Conflicting incomplete HTTP archive')
        body.replace(archived)


def actor_batch(adapter, tasks, skill_file, directory, config, *, final=False):
    """Same Actor batch protocol, with exact Skill text and narrow recovery.

    Kept local to v29.2 so v29/v29.1 batch and journal behavior stays unchanged.
    """
    transport = adapter.transport
    if transport is not None: p.validate_config(transport.metadata())
    p.require(type(final) is bool and final == (config.get('role') == 'evaluation'), 'Invalid final flag')
    cases = adapter._cases(tasks, config)
    skill = None if skill_file is None else read_skill(skill_file)
    signature = adapter._signature(tasks, skill, config)
    for case in cases: p.messages_for_case(case, skill)
    root = Path(directory)
    with actor.locked(root):
        if (root / 'batch.json').exists():
            batch = read(root / 'batch.json')
            p.require(batch['signature'] == signature, 'Existing batch differs')
        else:
            # batch.tmp is uncommitted initialization: no task journal may exist.
            p.require(all(path.is_file() and path.name in ('.execution.lock', 'batch.tmp')
                          for path in root.iterdir()), 'Missing identity for existing batch')
            batch = {'batch_id': str(uuid.uuid4()), 'signature': signature}
            save(root / 'batch.json', batch)
        if (root / 'records.json').exists():
            return adapter.read_batch(root)
        for index, case in enumerate(cases, 1):
            folder = adapter._folder(root, index)
            _recover_partial_body(case, skill, folder)
            actor.validate_pending(case, skill, folder)
            if (folder / 'trajectory.json').exists():
                expected = adapter._record(case, actor.read_completed(case, skill, folder), batch, index)
                freeze(folder / 'trajectory.json', expected, read_only=True)
        if transport is None:
            # Archive-only recovery can rebuild batch summaries, never execute.
            for index, case in enumerate(cases, 1):
                actor.read_completed(case, skill, adapter._folder(root, index))
            class ArchiveOnly:
                def metadata(self): return p.actor_config()
                def __call__(self, *args): raise RuntimeError('Archive-only recovery cannot request a model')
            transport = ArchiveOnly()

        def run(index, case):
            folder = adapter._folder(root, index)
            execution = actor.execute(case, skill, folder, transport)
            record = adapter._record(case, execution, batch, index)
            freeze(folder / 'trajectory.json', record)
            return record

        with ThreadPoolExecutor(max_workers=min(signature['workers'], len(cases))) as pool:
            futures = [pool.submit(run, i, case) for i, case in enumerate(cases, 1)]
            records = [future.result() for future in futures]
        freeze(root / 'records.json', records)
        return records
