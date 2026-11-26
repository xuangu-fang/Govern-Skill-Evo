"""Build/check a separate, audited OfficeQA corpus without network or models.

python -m scripts.benchmarks.officeqa.correct_parsed [--check]
Original downloads and historical run artifacts are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from .prepare import deny_network, digest


def patch_text(text, suffix, corrections):
    """Replace uniquely identified table rows, preserving all other bytes."""
    for correction in corrections:
        cells = [cell.strip() for cell in correction['txt_row'].strip('|').split('|')]
        column = correction['column']
        if cells[column] != correction['before']:
            raise ValueError('Correction column does not match its original value')
        changed = cells.copy()
        changed[column] = correction['after']
        if suffix == '.txt':
            before = correction['txt_row']
            after = '| ' + ' | '.join(changed) + ' |'
        elif suffix == '.json':
            def html_row(values):
                return '<tr>' + ''.join('<td>' + (f'{int(v):,}' if i and v.isdigit() else v) + '</td>'
                                       for i, v in enumerate(values)) + '</tr>'
            before, after = html_row(cells), html_row(changed)
        else:
            raise ValueError('Unsupported parsed document format')
        if text.count(before) != 1:
            raise ValueError(f'Expected exactly one original row: {correction["task_id"]}/{suffix}')
        text = text.replace(before, after, 1)
    if suffix == '.json':
        json.loads(text)
    return text


def run(root, *, check=False):
    root = Path(root)
    base = root / 'data/officeqa'
    source = base / 'raw/treasury_bulletins_parsed'
    destination = base / 'corrected_v1'
    corpus = destination / 'treasury_bulletins_parsed'
    spec_path = root / 'benchmarks/officeqa/parsed_corrections_v1.json'
    spec = json.loads(spec_path.read_text())
    downloaded = json.loads((base / 'download_manifest.json').read_text())
    if downloaded['revision'] != spec['source_revision']:
        raise ValueError('Correction source revision differs from download')
    # Validate the entire original download, including unchanged questions/answers.
    for entry in downloaded['files']:
        path = base / entry['path']
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Original download changed: {entry["path"]}')
    files = sorted(path for path in source.rglob('*') if path.is_file())
    expected, patched, changes = {}, {}, {}
    for path in files:
        relative = str(path.relative_to(source))
        corrections = [c for c in spec['corrections'] if c['document'] == path.stem]
        if corrections:
            content = patch_text(path.read_text(), path.suffix, corrections).encode()
            patched[relative] = content
            expected[relative] = hashlib.sha256(content).hexdigest()
            changes[relative] = {'before_sha256': digest(path), 'after_sha256': expected[relative]}
        else:
            expected[relative] = digest(path)
    wanted = {f'{folder}/{c["document"]}{suffix}' for c in spec['corrections']
              for folder, suffix in [('jsons', '.json'), ('transformed', '.txt')]}
    if set(patched) != wanted:
        raise ValueError('Missing correction source documents')
    report = {'version': spec['version'], 'source_revision': spec['source_revision'],
              'correction_spec_sha256': digest(spec_path), 'corrections': spec['corrections'],
              'source_csv_sha256': digest(base / 'raw/officeqa_full.csv'),
              'verified_original_files': len(downloaded['files']), 'corpus_files': len(files),
              'changed_files': changes,
              'corpus_sha256': hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
              'model_calls': 0, 'network_calls': 0}
    if destination.exists():
        actual = {str(p.relative_to(corpus)): digest(p) for p in corpus.rglob('*') if p.is_file()}
        if actual != expected or json.loads((destination / 'audit.json').read_text()) != report:
            raise ValueError('Existing corrected corpus or audit differs; refusing overwrite')
    elif check:
        raise ValueError('Corrected corpus is missing')
    else:
        staging = Path(tempfile.mkdtemp(prefix='.corrected_v1-', dir=base))
        try:
            target = staging / 'treasury_bulletins_parsed'
            shutil.copytree(source, target)
            for relative, content in patched.items():
                (target / relative).write_bytes(content)
            actual = {str(p.relative_to(target)): digest(p) for p in target.rglob('*') if p.is_file()}
            if actual != expected:
                raise ValueError('Copied corpus differs from expected content')
            (staging / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            staging.rename(destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(json.dumps({'status': 'passed', 'parsed_root': str(corpus),
                      'corpus_files': len(files), 'changed_files': len(changes),
                      'corrected_cells': len(spec['corrections']), 'model_calls': 0}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sys.addaudithook(deny_network)
    run(Path(__file__).resolve().parents[3], check=args.check)
