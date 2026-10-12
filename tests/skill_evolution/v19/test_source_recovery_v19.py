from pathlib import Path
from copy import deepcopy
import shutil

import pytest

import src.skill_evolution.v19.source_recovery_v19 as recovery
from src.skill_evolution.v19.evolution_replay_v19 import _save, _load
from src.skill_evolution.v19.memory_store_v19 import initialize_memory


@pytest.fixture
def source_case(tmp_path, monkeypatch):
    code = tmp_path/'code'
    old = tmp_path/'old'
    monkeypatch.setattr(recovery, 'ROOT', code)
    bodies = {
        'src/skill_evolution/v19/evolution_benchmark_v19.py':
            'class BenchmarkEvolutionV19:\n    def prepare(self): return 1\n    def evaluate(self): return 2\n',
        'src/skill_evolution/v19/memory_generation_prompt_v19.py': 'VERSION = 1\n',
        'scripts/runs/v19/run_v19_v4.py': '# runner\n',
    }
    for name, body in bodies.items():
        path = code/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body)
    shutil.copytree(code, old)
    original = recovery._sources()
    (code/'src/skill_evolution/v19/memory_generation_prompt_v19.py').write_text('VERSION = 2\n')
    output = tmp_path/'campaign'; output.mkdir()
    runtime = {'v19_source_files': {p: v for p,v in original.items() if p.startswith('src/')}, 'seed': 200}
    binding = {'source_files': original,
               'evolution_manifest': {'schema_version':'evolution_manifest_v19.1','runtime':runtime},
               'monitor_manifest': {'schema_version':'monitor_manifest_v19.1','runtime':runtime}}
    _save(output/'binding.json', binding)
    _save(output/'campaign.json', {'status':'INCOMPLETE','error_type':'BadRequestError',
                                  'failed_stage':'MEMORY_GENERATION','active_round':'round-02'})
    gen = output/'round-02/generation'
    _save(gen/'validation.json', {'status':'INCOMPLETE','error_type':'BadRequestError'})
    _save(gen/'input.json', {'original':'evidence'})
    _save(gen/'diagnosis-000/request.json', {'user_prompt':'original rejected request'})
    _save(output/'round-01/round_result.json', {'immutable':True})
    _save(output/'round-02/parent_evolution/validation.json', {'complete':True})
    _save(output/'round-02/grouping/validation.json', {'complete':True})
    initialize_memory(store_dir=output/'memory',run_id='test-run',initial_skill='Parent')
    return output, old, binding


def test_recovery_preserves_artifacts_and_binds_both_source_versions(source_case):
    output, old, binding = source_case
    receipt = recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    obj = recovery.DiagnosisSourceRecovery(receipt)
    obj.verify_reused_artifacts(output)
    assert _load(output/'binding.json') == binding
    assert not (output/'round-02/generation').exists()
    assert _load(receipt.parent/'failed_generation/diagnosis-000/request.json')['user_prompt'].startswith('original')
    current = {**binding, 'source_files':recovery._sources()}
    assert obj.campaign_binding(current) == binding
    manifest = deepcopy(binding['evolution_manifest'])
    manifest['runtime']['v19_source_files'] = {p:v for p,v in recovery._sources().items() if p.startswith('src/')}
    assert obj.execution_manifest(manifest) == binding['evolution_manifest']
    manifest['runtime']['seed'] = 42
    with pytest.raises(ValueError, match='execution config'): obj.execution_manifest(manifest)
    assert recovery.prepare_diagnosis_recovery(output=output, source_before=old) == receipt


@pytest.mark.parametrize('change', ['response','source','execution'])
def test_recovery_rejects_unsupported_changes_before_archiving(source_case, change):
    output, old, _ = source_case
    if change == 'response':
        _save(output/'round-02/generation/diagnosis-000/response.json', {'raw_response':'do not discard'})
    elif change == 'source':
        (recovery.ROOT/'src/skill_evolution/v19/monitor_campaign_v19.py').write_text('# changed gate')
    else:
        path = recovery.ROOT/'src/skill_evolution/v19/evolution_benchmark_v19.py'
        path.write_text(path.read_text().replace('return 1', 'return 3'))
    with pytest.raises(ValueError): recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    assert (output/'round-02/generation/diagnosis-000/request.json').exists()
    assert not (output/'diagnosis_recovery/failed_generation').exists()


def test_recovery_resumes_interruption_after_archive(source_case, monkeypatch):
    output, old, _ = source_case
    save = recovery._durable_save
    def stop(path, value):
        if path.name == 'receipt.json': raise RuntimeError('interrupted')
        save(path, value)
    monkeypatch.setattr(recovery, '_durable_save', stop)
    with pytest.raises(RuntimeError): recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    assert (output/'diagnosis_recovery/failed_generation').exists()
    monkeypatch.setattr(recovery, '_durable_save', save)
    receipt = recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    recovery.DiagnosisSourceRecovery(receipt).verify_reused_artifacts(output)


