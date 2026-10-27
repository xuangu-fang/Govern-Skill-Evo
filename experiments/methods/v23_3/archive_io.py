"""Local readers for V23.3 evidence in Git and raw data in artifacts."""
from contextlib import contextmanager
import json
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

EXPERIMENTS = Path(__file__).resolve().parent
ARCHIVE = EXPERIMENTS.parents[2] / 'artifacts/methods/v23_3'


def raw_path(path):
    path = Path(path).absolute()
    if path.is_relative_to(EXPERIMENTS):
        return ARCHIVE / path.relative_to(EXPERIMENTS)
    return path


def resolve(path):
    """Resolve a saved file; existing curated files keep their original location."""
    path = Path(path)
    archived = raw_path(path)
    return archived if not path.exists() and archived.exists() else path


def archive_glob(path, pattern, *, recursive=False):
    """Enumerate both locations once, including mixed evidence/runtime folders."""
    path = Path(path)
    files = {}
    for root in dict.fromkeys((raw_path(path), path)):
        matches = root.rglob(pattern) if recursive else root.glob(pattern)
        for file in matches:
            files[file.relative_to(root)] = file
    return iter(files[key] for key in sorted(files))


@contextmanager
def materialized(directory):
    """Assemble a temporary loader view; rewrite upstream paths only in that view."""
    directory = Path(directory).absolute()
    if not directory.is_relative_to(EXPERIMENTS) and not directory.is_relative_to(ARCHIVE):
        yield directory
        return
    with TemporaryDirectory(prefix='v23_3-read-') as temporary:
        root = Path(temporary)
        prepared = set()

        def assemble(source):
            base = EXPERIMENTS if source.is_relative_to(EXPERIMENTS) else ARCHIVE
            relative = source.relative_to(base)
            target = root / relative
            if relative in prepared:
                return target
            prepared.add(relative)
            for folder in (EXPERIMENTS / relative, ARCHIVE / relative):
                if folder.is_dir():
                    for file in folder.rglob('*'):
                        if file.is_file() and '__pycache__' not in file.parts:
                            destination = target / file.relative_to(folder)
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            copy2(file, destination)
            for metadata in target.rglob('run.json'):
                value = json.loads(metadata.read_text())
                changed = False
                for key in ('grouping_directory', 'diagnosis_directory', 'preconditioner_directory'):
                    if key in value:
                        upstream = Path(value[key])
                        if upstream.is_relative_to(EXPERIMENTS) or upstream.is_relative_to(ARCHIVE):
                            value[key] = str(assemble(upstream))
                            changed = True
                if changed:
                    metadata.write_text(json.dumps(value, ensure_ascii=False))
            return target

        yield assemble(directory)


def load_saved(loader, directory, *args, **kwargs):
    with materialized(directory) as view:
        return loader(view, *args, **kwargs)
