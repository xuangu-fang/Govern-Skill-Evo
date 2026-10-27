"""Read this experiment's split archives without changing historical records."""
import json
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parents[3] / 'artifacts/methods/v23_3' / HERE.name


def load_saved(relative, loader, *args, **kwargs):
    """Give an existing loader a temporary view of evidence and original inputs."""
    with TemporaryDirectory(prefix='v23_3-read-') as temporary:
        root = Path(temporary)

        def assemble(relative):
            destination = root / relative
            if destination.exists():
                return destination
            destination.mkdir(parents=True)
            for source in (HERE / relative, ARCHIVE / relative):
                if source.is_dir():
                    for file in source.iterdir():
                        if file.is_file():
                            copy2(file, destination / file.name)
            metadata = destination / 'run.json'
            if metadata.exists():
                value = json.loads(metadata.read_text())
                changed = False
                for key in ('grouping_directory', 'diagnosis_directory'):
                    if key not in value:
                        continue
                    path = Path(value[key])
                    for source in (HERE, ARCHIVE):
                        if path.is_relative_to(source):
                            value[key] = str(assemble(path.relative_to(source)))
                            changed = True
                            break
                if changed:
                    metadata.write_text(json.dumps(value, ensure_ascii=False))
            return destination

        return loader(assemble(Path(relative)), *args, **kwargs)