@pytest.mark.parametrize('target', ['artifact','source','archive','receipt','output'])
def test_recovery_detects_drift(source_case, tmp_path, target):
    output, old, _ = source_case
    receipt = recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    obj = recovery.DiagnosisSourceRecovery(receipt)
    if target == 'artifact':
        _save(output/'round-01/round_result.json', {'immutable':False})
    elif target == 'source':
        (recovery.ROOT/'src/skill_evolution/v19/memory_generation_prompt_v19.py').write_text('VERSION = 3\n')
    elif target == 'archive':
        _save(receipt.parent/'failed_generation/input.json', {'changed':True})
    elif target == 'receipt':
        _save(receipt, {**obj.receipt, 'reason':'changed'})
    if target in ('source','receipt'):
        with pytest.raises(ValueError): obj.validate_sources()
    else:
        with pytest.raises(ValueError): obj.verify_reused_artifacts(tmp_path/'elsewhere' if target=='output' else output)


@pytest.fixture
def contract_case(source_case, tmp_path):
    from src.skill_evolution.v19.memory_diagnosis_v19 import build_memory_diagnosis_inputs
    from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
    from src.skill_evolution.v19.evolution_replay_v19 import _file_digest
    from tests.skill_evolution.v19.test_memory_generation_v19 import current, raw_for
    output, old, _ = source_case
    first = recovery.prepare_diagnosis_recovery(output=output, source_before=old)
    original_receipt = first.read_bytes()
    # A real contract input and completed model response; only the model text is a fixture.
    kwargs = current(output, round_id='round-02')
    request = build_memory_diagnosis_inputs(**kwargs)[0]
    response = parse(raw_for(request.learner_payload, defer=True))
    response['diagnosis']['skill_addressability']['status'] = 'NO_ISSUE'
    gen = output/'round-02/generation'
    _save(gen/'input.json', {'requests':[{'payload':request.learner_payload,'provenance':request.provenance}]})
    _save(gen/'validation.json', {'status':'INCOMPLETE','error_type':'DiagnosisRejected'})
    call = gen/'diagnosis-000'
    _save(call/'request.json', {'prompt_version':'old','user_prompt':encode(request.learner_payload)})
    _save(call/'response.json', {'raw_response':encode(response),'finish_reason':'stop','refusal':None})
    _save(call/'response_complete.json', {'status':'COMPLETE','files':{
        name:_file_digest(call/name) for name in ('request.json','response.json')}})
    _save(output/'campaign.json', {'status':'INCOMPLETE','error_type':'DiagnosisRejected',
                                  'failed_stage':'MEMORY_GENERATION','active_round':'round-02'})
    sources = tmp_path/'contract-old'
    shutil.copytree(recovery.ROOT, sources)
    (recovery.ROOT/'src/skill_evolution/v19/memory_generation_prompt_v19.py').write_text('VERSION = 3\n')
    return output, sources, original_receipt


def test_contract_revision_keeps_prior_receipt_and_rejected_response(contract_case):
    output, sources, original = contract_case
    raw = (output/'round-02/generation/diagnosis-000/response.json').read_bytes()
    path = recovery.prepare_contract_recovery(output=output, source_before=sources)
    assert (path.parent/'receipt.json').read_bytes() == original
    assert (path.parent/'contract_rejected_generation/diagnosis-000/response.json').read_bytes() == raw
    obj = recovery.DiagnosisSourceRecovery(path)
    obj.verify_reused_artifacts(output)
    assert recovery.prepare_contract_recovery(output=output, source_before=sources) == path
    _save(path.parent/'contract_rejected_generation/diagnosis-000/response.json', {'changed':True})
    with pytest.raises(ValueError, match='archive changed'): obj.validate_sources()


def test_contract_revision_does_not_discard_later_responses(contract_case):
    output, sources, _ = contract_case
    _save(output/'round-02/generation/diagnosis-001/response.json', {'keep':True})
    with pytest.raises(ValueError, match='cannot discard'):
        recovery.prepare_contract_recovery(output=output, source_before=sources)
    assert (output/'round-02/generation/diagnosis-000/response.json').exists()


