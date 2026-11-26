"""Synthetic HTTP archives and corruption variants shared by recovery tests."""
import json
from .support import response
from src.skill_evolution.v27 import stages
from src.skill_evolution.v27.benchmarks.lmb import protocol as p


def interrupted_batch(pending, retried):
    def generate(messages, slot):
        task = slot.parent.parent.name
        if task == p.digest(pending):
            raise KeyboardInterrupt('Synthetic unfinished request')
        raw = response(None, 'length') if task == p.digest(retried) and slot.name == '001' else response()
        (slot/'http_response.txt').write_text(json.dumps(raw))
        stages.save(slot/'http_status.json', {'status_code': 200})
        return raw
    return generate


def corruptions():
    return [
        ('attempts/001/request.json', None),
        ('attempts/002/request.json', None),
        ('attempts/002/request.json', lambda v: v['body'].update(messages=[])),
        ('attempts/001/request.json', lambda v: v['body'].update(max_tokens=1)),
        ('attempts/002/request.json', lambda v: v.update(endpoint='https://changed.invalid')),
        ('attempts/001/response.json', None),
        ('attempts/001/response.json', lambda v: v['choices'][0].update(finish_reason='stop')),
        ('attempts/001/response.json', lambda v: v['choices'][0]['message'].update(content='altered')),
        ('attempts/001/http_response.txt', None),
        ('attempts/001/http_response.txt', 'BROKEN HTTP BODY'),
        ('attempts/001/http_status.json', None),
        ('attempts/001/error.json', None),
        ('attempts/001/error.json', lambda v: v.update(error='ConnectionError')),
        ('attempts/001/error.json', lambda v: v.update(status='unknown')),
        ('attempts/001/error.json', lambda v: v.pop('archive')),
    ]


def damage(path, operation):
    if operation is None: path.unlink()
    elif isinstance(operation, str): path.write_text(operation)
    else:
        value = stages.read(path); operation(value); stages.save(path, value)


def snapshot(root):
    return {str(f.relative_to(root)): f.read_bytes() for f in root.rglob('*') if f.is_file()}
