"""Materialize and audit OfficeQA without network, credentials, or model execution.

Run from the project root: conda run -n OfficeQA python -m
scripts.benchmarks.officeqa.prepare [--check]
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path


NETWORK_ATTEMPTS = []


def deny_network(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        NETWORK_ATTEMPTS.append(event)
        raise RuntimeError('Network disabled during OfficeQA offline preparation')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_or_check(path, text, check):
    if path.exists():
        if path.read_text() != text:
            raise ValueError(f'Existing generated file differs: {path}')
    elif check:
        raise ValueError(f'Missing generated file: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run(root, check=False):
    # Install the guard BEFORE importing any upstream runtime/model modules.
    sys.addaudithook(deny_network)
    from skillopt.config import load_config
    from skillopt.envs.officeqa.dataloader import OfficeQADataLoader, _normalize_row
    from skillopt.envs.officeqa.evaluator import evaluate
    from skillopt.envs.officeqa import rollout, tool_runtime
    from src.adapters.officeqa.local import aligned_item, LocalDocuments, lines
    import yaml

    def forbidden_model(*args, **kwargs):
        raise RuntimeError('Model execution is forbidden in offline preparation')
    rollout.chat_target_messages = forbidden_model
    rollout.run_target_exec = forbidden_model
    base = root / 'data/officeqa'
    raw = base / 'raw'
    output = base / 'prepared_v1'
    report_dir = root / 'artifacts/benchmarks/officeqa/offline_v1'
    upstream = root / 'external/SkillOpt'
    manifest = json.loads((base / 'download_manifest.json').read_text())
    for entry in manifest['files']:
        path = base / entry['path']
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Download integrity mismatch: {entry["path"]}')
    # Verify installed runtime source against the local pinned implementation.
    source_hashes = {}
    for module in (tool_runtime, rollout, sys.modules[OfficeQADataLoader.__module__],
                   sys.modules[evaluate.__module__], sys.modules[load_config.__module__],
                   sys.modules['skillopt.datasets.base'], sys.modules['skillopt.prompts']):
        relative = Path(*module.__name__.split('.')).with_suffix('.py')
        if Path(module.__file__).name == '__init__.py':
            relative = Path(*module.__name__.split('.')) / '__init__.py'
        if digest(Path(module.__file__)) != digest(upstream / relative):
            raise ValueError(f'Installed SkillOpt source differs: {relative}')
        source_hashes[str(relative)] = digest(upstream / relative)
    for path in sorted((upstream/'skillopt/envs/officeqa').rglob('*.md')):
        installed = Path(tool_runtime.__file__).parent / path.relative_to(upstream/'skillopt/envs/officeqa')
        if digest(installed) != digest(path):
            raise ValueError(f'Installed OfficeQA prompt differs: {path}')
        source_hashes[str(path.relative_to(upstream))] = digest(path)
    for path in (upstream/'configs/officeqa/default.yaml',upstream/'configs/_base_/default.yaml'):
        source_hashes[str(path.relative_to(upstream))] = digest(path)
    rows = list(csv.DictReader((raw / 'officeqa_full.csv').open(encoding='utf-8-sig', newline='')))
    by_id = {r['uid']: r for r in rows}
    if len(rows) != 246 or len(by_id) != 246:
        raise ValueError('Expected 246 distinct OfficeQA Full tasks')
    changes, page_audits, counts, seen = [], [], {}, set()
    parsed_root = raw / 'treasury_bulletins_parsed'
    skill = (upstream / 'skillopt/envs/officeqa/skills/initial.md').read_text()
    for split, count in [('train', 50), ('val', 24), ('test', 172)]:
        ids = json.loads((base / f'skillopt_splits/{split}/items.json').read_text())
        if len(ids) != count:
            raise ValueError(f'Incorrect split size: {split}')
        native, aligned = [], []
        for identity in ids:
            tid = identity['id']
            if tid in seen or tid not in by_id:
                raise ValueError(f'Duplicate or missing task: {tid}')
            seen.add(tid)
            source = by_id[tid]
            for key in ('source_files', 'source_docs'):
                if lines(source[key]) != lines(identity[key]):
                    raise ValueError(f'Manifest provenance differs: {tid}/{key}')
            if source['difficulty'] != identity['category']:
                raise ValueError(f'Difficulty differs: {tid}')
            item = _normalize_row({**source, 'split': split})
            if not item['question'] or not item['ground_truth']:
                raise ValueError(f'Incomplete task: {tid}')
            repaired, refs, legacy = aligned_item(item)
            native.append(item); aligned.append(repaired)
            if refs != legacy:
                changes.append({'task_id': tid, 'split': split, 'original_refs': legacy, 'aligned_refs': refs,
                                'original_source_files': item['source_files'], 'aligned_source_files': repaired['source_files']})
            documents = LocalDocuments(parsed_root, repaired)
            context = documents.pages(repaired)
            # Actual upstream input construction; no rollout or answer generation.
            user = rollout._build_user(repaired, documents.paths, oracle_context=context)
            system = rollout._build_system(skill, search_mode='offline', use_local_tools=True)
            if not context or '## Question' not in user or '## Skill' not in system:
                raise ValueError(f'Missing model input: {tid}')
            redacted = {**repaired, 'ground_truth':'OFFLINE_PRIVATE_ANSWER_SENTINEL',
                        'answers':['OFFLINE_PRIVATE_ANSWER_SENTINEL']}
            if rollout._build_user(redacted,documents.paths,oracle_context=context) != user:
                raise ValueError(f'Grading answer affected Actor input: {tid}')
            _, found = documents.call('glob', {'pattern': '*.txt'})
            if set(found.splitlines()) != set(documents.paths):
                raise ValueError(f'Incorrect tool allowlist: {tid}')
            for filename in documents.paths:
                _, excerpt = documents.call('read', {'path': filename, 'start': 1, 'limit': 80})
                expected = ''.join(Path(filename).read_text().splitlines(keepends=True)[:80])[:4000] or '[empty file]'
                if excerpt != expected:
                    raise ValueError(f'Read mismatch: {tid}')
                # Deterministic substring from the document, independent of answers.
                first = next(x.strip() for x in Path(filename).read_text().splitlines() if x.strip())[:24]
                _, hits = documents.call('grep', {'path': filename, 'pattern': first.swapcase()})
                if hits == '[no matches]' or not hits:
                    raise ValueError(f'Grep mismatch: {tid}')
            _, denied = documents.call('read', {'path': str(raw / 'officeqa_full.csv')})
            if 'path not allowed' not in denied:
                raise ValueError('Answer file was accessible through tools')
            lengths = [len(tool_runtime._render_parsed_page(str(parsed_root / 'jsons' / (Path(n).stem + '.json')), p)) for n,p,_ in refs]
            page_audits.append({'task_id': tid, 'split': split, 'source_pages': len(refs),
                               'page_characters': lengths, 'context_characters': len(context),
                               'visible_page_headers': [f'{n} page {p}' for n,p,_ in refs if f'### {n} page {p}\n' in context],
                               'system_sha256':hashlib.sha256(system.encode()).hexdigest(),
                               'user_sha256':hashlib.sha256(user.encode()).hexdigest(),
                               'page_truncated': any(n > 24000 for n in lengths),
                               'total_truncated': 'oracle parsed page context truncated' in context})
        counts[split] = len(native)
        for profile, items in [('skillopt_original', native), ('source_aligned', aligned)]:
            target = output / profile / split / 'items.json'
            write_or_check(target, json.dumps(items, ensure_ascii=False, indent=2)+'\n', check)
            loader = OfficeQADataLoader(split_dir=str(output/profile), split_mode='split_dir')
            loaded = loader.load_split_items(str(target.parent))
            if loaded != items:
                raise ValueError(f'Upstream loader roundtrip differs: {split}/{profile}')
    if seen != set(by_id):
        raise ValueError('Split coverage differs')
    for profile in ('skillopt_original', 'source_aligned'):
        cfg = {'_base_': str(upstream/'configs/officeqa/default.yaml'),
               'env': {'split_mode':'split_dir','split_dir': str(output/profile),
                       'data_dirs':[str(parsed_root)], 'search_mode':'offline','use_local_tools':True,
                       'skill_init': str(upstream/'skillopt/envs/officeqa/skills/initial.md') }}
        cfgpath = output / f'{profile}.yaml'
        write_or_check(cfgpath, yaml.safe_dump(cfg, sort_keys=False), check)
        effective = load_config(str(cfgpath))
        loader = OfficeQADataLoader(split_dir=str(output/profile), split_mode='split_dir')
        loader.setup({})
        if loader.get_train_size() != 50 or effective['env']['search_mode'] != 'offline':
            raise ValueError('Effective config/loader mismatch')
    scoring = [{'prediction':p,'gold':g,**evaluate(p,g)} for p,g in
               [('1,000','1000'),('1.0','1'),('25%','0.25'),('1 million','1 billion')]]
    generated = {str(p.relative_to(base)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    report = {'status':'passed','scope':'local data, input construction and tools only; not model/experiment readiness',
              'dataset_revision':manifest['revision'],'skillopt_commit':manifest['skillopt_commit'],
              'source_note':'SkillOpt base commit plus checked local source hashes; config.py has a pre-existing local modification.',
              'python':platform.python_version(),'environment':sys.prefix,
              'packages':{d.metadata['Name']:d.version for d in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata['Name'].lower())},
              'verified_download_files':len(manifest['files']), 'counts':counts,
              'source_page_links':sum(x['source_pages'] for x in page_audits),
              'mapping_changes':changes,'page_audits':page_audits,'scoring_examples':scoring,
              'upstream_source_hashes':source_hashes,'generated_sha256':generated,
              'network_attempts':NETWORK_ATTEMPTS,'model_calls':0,'dataset_rollouts':0,
              'limitations':['Original source mapping and EM quirks are retained in skillopt_original.',
                             'source_aligned changes source_files associations and adds files explicitly named by existing source URLs; raw data is unchanged.',
                             'Native SkillOpt tools permit an empty allowlist; the separately tested LocalDocuments helper rejects it. Native YAML does not replace upstream tool dispatch.',
                             'No semantic answer correctness or online tool-calling support has been evaluated.']}
    write_or_check(report_dir/'report.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n',check)
    print(json.dumps({k:report[k] for k in ('status','counts','source_page_links','model_calls','dataset_rollouts')},ensure_ascii=False))
    print('Report:', report_dir/'report.json')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing outputs without modifying them')
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[3], check=args.check)
