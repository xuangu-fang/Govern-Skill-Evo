"""Offline v25.5 prompt wiring and workbook regression fixtures. No model transport."""
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import openpyxl
from openpyxl.formula import Tokenizer

from scripts.runs.v25_4 import run_v25_4_train_test as baseline
from src.skill_evolution.shared.offline_records import offline_records
from src.skill_evolution.v25_2.cli import workbook_path
from src.skill_evolution.v25_4 import stages as previous
from src.skill_evolution.v25_5 import stages
from src.skill_evolution.v25_5.baseline.benchmarks.spreadsheetbench import protocol, scoring

MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ARCHIVE = baseline.EXPERIMENT
PUBLISHED_CONFIG = baseline.ROOT / 'experiments/methods/v25_4' / ARCHIVE.name / 'config'


def check(condition, detail):
    if not condition:
        raise ValueError(detail)


def check_wiring(train, test):
    for config, name in ((train, 'config.json'), (test, 'evaluation/config.json')):
        old = baseline.pipeline.read_config(PUBLISHED_CONFIG / name)
        expected = dict(old, candidate='v25_5_spreadsheetbench',
                        method=dict(old['method'], version='v25_5_selective_updates_prompt_v1'))
        check(config == expected, f'{name} drift')
    phrases = {'diagnosis': ('each source or reference explicitly required', 'exact replacement formula is uncertain'),
               'preconditioner': ('exact operation', 'requirements for subsequent operations'),
               'editor': ('which prior value the new result supersedes', 'after the last operation',
                          'what the intended reader will observe')}
    for name in train['method']['stages']:
        rnd = 'R08' if name == 'diagnosis' else 'R03'
        payload = stages.read(ARCHIVE / 'campaign/rounds' / rnd / name / 'input.json')
        profile = train['actor_profile']
        old = previous.messages_for(name, payload, profile)
        new = stages.messages_for(name, payload, profile)
        if name == 'replay':
            check(new == old, 'Replay messages changed')
            continue
        old_text = (previous.PACKAGE / 'prompts' / (name + '.md')).read_text()
        new_text = (stages.PACKAGE / 'prompts' / (name + '.md')).read_text()
        check(all(phrase in new_text and phrase not in old_text for phrase in phrases[name]), name)
        if name == 'editor':
            check(all(term not in new_text.casefold() for term in ('58147', 'xml', '<v', '<f>', 'openpyxl')),
                  'Editor template prescribes the historical cache implementation')
        check(old[0]['content'].startswith(old_text)
              and new[0]['content'] == new_text + old[0]['content'][len(old_text):]
              and new[1:] == old[1:], f'{name} message envelope or evidence changed')
    task = stages.read(ARCHIVE / 'campaign/rounds/R08/parent_runs/val_53647/trajectory.json')
    messages = protocol.initial_messages(task['task'], task['skill'], task['workbook_preview'], train['actor_profile'])
    check(messages == task['initial_messages'], 'Actor messages differ')


def rewrite_text_caches(source, dest, part, expected):
    # Fixture-only implementation of the requested rule, never imported by the Actor.
    with ZipFile(source) as original, ZipFile(dest, 'w') as output:
        xml = ET.fromstring(original.read(part))
        for address, value in expected.items():
            cell = xml.find(f'.//{MAIN}c[@r="{address}"]')
            nodes = cell.findall(MAIN + 'v')
            node = nodes[0] if nodes else ET.SubElement(cell, MAIN + 'v')
            for duplicate in nodes[1:]:
                cell.remove(duplicate)
            cell.set('t', 'str')
            node.text = value
        for item in original.infolist():
            content = ET.tostring(xml, encoding='utf-8') if item.filename == part else original.read(item)
            output.writestr(item, content)


def verify_final(path, sheet, expected, formulas):
    with_value = openpyxl.load_workbook(path, data_only=True)
    with_formula = openpyxl.load_workbook(path, data_only=False)
    try:
        for address, value in expected.items():
            observed = with_value[sheet][address].value
            formula = with_formula[sheet][address].value
            if formula != formulas[address] or observed != value:
                raise ValueError(f'{sheet}!{address} expected {(formulas[address], value)!r}, observed {(formula, observed)!r}')
    finally:
        with_value.close()
        with_formula.close()


def score(path, task, profile):
    result = scoring.score(path, workbook_path(task['answer_path']), task['answer_region'], profile)
    return [result['correct_cells'], result['total_cells']]


