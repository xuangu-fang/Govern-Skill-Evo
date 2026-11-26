"""Lazy adapter-owned resources: importing a module does not choose a benchmark."""
from pathlib import Path
from .benchmark import current as benchmark_current


class Resource:
    def __init__(self, key):
        self.key = key

    def read_text(self, encoding='utf-8'):
        return benchmark_current().resource(self.key).read_text(encoding=encoding)

    def read_bytes(self):
        return benchmark_current().resource(self.key).read_bytes()

    @property
    def stem(self):
        return Path(self.key).stem

    def __fspath__(self):
        return str(benchmark_current().resource(self.key))


def resource(key):
    return Resource(key)
