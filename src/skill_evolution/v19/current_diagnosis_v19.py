"""Current-round discovery, deliberately independent of historical Memory."""
from .edit_tracking_v19 import encode, digest, skill_ref
from .memory_store_v19 import require
from .evolution_replay_v19 import load_parent_experiences
from ..v17.group_diagnosis_input_v17 import build_group_diagnosis_inputs
from ..v18.diagnosis_references_v18 import build_reference_catalogs
from .review_contract_v19 import CurrentDiagnosisInput, CurrentFindings, CURRENT_SCHEMA, checked_response


def build_current_diagnosis_inputs(*, run_id, round_id, parent_skill, backend,
                                   parent_dir, grouping_result):
    sources, scope, executions = load_parent_experiences(run_id=run_id, round_id=round_id,
        parent_skill=parent_skill, backend=backend, artifact_dir=parent_dir, include_execution_refs=True)
    grouped = build_group_diagnosis_inputs(sources, scope=scope, grouping_result=grouping_result,
                                          parent_skill=parent_skill)
    group_ids = sorted(r.provenance['group_id'] for r in grouped)
    batch = {'run_id': run_id, 'round_id': round_id, 'parent_skill_ref': skill_ref(parent_skill),
             'grouping_sha256': digest(encode(grouping_result)), 'group_ids': group_ids,
             'evolution_manifest_sha256': digest(encode(backend.manifest()))}
    result = []
    namespace = 'CURRENT/' + digest(encode({'run_id': run_id, 'round_id': round_id})) + '/'
    for request in grouped:
        payload = request.learner_payload
        source_tasks = {b['presented']['task_ref']: b['source']['task_ref']
                        for b in request.provenance['experience_bindings']}
        refs = {}
        for exp in payload['experiences']:
            exp.update(origin='CURRENT_PARENT', source_round_id=round_id,
                       skill_ref=skill_ref(parent_skill), role='PARENT')
            execution = executions[source_tasks[exp['task_ref']]]
            if execution is not None:
                exp['execution_ref'] = execution
            for event in exp['events']:
                old = event['evidence_ref']; refs[old] = namespace + old
                event['evidence_ref'] = refs[old]
            old = exp['supervision']['supervision_ref']; refs[old] = namespace + old
            exp['supervision']['supervision_ref'] = refs[old]
        for field in ('available_evidence_refs', 'available_supervision_refs'):
            payload[field] = {refs[key]: value for key, value in payload[field].items()}
        payload.update(build_reference_catalogs(payload))
        payload['schema_version'] = 'current_diagnosis_input_v19.1'
        result.append(CurrentDiagnosisInput(encode(payload), encode({**request.provenance, 'batch': batch})))
    return tuple(result)


def validate_current_findings(raw, *, request):
    require(isinstance(request, CurrentDiagnosisInput), 'CurrentDiagnosisInput required')
    output = checked_response(raw, CURRENT_SCHEMA)
    payload = request.payload
    fields = {'evidence_refs': 'available_evidence_refs', 'supervision_refs': 'available_supervision_refs',
              'policy_refs': 'available_policy_refs', 'related_rule_refs': 'available_rule_refs'}
    findings, seen = [], set()
    for index, finding in enumerate(output['findings']):
        require(bool(finding['evidence_refs']) and bool(finding['dimensions']),
                f'finding {index}: current event evidence and dimensions required')
        for field, catalog in fields.items():
            missing = sorted(set(finding[field]) - set(payload[catalog]))
            require(not missing, f'finding {index}: invalid {field}: {encode(missing)}')
        # A policy or outcome reference must concern a cited trajectory/context.
        experiences = [e for e in payload['experiences'] if set(finding['evidence_refs']) &
                       {ev['evidence_ref'] for ev in e['events']}]
        require(set(finding['supervision_refs']) <= {e['supervision']['supervision_ref'] for e in experiences},
                f'finding {index}: supervision not linked to cited trajectories')
        require(all(payload['available_policy_refs'][ref]['context_ref'] in
                    {e['context_ref'] for e in experiences} for ref in finding['policy_refs']),
                f'finding {index}: policy outside cited contexts')
        fid = 'CF/' + digest(encode({'input_ref': request.input_ref, 'finding': finding}))
        require(fid not in seen, f'finding {index}: duplicate finding')
        seen.add(fid)
        findings.append({'finding_id': fid, **finding})
    return CurrentFindings(encode({'schema_version': 'current_findings_v19.1',
        'input_ref': request.input_ref, 'batch': request.provenance['batch'],
        'group_id': request.provenance['group_id'], 'raw_response': raw,
        'summary': output['summary'], 'findings': findings,
        'validation_scope': 'STRUCTURE_REFERENCES_AND_BINDINGS_NOT_SEMANTIC_TRUTH'}))


def validate_current_batch(requests, findings):
    require(bool(requests) and len(requests) == len(findings), 'complete Current Findings batch required')
    batch = requests[0].provenance['batch']
    require(sorted(r.provenance['group_id'] for r in requests) == batch['group_ids'],
            'missing or duplicate current group')
    by_ref = {f.payload['input_ref']: f for f in findings}
    require(len(by_ref) == len(findings), 'duplicate Current Findings input')
    for request in requests:
        require(request.provenance['batch'] == batch, 'mixed current batches')
        require(request.input_ref in by_ref, 'missing or stale Current Findings')
        saved = by_ref[request.input_ref]
        require(validate_current_findings(saved.payload['raw_response'], request=request) == saved,
                'Current Findings changed after validation')
    return batch