def check_cache(tmp, profile):
    part = 'xl/worksheets/sheet2.xml'  # "Here" in the two archived files
    sources = {'official': ARCHIVE.with_name(ARCHIVE.name + '_test280'),
               'rerun': ARCHIVE.with_name(ARCHIVE.name + '_unique_failures_20261108_101739')}
    results = {}
    for name, folder in sources.items():
        attempt = folder / 'episodes/test_58147/attempts/001'
        task = stages.read(attempt / 'trajectory.json')['task']
        source = attempt / 'code/001/output/result.xlsx'
        inp = openpyxl.load_workbook(workbook_path(task['input_path']), data_only=True)
        expected = {f'J{r}': inp['Here'][f'I{r}'].value.split(' - ')[-2] for r in range(2, 7)}
        inp.close()
        before = score(source, task, profile)
        with ZipFile(source) as z:
            xml = ET.fromstring(z.read(part))
        formulas = {}
        for address, value in expected.items():
            cell = xml.find(f'.//{MAIN}c[@r="{address}"]')
            check([v.text for v in cell.findall(MAIN + 'v')] == [None, value], f'Historical caches at {address}')
            formulas[address] = '=' + cell.find(MAIN + 'f').text
        output = tmp / (name + '.xlsx')
        rewrite_text_caches(source, output, part, expected)
        with ZipFile(output) as z:
            xml = ET.fromstring(z.read(part))
        for address in expected:
            check(len(xml.findall(f'.//{MAIN}c[@r="{address}"]/{MAIN}v')) == 1, f'Duplicate {address}')
        verify_final(output, 'Here', expected, formulas)
        after = score(output, task, profile)
        check((before, after) == ([0, 5], [5, 5]), f'{name} cache scores')
        results[name] = dict(before=before, repaired_copy=after)
    return results


def check_blank_and_persistent_error(tmp):
    source, output = tmp / 'blank.xlsx', tmp / 'blank_checked.xlsx'
    workbook = openpyxl.Workbook()
    formulas = {'A1': '=""', 'A2': '="ready"'}
    for address, formula in formulas.items():
        workbook.active[address] = formula
    workbook.save(source)
    workbook.close()
    expected = {'A1': None, 'A2': 'ready'}
    rewrite_text_caches(source, output, 'xl/worksheets/sheet1.xml', expected)
    verify_final(output, 'Sheet', expected, formulas)
    # Leave the last write with a stale nonempty value; a terminal check must reject it.
    broken = tmp / 'stale.xlsx'
    rewrite_text_caches(output, broken, 'xl/worksheets/sheet1.xml', {'A2': 'stale'})
    try:
        verify_final(broken, 'Sheet', expected, formulas)
    except ValueError as exc:
        check(all(s in str(exc) for s in ('Sheet!A2', 'ready', 'stale')), 'Missing mismatch details')
    else:
        raise ValueError('Persistent mismatch silently accepted')


def check_reference(profile):
    base = ARCHIVE / 'campaign/rounds/R08'
    results = {}
    for side, step in [('parent', '002'), ('candidate', '001')]:
        run = base / (side + '_runs') / 'val_53647'
        task = stages.read(run / 'trajectory.json')['task']
        check('appropriate reference cell' in task['instruction'], 'Missing source requirement')
        path = run / 'code' / step / 'output/result.xlsx'
        inputs = openpyxl.load_workbook(workbook_path(task['input_path']), data_only=True)
        saved = openpyxl.load_workbook(path, data_only=True)
        formulas = openpyxl.load_workbook(path, data_only=False)
        try:
            for row, col in ((7, 'C'), (8, 'D')):
                address = f'E{row}'
                raw = inputs['Sheet1'][f'{col}{row}'].value
                reference = inputs['Sheet1'][col + '5'].value
                tokens = Tokenizer(formulas['Sheet1'][address].value).items
                refs = {t.value.replace('$', '') for t in tokens if t.subtype == 'RANGE'}
                required = {'C5', 'D5'}
                if side == 'parent':
                    check(refs == {f'C{row}', f'D{row}'}, f'Unexpected Parent source at {address}')
                    check(saved['Sheet1'][address].value == raw != reference / raw, 'Parent self-check fixture')
                else:
                    check(required <= refs and saved['Sheet1'][address].value == reference / raw,
                          f'Candidate reference at {address}')
        finally:
            inputs.close()
            saved.close()
            formulas.close()
        results[side] = score(path, task, profile)
    check(results == {'parent': [8, 10], 'candidate': [10, 10]}, 'R08 reference fixture scores')
    return results


def acceptance(train, test, design):
    with offline_records('spreadsheetbench', stages), TemporaryDirectory() as temp:
        check_wiring(train, test)
        cache = check_cache(Path(temp), test['actor_profile'])
        check_blank_and_persistent_error(Path(temp))
        reference = check_reference(train['actor_profile'])
    return dict(status='passed', mode='offline_archived_workbooks_and_prompt_wiring', model_calls=0,
                design_sha256=baseline.pipeline.sha(design), verifier_sha256=baseline.pipeline.sha(Path(__file__)),
                changed_stage_prompts=['diagnosis', 'preconditioner', 'editor'], replay_message_parity=True,
                actor_message_parity=True, train_and_test_config_parity_except_version_labels=True,
                formula_cache_58147=cache, expected_blank_accepted=True, stale_cache_rejected_with_details=True,
                omitted_reference_53647=reference)
