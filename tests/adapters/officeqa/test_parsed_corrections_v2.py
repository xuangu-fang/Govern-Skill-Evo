"""Evidence-preserving repairs; no models or external requests."""
import hashlib
import json
from pathlib import Path
import re
import socket

import pytest

from scripts.benchmarks.officeqa.correct_parsed_v2 import patch_file


ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((ROOT / 'benchmarks/officeqa/parsed_corrections_v2.json').read_text())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('No network or model clients during correction tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    import openai
    monkeypatch.setattr(openai, 'OpenAI', denied)
    monkeypatch.setattr(openai, 'AzureOpenAI', denied)


@pytest.fixture
def corpora():
    paths = tuple(ROOT / f'data/officeqa/corrected_v{v}/treasury_bulletins_parsed' for v in (1, 2))
    if not all(p.exists() for p in paths):
        pytest.skip('Build both offline corpus revisions first')
    return paths


def test_source_ambiguity_and_output_drift_are_rejected():
    source = b'original row\noriginal row\n'
    patch = {'path': 'document.txt', 'before_sha256': hashlib.sha256(source).hexdigest(),
             'after_sha256': 'not-a-valid-output',
             'replacements': [{'before': 'original row', 'after': 'fixed row'}]}
    with pytest.raises(ValueError, match='source hash'):
        patch_file(b'drift', patch)
    with pytest.raises(ValueError, match='one original span'):
        patch_file(source, patch)
    patch['replacements'][0]['before'] = source.decode()
    with pytest.raises(ValueError, match='output hash'):
        patch_file(source, patch)


def test_actual_patches_are_exact_and_preserve_json_metadata(corpora):
    old, new = corpora
    for patch in SPEC['files']:
        before, after = (old / patch['path']).read_bytes(), (new / patch['path']).read_bytes()
        assert patch_file(before, patch) == after
        with pytest.raises(ValueError, match='source hash'):
            patch_file(after, patch)  # Never silently patch an already edited source.
        if patch['path'].endswith('.json'):
            a, b = json.loads(before), json.loads(after)
            assert len(a['document']['elements']) == len(b['document']['elements'])
            for ea, eb in zip(a['document']['elements'], b['document']['elements']):
                ea.pop('content', None); eb.pop('content', None)
            assert a == b  # Page IDs, element IDs, bbox, descriptions and metadata.


def test_restored_column_preserves_other_values_and_aligns_headers(corpora):
    from skilladam.benchmarks.officeqa import tool_runtime
    old, new = corpora
    name = 'treasury_bulletin_1939_11'
    a, b = [json.loads((p / 'jsons' / f'{name}.json').read_text())['document']['elements'][49]['content']
            for p in (old, new)]
    def rows(table):
        return [re.findall(r'<td[^>]*>(.*?)</td>', row) for row in re.findall(r'<tr[^>]*>.*?</tr>', table)
                if '<td' in row]
    ar, br = rows(a), rows(b)
    assert len(ar) == len(br) == 20
    assert [r[7] for r in br] == ['225','162','179','216','210','208','195','17','14','15',
                                  '20','16','15','13','17','14','17','19','16','17']
    assert all(len(r) == 15 for r in br)
    assert [r[:7] + r[8:] for r in br] == ar
    page = tool_runtime._render_parsed_page(str(new / 'jsons' / f'{name}.json'), 14)
    assert 'Receipts > Customs | Receipts > Miscellaneous receipts | Expenditures 2/ > Total' in page
    assert 'Expenditures 2/ > Debt retirement | Excess of receipts' in page
    text = (new / 'transformed' / f'{name}.txt').read_text()
    for r in br:
        line = '| ' + ' | '.join(v.replace(',', '') for v in r) + ' |'
        assert line in page.replace(',', '') and line in text


def test_all_17_cells_match_renderer_and_actual_read_tool(corpora):
    from skilladam.benchmarks.officeqa import tool_runtime
    from src.adapters.officeqa.data import Dataset
    from src.adapters.officeqa.runtime import Runtime
    _, new = corpora
    dataset = Dataset(ROOT / 'data/officeqa/prepared_v2'); runtime = Runtime(new)
    def normalize(s):
        return re.sub(r'(?<=\d)\.0+$', '', s.strip().replace(',', ''))
    grouped = {}
    for correction in SPEC['cell_corrections']:
        grouped.setdefault((correction['document'], correction['parsed_row']), []).append(correction)
    assert sum(map(len, grouped.values())) == 17
    for (doc, before), corrections in grouped.items():
        expected = [normalize(c) for c in before.strip('|').split('|')]
        for correction in corrections:
            assert expected[correction['column_index']] == correction['parsed_value']
            expected[correction['column_index']] = correction['pdf_value']
        while expected[-1] in ('', 'nan'):
            expected.pop()
        path = new / 'transformed' / f'{doc}.txt'
        found = []
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if not line.startswith('|'):
                continue
            cells = [normalize(c) for c in line.strip('|').split('|')]
            while cells and cells[-1] in ('', 'nan'):
                cells.pop()
            if cells == expected:
                found.append((i, line))
        assert len(found) == 1
        f = corrections[0]; initial, allowed = runtime.prepare(dataset.case(f['related_task']), None)
        _, observed = tool_runtime.run_tool('read', {'path': str(path), 'start': found[0][0], 'limit': 1},
                                            allowed_roots=runtime.roots, allowed_files=allowed)
        assert observed.strip() == found[0][1]
        page = tool_runtime._render_parsed_page(str(new / 'jsons' / f'{doc}.json'), f['pdf_page'])
        expected_line = '| ' + ' | '.join(expected) + ' |'
        assert expected_line in page.replace(',', '')
        assert expected_line in initial[-1]['content'].replace(',', '')