def test_contract_revision_interruption_reuses_original_attempt(contract_case, monkeypatch):
    output, sources, original = contract_case
    save = recovery._durable_save
    def stop(path, value):
        if path.name == 'receipt-contract.json': raise RuntimeError('interrupted')
        save(path, value)
    monkeypatch.setattr(recovery, '_durable_save', stop)
    with pytest.raises(RuntimeError): recovery.prepare_contract_recovery(output=output, source_before=sources)
    monkeypatch.setattr(recovery, '_durable_save', save)
    path = recovery.prepare_contract_recovery(output=output, source_before=sources)
    assert (path.parent/'receipt.json').read_bytes() == original
    recovery.DiagnosisSourceRecovery(path).verify_reused_artifacts(output)


def test_full_batch_archive_preserves_valid_prefix(contract_case):
    from src.skill_evolution.v19.edit_tracking_v19 import encode, parse
    from src.skill_evolution.v19.evolution_replay_v19 import _file_digest
    output, sources, _ = contract_case
    root = output/'diagnosis_recovery'
    gen = output/'round-02/generation'
    item = _load(gen/'input.json')['requests'][0]
    _save(gen/'input.json', {'requests':[item,item]})
    shutil.copytree(gen/'diagnosis-000',gen/'diagnosis-001')
    first = _load(gen/'diagnosis-000/response.json')
    obj = parse(first['raw_response'])
    obj['diagnosis']['skill_addressability']['status'] = 'NOT_ADDRESSABLE'
    first['raw_response'] = encode(obj)
    _save(gen/'diagnosis-000/response.json',first)
    for index in (0,1):
        call = gen/f'diagnosis-{index:03d}'
        req = _load(call/'request.json');req['prompt_sha256']='same-old-prompt'
        _save(call/'request.json',req)
        _save(call/'response_complete.json', {'status':'COMPLETE','files':{
            name:_file_digest(call/name) for name in ('request.json','response.json')}})
    _save(gen/'diagnosis-000.attempt-1/request.json', _load(gen/'diagnosis-000/request.json'))
    original = recovery._files(gen)
    path = recovery.prepare_diagnosis_batch(output=output,previous_receipt=root/'receipt.json',
        source_before=sources,batch_id='references-001',reason='Explicit prompt correction')
    record = _load(path)['batch_revision']
    assert [r['status'] for r in record['group_validation']] == ['VALID','REJECTED']
    assert recovery._files(root/record['generation_archive']) == original
    assert not gen.exists()
    recovery.DiagnosisSourceRecovery(path).verify_reused_artifacts(output)
    assert recovery.prepare_diagnosis_batch(output=output,previous_receipt=root/'receipt.json',
        source_before=sources,batch_id='references-001',reason='Explicit prompt correction') == path


def test_full_batch_refuses_editor_and_incomplete_transport(contract_case):
    output,sources,_ = contract_case
    gen=output/'round-02/generation'
    req=_load(gen/'diagnosis-000/request.json');req['prompt_sha256']='old'
    _save(gen/'diagnosis-000/request.json',req)
    # Changed request invalidates completion checksum; no artifact may be archived.
    with pytest.raises(ValueError):
        recovery.prepare_diagnosis_batch(output=output,previous_receipt=output/'diagnosis_recovery/receipt.json',
            source_before=sources,batch_id='invalid',reason='Prompt correction')
    assert gen.exists()
    (output/'round-02/candidate_evolution').mkdir()
    with pytest.raises(ValueError,match='downstream'):
        recovery.prepare_diagnosis_batch(output=output,previous_receipt=output/'diagnosis_recovery/receipt.json',
            source_before=sources,batch_id='invalid',reason='Prompt correction')


def test_full_batch_interrupted_archive_is_recoverable(contract_case, monkeypatch):
    from src.skill_evolution.v19.evolution_replay_v19 import _file_digest
    output,sources,_ = contract_case
    call=output/'round-02/generation/diagnosis-000'
    req=_load(call/'request.json');req['prompt_sha256']='old'
    _save(call/'request.json',req)
    _save(call/'response_complete.json',{'status':'COMPLETE','files':{
        name:_file_digest(call/name) for name in ('request.json','response.json')}})
    save=recovery._durable_save
    def stop(path,value):
        if path.name=='receipt-batch-interrupt.json':raise RuntimeError('interrupted after archive')
        save(path,value)
    monkeypatch.setattr(recovery,'_durable_save',stop)
    kwargs=dict(output=output,previous_receipt=output/'diagnosis_recovery/receipt.json',
                source_before=sources,batch_id='interrupt',reason='Correct references')
    with pytest.raises(RuntimeError):recovery.prepare_diagnosis_batch(**kwargs)
    assert not (output/'round-02/generation').exists()
    monkeypatch.setattr(recovery,'_durable_save',save)
    path=recovery.prepare_diagnosis_batch(**kwargs)
    recovery.DiagnosisSourceRecovery(path).verify_reused_artifacts(output)
