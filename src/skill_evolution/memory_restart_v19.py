"""Offline, audited restart after round-01 Current Diagnosis. Never calls a model."""
from copy import deepcopy
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timezone

from .edit_tracking_v19 import encode, digest
from .evolution_replay_v19 import _load, _file_digest, _lock, load_parent_experiences
from .memory_store_v19 import require, initialize_memory, load_memory, _durable_save
from .campaign_v19 import _binding, source_manifest

ENTRYPOINT = {'protocol':'unified_run_v19.1','generation':'local','attribution':'pair'}
# Changes to rollout, grouping or discovery require a different migration.
PRESERVED_SOURCES = ('evolution_benchmark', 'evolution_replay', 'monitor_campaign',
                     'current_diagnosis', 'review_prompt', 'grouping_campaign')


def files(root):
    root = Path(root)
    require(not any(p.is_symlink() for p in root.rglob('*')), 'migration rejects symlinks')
    return {str(p.relative_to(root)):_file_digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def compatible_manifest(old, current):
    left, right = deepcopy(old), deepcopy(current)
    for value in (left, right):
        value.get('runtime', {}).pop('v19_source_files', None)
    require(left == right, 'execution configuration/freeze/tasks changed; cannot reuse Parent')


class MemoryRestart:
    def __init__(self, receipt_path):
        self.path = Path(receipt_path).resolve()
        self.receipt = _load(self.path)
        self.sha256 = _file_digest(self.path)
        require(self.receipt['schema_version']=='memory_restart_v19.1', 'unknown restart protocol')
        self.validate_sources()

    def validate_sources(self):
        require(_file_digest(self.path)==self.sha256, 'migration receipt changed')
        require(source_manifest()==self.receipt['replacement_sources'], 'migration source drift')

    def execution_manifest(self, current):
        key = 'evolution_manifest' if current['schema_version']=='evolution_manifest_v19.1' else 'monitor_manifest'
        require(current==self.receipt['current_manifests'][key], 'migration runtime changed')
        # Preserve original evidence namespaces. Actual replacement code is bound
        # independently in receipt and campaign binding, not disguised as old code.
        return deepcopy(self.receipt['original_binding'][key])

    def campaign_binding(self, current):
        self.validate_sources()
        return {**current, 'memory_restart_sha256':self.sha256}

    def verify_reused_artifacts(self, output):
        output = Path(output).resolve()
        require(self.path==output/'migration.json', 'migration belongs to another output')
        self.validate_sources()
        require(all(_file_digest(output/name)==sha for name,sha in self.receipt['reused_files'].items()),
                'reused upstream artifact changed')
        archive = Path(self.receipt['archive'])
        require(files(archive)==self.receipt['archive_files'], 'whole-run archive changed')


class _ManifestView:
    def __init__(self, backend, manifest):
        self.backend, self.saved_manifest = backend, manifest
    def manifest(self):
        return deepcopy(self.saved_manifest)
    def __getattr__(self, name):
        return getattr(self.backend, name)


def prepare_memory_restart(*, source, archive, output, evolution, monitor):
    """Publish archive and fresh checkpoint only after offline validation.

    Source is never edited. Existing destinations are refused. Incomplete work is
    retained in uniquely named .pending directories for inspection, never reused.
    """
    from .experience_cards_v17 import build_experience_cards
    from .grouping_campaign_v19 import run_campaign_grouping
    from .current_diagnosis_v19 import build_current_diagnosis_inputs, validate_current_findings
    from .review_prompt_v19 import build_current_diagnosis_request
    from .separated_generation_v19 import _contract_call

    source, archive, output = (Path(p).resolve() for p in (source, archive, output))
    paths = (source, archive, output)
    require(all(a!=b and a not in b.parents and b not in a.parents
                for i,a in enumerate(paths) for b in paths[i+1:]), 'migration paths must be disjoint')
    require(source.is_dir(), 'source run missing')
    def no_model(*args, **kwargs):
        raise ValueError('offline migration requires complete reusable responses; model dispatch forbidden')
    with _lock(source), _lock(archive), _lock(output):
        require(not archive.exists() and not output.exists(), 'archive/output already exists; refusing overwrite')
        old = _load(source/'binding.json')
        require(old.get('entrypoint')==ENTRYPOINT, 'source is not a unified local/pair run')
        current_sources = source_manifest()
        for name in PRESERVED_SOURCES:
            path = 'src/skill_evolution/'+name+'_v19.py'
            require(old['source_files'].get(path)==current_sources[path], 'upstream implementation changed: '+name)
        actual = {'evolution_manifest':evolution.manifest(), 'monitor_manifest':monitor.manifest()}
        for key, value in actual.items():compatible_manifest(old[key], value)
        require(digest(old['initial_skill'])==old['initial_skill_sha256'], 'initial Skill hash mismatch')
        frozen_skill = actual['evolution_manifest'].get('runtime', {}).get('initial_skill_sha256')
        require(frozen_skill is None or frozen_skill==old['initial_skill_sha256'], 'initial Skill differs from frozen benchmark')
        # Verify committed history before copying; it is archived, never imported.
        load_memory(source/'memory')
        original_files = files(source)
        staging_archive = archive.with_name('.'+archive.name+'.pending-'+uuid.uuid4().hex)
        shutil.copytree(source, staging_archive)
        require(files(staging_archive)==original_files==files(source), 'whole-run archive verification failed')
        stage = output.with_name('.'+output.name+'.pending-'+uuid.uuid4().hex)
        stage.mkdir()
        root = stage/'round-01'; root.mkdir()
        for name in ('parent_evolution','grouping'):
            shutil.copytree(staging_archive/'round-01'/name, root/name)
        evo = _ManifestView(evolution, old['evolution_manifest'])
        mon = _ManifestView(monitor, old['monitor_manifest'])
        sources, scope = load_parent_experiences(run_id=old['run_id'],round_id='round-01',
            parent_skill=old['initial_skill'],backend=evo,artifact_dir=root/'parent_evolution')
        batch = build_experience_cards(sources,scope=scope,max_input_chars=old['config']['max_grouping_chars'])
        grouping = run_campaign_grouping(batch,scope=scope,artifact_dir=root/'grouping',resume=True,transport=no_model)
        requests = build_current_diagnosis_inputs(run_id=old['run_id'],round_id='round-01',
            parent_skill=old['initial_skill'],backend=evo,parent_dir=root/'parent_evolution',grouping_result=grouping)
        old_generation = staging_archive/'round-01'/'generation'
        old_input = _load(old_generation/'input.json')
        require(old_input['current_inputs']==[{'payload':r.payload,'provenance':r.provenance} for r in requests],
                'Current Diagnosis input changed')
        generation = root/'generation'; generation.mkdir()
        for i, request in enumerate(requests):
            name = f'current-{i:03d}'
            for path in old_generation.glob(name+'*'):
                if path.is_dir():shutil.copytree(path, generation/path.name)
                else:shutil.copy2(path, generation/path.name)
            result = _contract_call(generation/name, build_current_diagnosis_request(request),
                lambda raw,r=request:validate_current_findings(raw,request=r),no_model)
            require(_load(generation/(name+'-findings.json'))==result.payload, 'saved Findings changed')
        initialize_memory(store_dir=stage/'memory',run_id=old['run_id'],initial_skill=old['initial_skill'])
        head = load_memory(stage/'memory').head
        require(head['revision']==0, 'restart Memory must be empty')
        _durable_save(generation/'input.json', {'schema_version':'local_generation_v19.1','head':head,
            'round_id':'round-01','current_inputs':old_input['current_inputs'],
            'source_files':{p.name:_file_digest(p) for p in sorted(Path(__file__).parent.glob('*v19.py'))}})
        reused = {str(p.relative_to(stage)):_file_digest(p) for directory in
                  (root/'parent_evolution', root/'grouping', generation) for p in directory.rglob('*')
                  if p.is_file() and not (directory==generation and p.name=='input.json')}
        # Source copies and imported upstream must still match after offline checks.
        require(all(original_files[name]==sha for name,sha in reused.items()), 'offline validation altered upstream')
        receipt = {'schema_version':'memory_restart_v19.1', 'created_at':datetime.now(timezone.utc).isoformat(), 'source':str(source), 'archive':str(archive),
            'original_binding':old, 'replacement_sources':current_sources,'current_manifests':actual,
            'archive_files':original_files, 'reused_files':reused,
            'resume_stage':'round-01/MEMORY_REVIEW','memory_protocol':'issue_memory_v19.1',
            'identity_policy':'PRESERVE_SOURCE_RUN_ID_AND_EVIDENCE_IDS_IN_NEW_OUTPUT',
            'memory_policy':'EMPTY_REVISION_ZERO_NO_OLD_COMMITS'}
        _durable_save(stage/'migration.json', receipt)
        bound = _binding(old['config'],old['run_id'],old['initial_skill'],evo,mon)
        _durable_save(stage/'binding.json',{**bound,'entrypoint':ENTRYPOINT,
                                          'memory_restart_sha256':_file_digest(stage/'migration.json')})
        require(files(source)==original_files, 'source changed during migration')
        require(source_manifest()==current_sources, 'source code changed during migration')
        staging_archive.rename(archive)
        stage.rename(output)
        MemoryRestart(output/'migration.json').verify_reused_artifacts(output)
    return {'status':'READY','output':str(output),'archive':str(archive),
            'run_id':old['run_id'],'memory_revision':0,'resume_stage':'round-01/MEMORY_REVIEW'}
