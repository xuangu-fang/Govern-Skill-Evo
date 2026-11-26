"""Offline corpus corrections: original provenance, exact scope and Actor input."""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import socket

import pytest

from scripts.benchmarks.officeqa.correct_parsed import patch_text, run


ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((ROOT / 'benchmarks/officeqa/parsed_corrections_v1.json').read_text())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Network and model clients are forbidden')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    import openai
    monkeypatch.setattr(openai, 'OpenAI', denied)
    monkeypatch.setattr(openai, 'AzureOpenAI', denied)


@pytest.fixture
def corpus(tmp_path):
    spec = tmp_path / 'benchmarks/officeqa/parsed_corrections_v1.json'
    spec.parent.mkdir(parents=True)
    spec.write_text(json.dumps(SPEC))
    base = tmp_path / 'data/officeqa'
    raw = base / 'raw/treasury_bulletins_parsed'
    for folder in ('transformed', 'jsons'):
        (raw / folder).mkdir(parents=True)
    for document in {c['document'] for c in SPEC['corrections']}:
        rows = [c['txt_row'] for c in SPEC['corrections'] if c['document'] == document]
        (raw / 'transformed' / f'{document}.txt').write_text('Untouched heading\n' + '\n'.join(rows) + '\n')
        html = ''
        for row in rows:
            cells = [s.strip() for s in row.strip('|').split('|')]
            html += '<tr>' + ''.join(f'<td>{int(c):,}</td>' if i and c.isdigit() else f'<td>{c}</td>'
                                     for i, c in enumerate(cells)) + '</tr>'
        (raw / 'jsons' / f'{document}.json').write_text(json.dumps({'document': {'elements': [
            {'bbox': [{'page_id': 15}], 'content': '<table>' + html + '</table>'}]}}))
    (raw / 'transformed/unchanged.txt').write_text('Unchanged evidence 4100 2113 3532 3531\n')
    (base / 'raw/officeqa_full.csv').write_text('uid,answer\nUID0007,4962.46\nUID0004,1608.80%\n')
    entries = [{'path': str(p.relative_to(base)), 'bytes': p.stat().st_size,
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (base / 'raw').rglob('*') if p.is_file()]
    (base / 'download_manifest.json').write_text(json.dumps({'revision': SPEC['source_revision'], 'files': entries}))
    return tmp_path, raw


def test_build_check_preserves_raw_and_only_changes_four_files(corpus):
    root, raw = corpus
    before = {p: p.read_bytes() for p in raw.rglob('*') if p.is_file()}
    report = run(root)
    assert len(report['changed_files']) == 4
    assert run(root, check=True) == report == run(root)
    assert all(p.read_bytes() == content for p, content in before.items())
    corrected = root / 'data/officeqa/corrected_v1/treasury_bulletins_parsed'
    assert (corrected / 'transformed/unchanged.txt').read_bytes() == (raw / 'transformed/unchanged.txt').read_bytes()
    assert all((corrected / rel).stat().st_ino != (raw / rel).stat().st_ino for rel in report['changed_files'])
    (corrected / 'transformed/unchanged.txt').write_text('drift')
    with pytest.raises(ValueError, match='refusing overwrite'):
        run(root, check=True)


def test_reject_raw_drift_and_missing_output(corpus):
    root, raw = corpus
    with pytest.raises(ValueError, match='missing'):
        run(root, check=True)
    (raw / 'transformed/unchanged.txt').write_text('drift')
    with pytest.raises(ValueError, match='Original download changed'):
        run(root)
    assert not (root / 'data/officeqa/corrected_v1').exists()


@pytest.mark.parametrize('copies', [0, 2])
def test_reject_missing_or_ambiguous_row(copies):
    correction = SPEC['corrections'][0]
    with pytest.raises(ValueError, match='exactly one'):
        patch_text((correction['txt_row'] + '\n') * copies, '.txt', [correction])


@pytest.mark.parametrize('version', [1, 2])
def test_real_corrected_pages_tools_and_uid7_arithmetic(version):
    from skilladam.benchmarks.officeqa import tool_runtime
    from src.adapters.officeqa.data import Dataset
    from src.adapters.officeqa.runtime import Runtime
    parsed = ROOT / f'data/officeqa/corrected_v{version}/treasury_bulletins_parsed'
    if not parsed.exists():
        pytest.skip('Run offline corpus correction preparation first')
    dataset = Dataset(ROOT / 'data/officeqa/prepared_v2')
    runtime = Runtime(parsed)
    for correction in SPEC['corrections']:
        case = dataset.case(correction['task_id'])
        initial, allowed = runtime.prepare(case, None)
        path = parsed / 'transformed' / (correction['document'] + '.txt')
        text = path.read_text()
        cells = [v.strip() for v in correction['txt_row'].strip('|').split('|')]
        cells[correction['column']] = correction['after']
        row = '| ' + ' | '.join(cells) + ' |'
        assert row in text and correction['txt_row'] not in text
        line = text.splitlines().index(row) + 1
        _, observation = tool_runtime.run_tool('read', {'path': str(path), 'start': line, 'limit': 1},
                                              allowed_roots=runtime.roots, allowed_files=allowed)
        assert observation.strip() == row
        page = tool_runtime._render_parsed_page(str(parsed / 'jsons' / (correction['document'] + '.json')), 15)
        assert row in page.replace(',', '')
        if correction['task_id'] == 'UID0007':
            assert row in initial[-1]['content'].replace(',', '')
    text = (parsed / 'transformed/treasury_bulletin_1950_02.txt').read_text()
    section = text.split('| Budget expenditures 2/ |', 1)[1].split('| Budget surplus, or deficit', 1)[0]
    values = []
    for line in section.splitlines():
        cells = [v.strip() for v in line.strip('|').split('|')]
        if len(cells) != 14 or not cells[0].isdigit():
            continue
        year = int(cells[0])
        values.extend(Decimal(v) for month, v in enumerate(cells[1:13], 1)
                      if (1942, 3) <= (year, month) <= (1948, 10))
    assert len(values) == 80
    with localcontext() as context:
        context.prec = 60
        product = Decimal(1)
        for value in values:
            product *= value
        result = product ** (Decimal(1) / 80)
        assert str(result.quantize(Decimal('0.01'))) == dataset.rows['UID0007']['ground_truth'] == '4962.46'
