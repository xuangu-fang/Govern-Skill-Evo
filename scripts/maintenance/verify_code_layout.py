"""Check code relocation, imports, old entry removal, and recorded checksums."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile
from layout_history import current as canonical_path, expected_digest, deleted

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def import_errors(tree, name):
    """Resolve internal module imports without executing experiment code."""
    errors = []
    package = name[:-3].replace('/', '.').split('.')[:-1]

    def exists(module):
        path = ROOT.joinpath(*module.split('.'))
        return path.with_suffix('.py').is_file() or path.is_dir()

    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level:
                module = '.'.join(package[:len(package) - node.level + 1]
                                  + ([module] if module else []))
            modules = [module]
            # Package initializers contain no compatibility exports.
            if module.startswith(('src.skill_evolution', 'scripts', 'tests')):
                path = ROOT.joinpath(*module.split('.'))
                if path.is_dir():
                    modules += [module + '.' + alias.name for alias in node.names
                                if alias.name != '*']
        for module in modules:
            if module.startswith(('src.skill_evolution.', 'skill_evolution.', 'scripts.', 'tests.',
                                  'src.benchmark_', 'benchmark_v5')):
                canonical = 'src.' + module if module.startswith(('skill_evolution.', 'benchmark_v5')) else module
                if not exists(canonical):
                    errors.append(f'Missing import in {name}:{node.lineno}: {module}')
    return errors


def verify():
    receipt = json.loads((ROOT / 'docs/repository/code-migration.json').read_text())
    errors = []
    snapshot = ROOT / receipt['snapshot']
    if digest(snapshot.read_bytes()) != receipt['snapshot_sha256']:
        raise ValueError('Code relocation snapshot checksum mismatch')
    with zipfile.ZipFile(snapshot) as archive:
        for row in receipt['files']:
            if digest(archive.read(row['old'])) != row['before_sha256']:
                errors.append('Snapshot changed: ' + row['old'])
            if deleted(row['new']):
                continue
            current = ROOT / canonical_path(row['new'])
            if not current.is_file() or digest(current.read_bytes()) != expected_digest(row['new'], row['after_sha256']):
                errors.append('Current file changed: ' + row['new'])
    for name, expected in receipt['created_files'].items():
        if deleted(name):
            continue
        path = ROOT / canonical_path(name)
        if not path.is_file() or digest(path.read_bytes()) != expected_digest(name, expected):
            errors.append('Created file changed: ' + name)
    for row in receipt['relocations']:
        old = ROOT / row['old']
        if old.exists() or old.is_symlink():
            errors.append('Old entry remains: ' + row['old'])
        if not deleted(row['new']) and not (ROOT / canonical_path(row['new'])).exists():
            errors.append('Destination missing: ' + row['new'])
    tokens = [row['old'] for row in receipt['relocations']]
    tokens += list(receipt['module_relocations'])
    pattern = re.compile('|'.join(re.escape(t) + r'(?=$|[^A-Za-z0-9_])'
                                  for t in sorted(tokens, key=len, reverse=True)))
    for name in receipt['active_files']:
        if deleted(name):
            continue
        path = ROOT / canonical_path(name)
        if not path.is_file():
            errors.append('Active file missing: ' + name)
            continue
        source = path.read_text()
        if pattern.search(source):
            errors.append('Old path/module reference: ' + name)
        if path.suffix == '.py':
            try:
                tree = ast.parse(source, filename=name)
                errors.extend(import_errors(tree, canonical_path(name)))
            except SyntaxError as error:
                errors.append(str(error))
    links = []
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [d for d in dirs if d not in
                   ('.git', 'external', '.venv', '__pycache__', '.pytest_cache')]
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                links.append(str(path.relative_to(ROOT)))
    errors.extend('Project symlink remains: ' + name for name in links)
    for name, expected in receipt['preserved_logs'].items():
        if digest((ROOT / name).read_bytes()) != expected_digest(name, expected):
            errors.append('Preserved experiment log changed: ' + name)
    return {'moved_files': receipt['moved_files'], 'changed_or_moved_files': len(receipt['files']),
            'active_files_checked': len(receipt['active_files']), 'project_symlinks': len(links),
            'errors': errors}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
