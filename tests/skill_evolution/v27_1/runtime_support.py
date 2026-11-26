"""Synthetic LMB tasks and providers; no credentials or network."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from skilladam.types import BenchmarkCase
from src.skill_evolution.v27_1.lmb import actor, protocol as p
from src.skill_evolution.v28.storage import save

SKILL = '## Strategy\nUse the supplied passages.'
HIDDEN = 'PRIVATE_REASONING_SENTINEL'


def response(content='<answer>A</answer>', finish='stop', **extra):
    return {'model': 'synthetic', 'choices': [{'finish_reason': finish, 'message': {
        'role': 'assistant', 'content': content, 'reasoning_content': HIDDEN, **extra}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30,
                  'completion_tokens_details': {'reasoning_tokens': 5}}}


class Transport:
    def __init__(self, fn=None):
        self.fn, self.calls, self.seen = fn, 0, []
        self.config = deepcopy(p.ACTOR)
        self.lock = threading.Lock()

    def metadata(self):
        return deepcopy(self.config)

    def __call__(self, messages, directory):
        with self.lock:
            self.calls += 1
            self.seen.append(deepcopy(messages))
        return self.fn(messages, directory) if self.fn else response()


def http_archive(slot, raw):
    (slot / 'http_response.txt').write_text(json.dumps(raw))
    save(slot / 'http_status.json', {'status_code': 200})
    return raw


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.skill = self.root / 'skill.md'
        self.skill.write_text(SKILL)
        self.sleep = patch.object(actor.time, 'sleep').start()
        self.addCleanup(patch.stopall)

    def reject(self, fn, *args, **kwargs):
        with self.assertRaises((ValueError, KeyError, FileNotFoundError)):
            fn(*args, **kwargs)
