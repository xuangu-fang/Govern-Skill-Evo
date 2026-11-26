"""Apply audited v2 document corrections offline, preserving raw and v1.

python -m scripts.benchmarks.officeqa.correct_parsed_v2 [--check]
Requires the verified corrected_v1 corpus. No models or network are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from .correct_parsed import run as verify_v1
from .prepare import deny_network, digest


def patch_file(content, patch):
    """Fail closed on source drift, ambiguity, or unexpected output bytes."""
    if hashlib.sha256(content).hexdigest() != patch['before_sha256']:
        raise ValueError(f'Correction source hash differs: {patch["path"]}')
    text = content.decode('utf-8')
    for replacement in patch['replacements']:
        if text.count(replacement['before']) != 1:
            raise ValueError(f'Expected one original span: {patch["path"]}')
        text = text.replace(replacement['before'], replacement['after'], 1)
    result = text.encode('utf-8')
    if hashlib.sha256(result).hexdigest() != patch['after_sha256']:
        raise ValueError(f'Correction output hash differs: {patch["path"]}')
    if patch['path'].endswith('.json'):
        json.loads(text)
    return result


def run(root, *, check=False):
    root = Path(root)
    base = root / 'data/officeqa'
    spec_path = root / 'benchmarks/officeqa/parsed_corrections_v2.json'
    spec = json.loads(spec_path.read_text())
    parent = verify_v1(root, check=True)
    if (parent['version'] != spec['base_version'] or parent['source_revision'] != spec['source_revision']
            or digest(base / 'corrected_v1/audit.json') != spec['base_audit_sha256']):
        raise ValueError('Correction base differs')
    if digest(root / spec['evidence_audit_path']) != spec['evidence_audit_sha256']:
        raise ValueError('Correction evidence audit differs')
    source = base / 'corrected_v1/treasury_bulletins_parsed'
    destination = base / 'corrected_v2'
    patches = {p['path']: p for p in spec['files']}
    if len(patches) != len(spec['files']):
        raise ValueError('Duplicate correction file')
    expected, changed = {}, {}
    for path in sorted(source.rglob('*')):
        if not path.is_file():
            continue
        relative = str(path.relative_to(source))
        if relative in patches:
            changed[relative] = patch_file(path.read_bytes(), patches[relative])
            expected[relative] = hashlib.sha256(changed[relative]).hexdigest()
        else:
            expected[relative] = digest(path)
    if set(changed) != set(patches):
        raise ValueError('Missing correction source file')
    report = {'version': spec['version'], 'source_revision': spec['source_revision'],
              'base_audit_sha256': spec['base_audit_sha256'], 'correction_spec_sha256': digest(spec_path),
              'source_csv_sha256': parent['source_csv_sha256'], 'corpus_files': len(expected),
              'changed_files_from_v1': {p: {'before_sha256': patches[p]['before_sha256'],
                                          'after_sha256': expected[p]} for p in changed},
              'new_corrected_cells': len(spec['cell_corrections']),
              'restored_column_values': len(spec['restored_column']['values_by_row']),
              'corpus_sha256': hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
              'model_calls': 0, 'network_calls': 0}
    def validate_files(folder):
        actual = {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('Corrected v2 corpus differs; refusing overwrite')
    if destination.exists():
        validate_files(destination / 'treasury_bulletins_parsed')
        if json.loads((destination / 'audit.json').read_text()) != report:
            raise ValueError('Corrected v2 audit differs; refusing overwrite')
    elif check:
        raise ValueError('Corrected v2 corpus is missing')
    else:
        staging = Path(tempfile.mkdtemp(prefix='.corrected_v2-', dir=base))
        try:
            target = staging / 'treasury_bulletins_parsed'
            shutil.copytree(source, target)
            for relative, content in changed.items():
                (target / relative).write_bytes(content)
            validate_files(target)
            (staging / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            staging.rename(destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print(json.dumps({'status': 'passed', 'parsed_root': str(destination / 'treasury_bulletins_parsed'),
                      'changed_files_from_v1': len(changed), 'new_corrected_cells': report['new_corrected_cells'],
                      'restored_column_values': report['restored_column_values'], 'model_calls': 0}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sys.addaudithook(deny_network)
    run(Path(__file__).resolve().parents[3], check=args.check)
