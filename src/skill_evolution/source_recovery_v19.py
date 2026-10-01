"""Explicit, hash-bound recovery for the v19 Diagnosis representation patch only.

Execution manifests retain their original identity because no rollout/evaluator
code changes. The actual replacement sources and every reused artifact are audited
separately. This is not a general 'ignore version mismatch' switch.
"""
from pathlib import Path
import ast
import shutil

from .edit_tracking_v19 import encode, digest, parse
from .evolution_replay_v19 import _load, _file_digest, _lock
from .memory_store_v19 import require, _durable_save, _sync_directory

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = frozenset({
    'src/skill_evolution/memory_generation_prompt_v19.py',
    'src/skill_evolution/memory_generation_v19.py',
    'src/skill_evolution/memory_diagnosis_v19.py',
    'src/skill_evolution/source_recovery_v19.py',
    'src/skill_evolution/evolution_benchmark_v19.py',
    'src/skill_evolution/campaign_v19.py',
    'scripts/run_v19_v4.py',
})


def _sources():
    paths = sorted((ROOT/'src/skill_evolution').glob('*v19.py')) + [ROOT/'scripts/run_v19_v4.py']
    return {str(p.relative_to(ROOT)): _file_digest(p) for p in paths}


def _files(root):
    return {str(p.relative_to(root)): _file_digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def _execution_methods(text):
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BenchmarkEvolutionV19')
    return {n.name: ast.dump(n, include_attributes=False) for n in cls.body
            if isinstance(n, ast.FunctionDef) and n.name in ('prepare', 'evaluate', '_make_manifest', 'preflight')}


def _validate_source_change(original, replacement, source_before):
    require(_sources() == replacement, 'recovery replacement source drift')
    require(_files(source_before) == original, 'original source archive changed')
    changed = {p for p in set(original) | set(replacement) if original.get(p) != replacement.get(p)}
    require(changed <= ALLOWED and 'src/skill_evolution/memory_generation_prompt_v19.py' in changed,
            'recovery is restricted to the Diagnosis representation patch')
    name = 'src/skill_evolution/evolution_benchmark_v19.py'
    require(_execution_methods((source_before/name).read_text()) ==
            _execution_methods((ROOT/name).read_text()), 'rollout/evaluator implementation changed')


class DiagnosisSourceRecovery:
    def __init__(self, receipt_path):
        self.path = Path(receipt_path).resolve()
        self.receipt = _load(self.path)
        self.root = self.path.parent
        self.sha256 = _file_digest(self.path)
        self.validate_sources()

    def validate_sources(self):
        r = self.receipt
        require(r['schema_version'] == 'diagnosis_source_recovery_v19.1', 'unknown recovery protocol')
        require(_file_digest(self.path) == self.sha256, 'recovery receipt changed')
        _validate_source_change(r['original_binding']['source_files'], r['replacement_sources'],
                                self.root/'source_before')
        if 'batch_revision' in r:
            batch = r['batch_revision']
            require(self.path.name == batch['receipt_name'], 'batch receipt name mismatch')
            require(all(_file_digest(self.root/name) == sha for name,sha in batch['prior_files'].items()),
                    'previous recovery chain changed')
            previous = _load(self.root/batch['previous_receipt'])
            require(all(previous[k] == r[k] for k in ('original_binding','preserved_files',
                        'memory_head_before','failed_generation_files','round_id')), 'batch identity changed')
            require(_files(self.root/batch['source_archive']) == previous['replacement_sources'],
                    'previous batch source archive changed')
            changed = {p for p in set(previous['replacement_sources']) | set(r['replacement_sources'])
                       if previous['replacement_sources'].get(p) != r['replacement_sources'].get(p)}
            require(changed <= BATCH_ALLOWED, 'batch recovery changed unrelated source')
            require(_files(self.root/batch['generation_archive']) == batch['generation_files'],
                    'archived Diagnosis batch changed')
            return
        if 'contract_revision' in r:
            prior = r['contract_revision']
            require(_file_digest(self.root/'receipt.json') == prior['prior_receipt_sha256'],
                    'previous recovery receipt changed')
            old = _load(self.root/'receipt.json')
            require(old['original_binding'] == r['original_binding']
                    and old['preserved_files'] == r['preserved_files']
                    and old['memory_head_before'] == r['memory_head_before']
                    and old['failed_generation_files'] == r['failed_generation_files'],
                    'contract revision changed original recovery evidence')
            require(_files(self.root/'contract_source_before') == old['replacement_sources'],
                    'previous replacement sources changed')
            changed = {p for p in set(old['replacement_sources']) | set(r['replacement_sources'])
                       if old['replacement_sources'].get(p) != r['replacement_sources'].get(p)}
            require(changed <= {'src/skill_evolution/memory_generation_prompt_v19.py',
                                'src/skill_evolution/source_recovery_v19.py'},
                    'contract revision changes more than prompt and recovery audit')
            require(_files(self.root/'contract_rejected_generation') == prior['rejected_files'],
                    'contract-rejected response archive changed')

    def execution_manifest(self, current):
        self.validate_sources()
        key = ('evolution_manifest' if current['schema_version'] == 'evolution_manifest_v19.1'
               else 'monitor_manifest')
        original = self.receipt['original_binding'][key]
        expected = parse(encode(original))
        expected['runtime']['v19_source_files'] = {
            p: sha for p, sha in self.receipt['replacement_sources'].items() if p.startswith('src/')}
        require(current == expected, 'recovery cannot change execution config, split or runtime')
        return parse(encode(original))

    def campaign_binding(self, current):
        self.validate_sources()
        original = self.receipt['original_binding']
        expected = {**original, 'source_files': self.receipt['replacement_sources']}
        require(current == expected, 'recovery cannot change campaign binding')
        return parse(encode(original))

    def verify_reused_artifacts(self, output):
        output = Path(output).resolve()
        name = (self.receipt['batch_revision']['receipt_name'] if 'batch_revision' in self.receipt else
                'receipt-contract.json' if 'contract_revision' in self.receipt else 'receipt.json')
        require(self.path == output/'diagnosis_recovery'/name, 'receipt belongs to another output')
        require(_load(output/'binding.json') == self.receipt['original_binding'], 'original binding changed')
        require(all(_file_digest(output/name) == sha for name, sha in self.receipt['preserved_files'].items()),
                'previously completed artifact changed')
        require(_files(self.root/'failed_generation') == self.receipt['failed_generation_files'],
                'failed generation archive changed')
        from .memory_store_v19 import load_memory
        snapshot = load_memory(output/'memory')
        before = self.receipt['memory_head_before']
        require(snapshot.head['revision'] >= before['revision'], 'memory history was rolled back')
        if snapshot.head['revision'] == before['revision']:
            require(snapshot.head == before, 'memory head changed before recovery')
        elif before['revision']:
            record = snapshot.rounds[before['revision']-1]['record']
            require({'artifact_id':record['memory_record_id'], 'sha256':digest(encode(record))}
                    == before['memory_ref'], 'committed memory lineage changed')


def prepare_diagnosis_recovery(*, output, source_before):
    """Archive one wholly rejected first-Diagnosis attempt; no model calls.

    A durable pending receipt makes interruption around the directory rename
    recoverable. Only the explicit CLI --diagnosis-recovery uses the receipt.
    """
    output, source_before = Path(output).resolve(), Path(source_before).resolve()
    root = output/'diagnosis_recovery'
    receipt_path = root/'receipt.json'
    with _lock(output):
        if receipt_path.exists():
            recovery = DiagnosisSourceRecovery(receipt_path)
            recovery.verify_reused_artifacts(output)
            return receipt_path
        pending = root/'pending.json'
        if not pending.exists():
            require(not root.exists(), 'unfinished recovery preparation; inspect before retry')
            binding = _load(output/'binding.json')
            require(_files(source_before) == binding['source_files'], 'source archive does not match original run')
            report = _load(output/'campaign.json')
            require(report['status'] == 'INCOMPLETE' and report['error_type'] == 'BadRequestError'
                    and report['failed_stage'] == 'MEMORY_GENERATION', 'not a rejected Diagnosis request')
            round_id = report['active_round']
            generation = output/round_id/'generation'
            require(_load(generation/'validation.json') == {'status':'INCOMPLETE','error_type':'BadRequestError'},
                    'generation was not rejected by gateway')
            require(set(_files(generation)) == {'input.json','validation.json','diagnosis-000/request.json'},
                    'recovery must not discard a completed response or later request')
            preserved = {'binding.json': _file_digest(output/'binding.json')}
            # Previous round archives and the current completed Parent/group stay immutable.
            for prior in sorted(output.glob('round-*')):
                paths = [prior] if prior.name < round_id else [prior/'parent_evolution', prior/'grouping']
                for path in paths:
                    if path.exists():
                        preserved.update({str(path.relative_to(output)/name): sha for name, sha in _files(path).items()
                                          if not name.endswith('.lock')})
            r = {'schema_version':'diagnosis_source_recovery_v19.1',
                 'reason':'Gateway rejected oversized first Diagnosis; lossless reference projection, no evidence truncation',
                 'original_binding':binding, 'replacement_sources':_sources(), 'round_id':round_id,
                 'memory_head_before':_load(output/'memory/head.json'), 'preserved_files':preserved,
                 'failed_generation_files':_files(generation)}
            _validate_source_change(binding['source_files'], r['replacement_sources'], source_before)
            root.mkdir()
            shutil.copytree(source_before, root/'source_before')
            _durable_save(pending, r)
        r = _load(pending)
        require(_sources() == r['replacement_sources'], 'sources changed during recovery preparation')
        generation = output/r['round_id']/'generation'
        archive = root/'failed_generation'
        if generation.exists():
            require(not archive.exists() and _files(generation) == r['failed_generation_files'],
                    'generation changed during recovery preparation')
            generation.rename(archive)
            _sync_directory(generation.parent)
            _sync_directory(root)
        require(_files(archive) == r['failed_generation_files'], 'failed attempt archive incomplete')
        _durable_save(receipt_path, r)
        recovery = DiagnosisSourceRecovery(receipt_path)
        recovery.verify_reused_artifacts(output)
        return receipt_path


def prepare_contract_recovery(*, output, source_before):
    """One explicit prompt correction after a completed but rejected first response.

    Keep both earlier receipts/attempts immutable. No normalization of the rejected
    response and no retry of any accepted group are permitted here.
    """
    output, source_before = Path(output).resolve(), Path(source_before).resolve()
    root = output/'diagnosis_recovery'
    path, pending = root/'receipt-contract.json', root/'contract_pending.json'
    with _lock(output):
        if path.exists():
            obj = DiagnosisSourceRecovery(path)
            obj.verify_reused_artifacts(output)
            return path
        if not pending.exists():
            previous = _load(root/'receipt.json')
            require(_files(source_before) == previous['replacement_sources'], 'previous replacement archive mismatch')
            changed = {p for p in set(previous['replacement_sources']) | set(_sources())
                       if previous['replacement_sources'].get(p) != _sources().get(p)}
            require(changed <= {'src/skill_evolution/memory_generation_prompt_v19.py',
                                'src/skill_evolution/source_recovery_v19.py'}, 'unexpected contract recovery change')
            _validate_source_change(previous['original_binding']['source_files'], _sources(), root/'source_before')
            report = _load(output/'campaign.json')
            require(report['status'] == 'INCOMPLETE' and report['error_type'] == 'DiagnosisRejected'
                    and report['failed_stage'] == 'MEMORY_GENERATION'
                    and report['active_round'] == previous['round_id'], 'not the expected rejected Diagnosis')
            generation = output/previous['round_id']/'generation'
            require(_load(generation/'validation.json') == {'status':'INCOMPLETE','error_type':'DiagnosisRejected'},
                    'expected local Diagnosis rejection')
            require(set(_files(generation)) == {'input.json','validation.json','diagnosis-000/request.json',
                    'diagnosis-000/response.json','diagnosis-000/response_complete.json'},
                    'cannot discard later or accepted model calls')
            from .memory_generation_v19 import _read_call
            from .memory_diagnosis_v19 import validate_memory_diagnosis_response
            from .group_diagnosis_input_v17 import GroupDiagnosisInput
            from .information_boundary_v15 import _seal
            from .diagnosis_validation_v18 import DiagnosisRejected
            call = generation/'diagnosis-000'
            raw = _read_call(call, _load(call/'request.json'))
            item = _load(generation/'input.json')['requests'][0]
            request = GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', item['payload']), encode(item['provenance']))
            try:
                validate_memory_diagnosis_response(raw, request=request)
            except DiagnosisRejected as exc:
                require(str(exc) == 'LINKAGE: NO_ISSUE contradicts observed failure or violation supervision',
                        'unexpected rejection; inspect before recovery')
            else:
                raise ValueError('response was not rejected; must not rerun it')
            require(_load(output/'memory/head.json') == previous['memory_head_before'], 'memory already advanced')
            require(all(_file_digest(output/name) == sha for name,sha in previous['preserved_files'].items()),
                    'completed artifacts changed')
            require(_files(root/'failed_generation') == previous['failed_generation_files'], 'earlier failed archive changed')
            r = {**previous, 'replacement_sources':_sources(), 'contract_revision':{
                'prior_receipt_sha256':_file_digest(root/'receipt.json'), 'rejected_files':_files(generation),
                'reason':'Unify all-observation status scope and exactly-once edit review; validators unchanged'}}
            shutil.copytree(source_before, root/'contract_source_before')
            _durable_save(pending, r)
        r = _load(pending)
        require(_sources() == r['replacement_sources'], 'sources changed during contract recovery preparation')
        generation, archive = output/r['round_id']/'generation', root/'contract_rejected_generation'
        if generation.exists():
            require(not archive.exists() and _files(generation) == r['contract_revision']['rejected_files'],
                    'rejected attempt changed during preparation')
            generation.rename(archive)
            _sync_directory(generation.parent)
            _sync_directory(root)
        require(_files(archive) == r['contract_revision']['rejected_files'], 'rejected archive incomplete')
        _durable_save(path, r)
        obj = DiagnosisSourceRecovery(path)
        obj.verify_reused_artifacts(output)
        return path


BATCH_ALLOWED = frozenset({
    'src/skill_evolution/memory_generation_prompt_v19.py',
    'src/skill_evolution/memory_generation_v19.py',
    'src/skill_evolution/memory_diagnosis_v19.py',
    'src/skill_evolution/source_recovery_v19.py',
})


def prepare_diagnosis_batch(*, output, previous_receipt, source_before, batch_id, reason):
    """Explicitly archive an entire failed Diagnosis batch, then regenerate all groups.

    This is never an automatic retry. Accepted prefix responses remain auditable
    in the archive but are not reused under a different prompt. Refuse Editor,
    Candidate, incomplete transport or successful-batch replacement.
    """
    import re
    require(type(batch_id) is str and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', batch_id), 'invalid batch ID')
    require(type(reason) is str and bool(reason.strip()), 'batch restart reason required')
    output, source_before = Path(output).resolve(), Path(source_before).resolve()
    root = output/'diagnosis_recovery'
    previous_path = Path(previous_receipt).resolve()
    require(previous_path.parent == root and previous_path.is_file(), 'previous receipt must belong to this run')
    path = root/f'receipt-batch-{batch_id}.json'
    pending = root/f'pending-batch-{batch_id}.json'
    require(previous_path != path, 'batch cannot reference itself')
    with _lock(output):
        if path.exists():
            obj = DiagnosisSourceRecovery(path)
            obj.verify_reused_artifacts(output)
            return path
        if not pending.exists():
            previous = _load(previous_path)
            # Validate the existing receipt chain against its own frozen sources
            # before creating a new link. Never bless altered archives by hashing
            # them for the first time into the new receipt.
            import subprocess, sys
            verifier = (
                'from pathlib import Path; import sys; '
                'import src.skill_evolution.source_recovery_v19 as m; '
                'm.ROOT=Path(sys.argv[1]); '
                'r=m.DiagnosisSourceRecovery(sys.argv[2]); '
                'r.verify_reused_artifacts(sys.argv[3])')
            completed = subprocess.run([sys.executable, '-c', verifier, str(source_before),
                                        str(previous_path), str(output)], capture_output=True, text=True)
            require(completed.returncode == 0, 'previous recovery chain verification failed: ' + completed.stderr)
            require(_files(source_before) == previous['replacement_sources'], 'previous source snapshot mismatch')
            current = _sources()
            changed = {p for p in set(current) | set(previous['replacement_sources'])
                       if current.get(p) != previous['replacement_sources'].get(p)}
            require(changed <= BATCH_ALLOWED and
                    'src/skill_evolution/memory_generation_prompt_v19.py' in changed,
                    'batch restart requires an explicit prompt correction only')
            _validate_source_change(previous['original_binding']['source_files'], current, root/'source_before')
            require(_load(output/'binding.json') == previous['original_binding'], 'original binding changed')
            require(_load(output/'memory/head.json') == previous['memory_head_before'], 'memory already advanced')
            require(all(_file_digest(output/name) == sha for name,sha in previous['preserved_files'].items()),
                    'completed artifacts changed')
            report = _load(output/'campaign.json')
            require(report['status'] == 'INCOMPLETE' and report['failed_stage'] == 'MEMORY_GENERATION'
                    and report['active_round'] == previous['round_id'], 'batch is not stopped in generation')
            round_root = output/previous['round_id']
            require(not any((round_root/name).exists() for name in
                    ('candidate_evolution','attribution','monitor_private','round_result.json')),
                    'downstream execution already exists')
            generation = round_root/'generation'
            require(_load(generation/'validation.json').get('status') == 'INCOMPLETE', 'batch is not incomplete')
            from .memory_generation_v19 import _read_call
            from .memory_diagnosis_v19 import validate_memory_diagnosis_response
            from .group_diagnosis_input_v17 import GroupDiagnosisInput
            from .information_boundary_v15 import _seal
            from .diagnosis_validation_v18 import DiagnosisRejected
            from .memory_store_v19 import MemoryRejected
            inputs = _load(generation/'input.json')['requests']
            dirs = sorted(p for p in generation.glob('diagnosis-*')
                          if re.fullmatch(r'diagnosis-[0-9]{3}', p.name))
            require(bool(dirs) and len(dirs) <= len(inputs), 'no completed Diagnosis response to audit')
            expected = {'input.json','validation.json'}
            # Preserve previously explicitly archived unanswered calls; never
            # mistake them for validated groups or discard a completed response.
            for attempt in generation.glob('diagnosis-*.attempt-*'):
                match = re.fullmatch(r'(diagnosis-[0-9]{3})[.]attempt-[1-9][0-9]*', attempt.name)
                require(match is not None and (generation/match[1]) in dirs,
                        'orphan or invalid archived attempt')
                require(set(_files(attempt)) == {'request.json'}, 'archived attempt contains response or unknown artifacts')
                require(_load(attempt/'request.json') == _load(generation/match[1]/'request.json'),
                        'archived attempt request differs from active call')
                expected.add(attempt.name+'/request.json')
            groups, versions = [], set()
            for index, call in enumerate(dirs):
                require(call.name == f'diagnosis-{index:03d}', 'Diagnosis prefix is not contiguous')
                req = _load(call/'request.json')
                raw = _read_call(call, req)
                versions.add((req['prompt_version'],req['prompt_sha256']))
                item = inputs[index]
                request = GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT',item['payload']),encode(item['provenance']))
                error = None
                try:
                    validate_memory_diagnosis_response(raw, request=request)
                except (DiagnosisRejected, MemoryRejected) as exc:
                    error = {'type':type(exc).__name__, 'message':str(exc)}
                require(error is None or index == len(dirs)-1, 'responses exist after rejected group')
                groups.append({'index':index,'status':'REJECTED' if error else 'VALID', 'error':error})
                expected.update(f'{call.name}/{name}' for name in ('request.json','response.json','response_complete.json'))
            require(len(versions) == 1, 'old batch mixes prompt versions')
            require(groups[-1]['status'] == 'REJECTED', 'no local contract rejection; do not rerun valid batch')
            require(set(_files(generation)) == expected, 'unexpected generation artifacts; no Editor or later output permitted')
            archive_name, source_name = f'batch-{batch_id}-generation', f'batch-{batch_id}-source-before'
            require(not (root/archive_name).exists() and not (root/source_name).exists(), 'batch archive already exists')
            prior_files = _files(root)
            r = {**previous, 'replacement_sources':current, 'batch_revision':{
                'receipt_name':path.name, 'previous_receipt':previous_path.name, 'prior_files':prior_files,
                'source_archive':source_name,'generation_archive':archive_name,
                'generation_files':_files(generation), 'group_validation':groups,
                'old_prompt_version':next(iter(versions))[0], 'reason':reason,
                'policy':'REGENERATE_ALL_GROUPS_NO_MIXED_PROMPT_BATCH'}}
            shutil.copytree(source_before, root/source_name)
            _durable_save(pending,r)
        r = _load(pending)
        require(_sources() == r['replacement_sources'], 'sources changed during batch preparation')
        batch = r['batch_revision']
        require(all(_file_digest(root/name) == sha for name,sha in batch['prior_files'].items()),
                'prior recovery artifacts changed')
        generation, archive = output/r['round_id']/'generation', root/batch['generation_archive']
        if generation.exists():
            require(not archive.exists() and _files(generation) == batch['generation_files'], 'batch changed during preparation')
            generation.rename(archive)
            _sync_directory(generation.parent)
            _sync_directory(root)
        require(_files(archive) == batch['generation_files'], 'batch archive incomplete')
        _durable_save(path,r)
        obj = DiagnosisSourceRecovery(path)
        obj.verify_reused_artifacts(output)
        return path
