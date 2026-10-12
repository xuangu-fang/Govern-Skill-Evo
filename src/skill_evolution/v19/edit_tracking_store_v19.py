"""Audited, model-free storage for v19 edit ledgers, not full Memory commits."""
from pathlib import Path

from .edit_tracking_v19 import DecidedEdits, EditLedger, TrackingRejected, digest, encode, parse, trace_edit_history, validate_edit_ledger


def save_edit_ledger(ledger, *, artifact_dir, history=()):
    """Validate before writing; existing directories are never overwritten."""
    payload = validate_edit_ledger(ledger, history=history)
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)

    def save(name, text):
        path = directory / name
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_bytes(text.encode('utf-8'))
        temporary.replace(path)

    save('validation.json', encode({'status': 'RUNNING'}))
    save('input.json', ledger.input_json)
    save('ledger.json', ledger.output_json)
    result = {'schema_version': 'edit_tracking_validation_v19.1', 'status': 'VALID',
              'run_id': payload['run_id'], 'round_id': payload['round_id'],
              'artifact_sha256': {'input.json': digest(ledger.input_json),
                                  'ledger.json': digest(ledger.output_json)}}
    save('validation.json', encode(result))
    return result


def load_edit_ledger(artifact_dir, *, history=()):
    """Hashes plus deterministic source revalidation; no trusting VALID alone."""
    directory = Path(artifact_dir)
    try:
        validation = parse((directory / 'validation.json').read_bytes().decode('utf-8'))
        if (set(validation) != {'schema_version', 'status', 'run_id', 'round_id', 'artifact_sha256'}
                or validation['schema_version'] != 'edit_tracking_validation_v19.1'
                or validation['status'] != 'VALID'
                or set(validation['artifact_sha256']) != {'input.json', 'ledger.json'}):
            raise TrackingRejected('incomplete or invalid ledger manifest')
        source = (directory / 'input.json').read_bytes().decode('utf-8')
        output = (directory / 'ledger.json').read_bytes().decode('utf-8')
        if validation['artifact_sha256'] != {'input.json': digest(source), 'ledger.json': digest(output)}:
            raise TrackingRejected('ledger artifact digest mismatch')
        ledger = EditLedger(source, output)
        payload = validate_edit_ledger(ledger, history=history)
        if any(validation[k] != payload[k] for k in ('run_id', 'round_id')):
            raise TrackingRejected('ledger manifest identity mismatch')
        return ledger
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        raise TrackingRejected('cannot load edit ledger: ' + str(exc)) from exc


def save_edit_history(history, *, artifact_dir):
    """Save an immutable audit snapshot including decisions; not a campaign commit.

    Decisions are supplied by the trusted caller. Writing this archive never
    promotes a Skill or advances the future persistent-Memory commit head.
    """
    view = trace_edit_history(history)
    snapshot = {'schema_version': 'edit_history_snapshot_v19.1', 'rounds': [
        {'gate_decision': item.gate_decision, 'input_json': item.ledger.input_json,
         'output_json': item.ledger.output_json} for item in history]}
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)
    artifacts = {'history.json': encode(snapshot), 'view.json': encode(view)}

    def save(name, text):
        temporary = directory / (name + '.tmp')
        temporary.write_bytes(text.encode('utf-8'))
        temporary.replace(directory / name)

    save('validation.json', encode({'status': 'RUNNING'}))
    for name, content in artifacts.items():
        save(name, content)
    result = {'schema_version': 'edit_history_validation_v19.1', 'status': 'VALID',
              'history_sha256': view['history_sha256'],
              'artifact_sha256': {name: digest(content) for name, content in artifacts.items()}}
    save('validation.json', encode(result))
    return result


def load_edit_history(artifact_dir):
    directory = Path(artifact_dir)
    try:
        manifest = parse((directory / 'validation.json').read_bytes().decode('utf-8'))
        if (set(manifest) != {'schema_version', 'status', 'history_sha256', 'artifact_sha256'}
                or manifest['schema_version'] != 'edit_history_validation_v19.1'
                or manifest['status'] != 'VALID'
                or set(manifest['artifact_sha256']) != {'history.json', 'view.json'}):
            raise TrackingRejected('incomplete or invalid history manifest')
        artifacts = {name: (directory / name).read_bytes().decode('utf-8')
                     for name in ('history.json', 'view.json')}
        if manifest['artifact_sha256'] != {name: digest(content) for name, content in artifacts.items()}:
            raise TrackingRejected('history artifact digest mismatch')
        snapshot = parse(artifacts['history.json'])
        if (set(snapshot) != {'schema_version', 'rounds'}
                or snapshot['schema_version'] != 'edit_history_snapshot_v19.1'
                or type(snapshot['rounds']) is not list):
            raise TrackingRejected('invalid history snapshot')
        for item in snapshot['rounds']:
            if type(item) is not dict or set(item) != {'gate_decision', 'input_json', 'output_json'}:
                raise TrackingRejected('invalid history round')
        history = tuple(DecidedEdits(EditLedger(item['input_json'], item['output_json']), item['gate_decision'])
                        for item in snapshot['rounds'])
        view = trace_edit_history(history)
        if (encode(view) != encode(parse(artifacts['view.json']))
                or view['history_sha256'] != manifest['history_sha256']):
            raise TrackingRejected('history view differs from revalidated sources')
        return history
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        raise TrackingRejected('cannot load edit history: ' + str(exc)) from exc
