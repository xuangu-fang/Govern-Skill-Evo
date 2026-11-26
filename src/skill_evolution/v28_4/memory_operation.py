"""Operation-local byte validation shared with the plain SearchQA Actor journals."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from src.skill_evolution.v28 import validation

_ACTIVE = ContextVar('v28_4_memory_operation', default=None)


def current(method):
    active = _ACTIVE.get()
    return active if active is not None and active.method is method else None


class Operation:
    def __init__(self, method, checks):
        self.method, self.checks = method, checks

    def watch(self, root):
        self.checks.watch_tree(Path(root))

    def watch_file(self, path):
        self.checks.watch_file(path)

    def verify(self):
        self.method.actor_adapter._preflight()
        self.checks.verify()


@contextmanager
def operation(method):
    active = current(method)
    if active is not None:
        yield active
        return
    with validation.operation(method.actor_adapter) as checks:
        session = Operation(method, checks)
        token = _ACTIVE.set(session)
        try:
            yield session
            session.verify()
        finally:
            _ACTIVE.reset(token)
