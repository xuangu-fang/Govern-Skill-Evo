"""Edit-level association hypotheses over verified v19 Evolution evidence.

Structural validation is not semantic or causal verification. No Monitor input,
Skill mutation, memory commit, or automatic fallback to UNKNOWN.
"""
from dataclasses import dataclass
from pathlib import Path

from .edit_tracking_v19 import digest, encode, parse, validate_edit_ledger
from .evolution_replay_v19 import load_candidate_replay, _save, _load, _file_digest, _lock
from .attribution_prompt_v19 import SYSTEM_PROMPT


class AttributionRejected(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AttributionRejected(reason)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'unexpected or missing fields: ' + names)


def text(value):
    require(type(value) is str and bool(value.strip()), 'nonempty text required')


def refs(value, available, *, nonempty=False):
    require(type(value) is list and (bool(value) or not nonempty)
            and all(type(r) is str for r in value), 'reference list required')
    require(len(value) == len(set(value)) and set(value) <= set(available), 'duplicate or unresolved references')


@dataclass(frozen=True)
class AttributionBatch:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


def build_attribution_input(ledger, *, backend, parent_dir, replay_dir, history=()):
    """Revalidate private checkpoints; expose only explicit learner fields.

    History is used only to validate the ledger. Gate decisions and the ledger's
    private compiler/diagnosis source are never serialized into this input.
    """
    edits = validate_edit_ledger(ledger, history=history)
    replay = load_candidate_replay(ledger, backend=backend, parent_dir=parent_dir,
                                   artifact_dir=replay_dir, history=history)
    data = replay.payload
    return {'schema_version': 'attribution_input_v19.1', 'run_id': edits['run_id'],
            'round_id': edits['round_id'], 'ledger_sha256': digest(ledger.output_json),
            'replay_sha256': digest(replay.payload_json),
            'parent_skill': ledger.source['editor']['parent_skill'],
            'candidate_skill': ledger.source['candidate_skill'],
            'edits': edits['edits'], 'contexts': data['contexts'], 'pairs': data['pairs'],
            **({'candidate_layout': edits['candidate_layout'],
                'comparison_scope': 'Candidate includes a user-authorized layout change as well as the learned edits. Outcome changes alone do not isolate edit effects; consider layout as an alternative explanation.'}
               if 'candidate_layout' in edits else {})}


EFFECTS = ('BENEFICIAL', 'HARMFUL', 'MIXED', 'NO_OBSERVED_EFFECT', 'NOT_EXERCISED', 'UNKNOWN')
LEVELS = ('UNRESOLVED', 'OUTCOME_ASSOCIATION', 'BEHAVIOR_SUPPORTED')
FOLLOWUPS = ('PRESERVE', 'REVISE', 'CONSIDER_REMOVE', 'RETRY', 'DEFER')
RECORD_FIELDS = ('edit_ids effect evidence_level observations interpretation applicability '
                 'alternative_explanations uncertainty suggested_followup')
OBS_FIELDS = ('pair_id relation parent_evidence_refs candidate_evidence_refs supervision_refs behavior_comparison')


def validate_attribution_response(raw_response, *, learner_input):
    """Use with freshly built input; never accepts private evaluator evidence.

    IDs, role-bound refs and result-direction constraints are deterministic.
    Textual relevance, causal explanations and claimed non-exercise still need
    scientific scrutiny; VALID is explicitly only structural/reference validity.
    """
    try:
        output = parse(raw_response)
        fields(output, 'schema_version records')
        require(output['schema_version'] == 'attribution_response_v19.1', 'wrong response schema')
        records = output['records']
        require(type(records) is list and bool(records), 'nonempty records required')
        edit_ids = {e['edit_id'] for e in learner_input['edits']}
        pairs = {p['pair_id']: p for p in learner_input['pairs']}
        covered, identities, result = set(), set(), []
        for record in records:
            fields(record, RECORD_FIELDS)
            refs(record['edit_ids'], edit_ids, nonempty=True)
            covered.update(record['edit_ids'])
            require(record['effect'] in EFFECTS and record['evidence_level'] in LEVELS
                    and record['suggested_followup'] in FOLLOWUPS, 'invalid attribution enum')
            for key in ('interpretation', 'applicability', 'uncertainty'):
                text(record[key])
            alternatives = record['alternative_explanations']
            require(type(alternatives) is list and bool(alternatives), 'alternative explanations required')
            for alternative in alternatives:
                text(alternative)
            observations = record['observations']
            require(type(observations) is list, 'observations list required')
            require(bool(observations) or record['effect'] == 'UNKNOWN', 'only UNKNOWN may lack observations')
            seen, directions, supports = set(), set(), 0
            for observation in observations:
                fields(observation, OBS_FIELDS)
                pair_id = observation['pair_id']
                require(type(pair_id) is str and pair_id in pairs and pair_id not in seen,
                        'unknown or duplicate pair in record')
                seen.add(pair_id)
                pair = pairs[pair_id]
                require(observation['relation'] in ('SUPPORT', 'COUNTEREVIDENCE', 'CONTEXT'), 'invalid relation')
                text(observation['behavior_comparison'])
                supervision = [pair[r]['supervision']['supervision_ref'] for r in ('parent', 'candidate')]
                refs(observation['supervision_refs'], supervision, nonempty=True)
                require(set(observation['supervision_refs']) == set(supervision), 'both supervision refs required')
                for role in ('parent', 'candidate'):
                    events = {e['evidence_ref']: e for e in pair[role]['events']}
                    selected = observation[role + '_evidence_refs']
                    refs(selected, events)
                    if record['evidence_level'] == 'BEHAVIOR_SUPPORTED' and observation['relation'] == 'SUPPORT':
                        require(any(events[r]['actor'] in ('assistant', 'tool') for r in selected),
                                'behavior support requires agent behavior on both sides')
                if observation['relation'] == 'SUPPORT':
                    supports += 1
                if observation['relation'] != 'CONTEXT':
                    for key in ('success_delta', 'compliant_delta'):
                        delta = pair['outcome_transition'][key]
                        if delta:
                            directions.add(1 if delta > 0 else -1)
            effect, level = record['effect'], record['evidence_level']
            if effect == 'UNKNOWN':
                require(level == 'UNRESOLVED' and record['suggested_followup'] == 'DEFER',
                        'UNKNOWN must remain unresolved/deferred')
            elif effect == 'NOT_EXERCISED':
                require(level == 'UNRESOLVED' and record['suggested_followup'] == 'DEFER',
                        'non-exercise does not authorize an effect conclusion')
                require(all(o['parent_evidence_refs'] and o['candidate_evidence_refs'] for o in observations),
                        'non-exercise needs observed scope evidence on both sides')
            else:
                require(level != 'UNRESOLVED' and supports > 0, 'effect needs a supporting observation')
                if effect == 'BENEFICIAL':
                    require(directions == {1}, 'benefit requires positive outcomes without hidden opposite direction')
                elif effect == 'HARMFUL':
                    require(directions == {-1}, 'harm requires negative outcomes without hidden opposite direction')
                elif effect == 'MIXED':
                    require(directions == {-1, 1}, 'mixed requires opposing observed outcome directions')
                else:
                    require(not directions, 'no observed effect requires unchanged associated outcome labels')
            identity = digest(encode(record))
            require(identity not in identities, 'duplicate attribution record')
            identities.add(identity)
            result.append({'schema_version': 'attribution_record_v19.1',
                           'attribution_id': 'ATTRIBUTION/' + digest(encode({
                               'input_sha256': digest(encode(learner_input)), 'record': record})),
                           'run_id': learner_input['run_id'], 'round_id': learner_input['round_id'], **record})
        require(covered == edit_ids, 'attribution must cover every edit')
        return AttributionBatch(encode({'schema_version': 'attribution_batch_v19.1',
            'run_id': learner_input['run_id'], 'round_id': learner_input['round_id'],
            'input_sha256': digest(encode(learner_input)), 'records': result,
            'validation_scope': 'STRUCTURE_AND_REFERENCES_ONLY'}))
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, AttributionRejected):
            raise
        raise AttributionRejected('invalid attribution response: ' + type(exc).__name__) from exc


def build_attribution_request(learner_input):
    return {'system_prompt': SYSTEM_PROMPT, 'user_prompt': encode(learner_input),
            'model': 'deepseek-v4-pro', 'temperature': 0.0, 'reasoning_effort': 'high',
            'max_completion_tokens': 24000, 'timeout_seconds': 300, 'max_retries': 0,
            'response_format': {'type': 'json_object'}}


def _transport(request):
    import os
    from openai import OpenAI
    require(bool(os.environ.get('OPENAI_API_KEY')) and bool(os.environ.get('OPENAI_BASE_URL')),
            'missing configured model connection')
    with OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'],
                timeout=request['timeout_seconds'], max_retries=0) as client:
        response = client.chat.completions.create(
            model=request['model'], temperature=request['temperature'],
            reasoning_effort=request['reasoning_effort'], max_completion_tokens=request['max_completion_tokens'],
            response_format=request['response_format'], messages=[
                {'role': 'system', 'content': request['system_prompt']},
                {'role': 'user', 'content': request['user_prompt']}])
    choice = response.choices[0]
    return {'raw_response': choice.message.content, 'finish_reason': choice.finish_reason,
            'refusal': getattr(choice.message, 'refusal', None), 'response_model': response.model,
            'response_id': response.id, 'usage': response.usage.model_dump() if response.usage else None}


def _validate_completion(response, learner_input):
    require(type(response) is dict and response.get('finish_reason') == 'stop'
            and not response.get('refusal'), 'refused or incomplete completion')
    return validate_attribution_response(response.get('raw_response'), learner_input=learner_input)


RESPONSE_FILES = ('input.json', 'request.json', 'response.json')
FILES = (*RESPONSE_FILES, 'response_complete.json', 'attributions.json')


def _check_response(directory):
    marker = _load(directory / 'response_complete.json')
    require(marker == {'status': 'COMPLETE', 'files': {
        name: _file_digest(directory / name) for name in RESPONSE_FILES}},
        'saved response checkpoint mismatch')


def _load_complete(directory, learner_input, request):
    marker = _load(directory / 'validation.json')
    fields(marker, 'status validation_scope files')
    require(marker['status'] == 'VALID' and marker['validation_scope'] == 'STRUCTURE_AND_REFERENCES_ONLY',
            'attribution not complete')
    require(type(marker['files']) is dict and set(marker['files']) == set(FILES), 'incomplete artifact manifest')
    require(all(_file_digest(directory / name) == sha for name, sha in marker['files'].items()),
            'attribution artifact digest mismatch')
    _check_response(directory)
    require(_load(directory / 'input.json') == learner_input and _load(directory / 'request.json') == request,
            'attribution input or prompt version changed')
    batch = _validate_completion(_load(directory / 'response.json'), learner_input)
    require(encode(_load(directory / 'attributions.json')) == batch.payload_json,
            'attributions differ from revalidated response')
    return batch


def load_attribution(ledger, *, backend, parent_dir, replay_dir, artifact_dir, history=()):
    learner_input = build_attribution_input(ledger, backend=backend, parent_dir=parent_dir,
                                           replay_dir=replay_dir, history=history)
    return _load_complete(Path(artifact_dir), learner_input, build_attribution_request(learner_input))


def run_attribution(ledger, *, backend, parent_dir, replay_dir, artifact_dir, history=(),
                    transport=None, resume=False):
    """One model call; explicit resume may finish validating a saved response.

    A failed/uncertain call without a saved response cannot be silently retried.
    Use a new audit directory for an explicitly requested new attempt.
    """
    require(type(resume) is bool, 'resume must be boolean')
    learner_input = build_attribution_input(ledger, backend=backend, parent_dir=parent_dir,
                                           replay_dir=replay_dir, history=history)
    request = build_attribution_request(learner_input)
    directory = Path(artifact_dir)
    with _lock(directory):
        if directory.exists():
            require(resume, 'existing attribution requires explicit resume')
            if (directory / 'validation.json').exists() and _load(directory / 'validation.json').get('status') == 'VALID':
                return _load_complete(directory, learner_input, request)
            require(_load(directory / 'input.json') == learner_input and _load(directory / 'request.json') == request,
                    'resume input or prompt mismatch')
            require((directory / 'response.json').exists(), 'no saved response; explicit new attempt required')
            require((directory / 'response_complete.json').exists(),
                    'response was not checkpointed; explicit new attempt required')
            _check_response(directory)
        else:
            require(not resume, 'resume requires existing output')
            directory.mkdir(parents=True)
            _save(directory / 'input.json', learner_input)
            _save(directory / 'request.json', request)
            _save(directory / 'validation.json', {'status': 'RUNNING'})
            try:
                response = (transport or _transport)(parse(encode(request)))
                _save(directory / 'response.json', response)
                _save(directory / 'response_complete.json', {'status': 'COMPLETE', 'files': {
                    name: _file_digest(directory / name) for name in RESPONSE_FILES}})
            except BaseException as exc:
                _save(directory / 'validation.json', {'status': 'INCOMPLETE', 'stage': 'TRANSPORT',
                                                     'error_type': type(exc).__name__})
                raise
        try:
            batch = _validate_completion(_load(directory / 'response.json'), learner_input)
            if (directory / 'attributions.json').exists():
                require(encode(_load(directory / 'attributions.json')) == batch.payload_json,
                        'existing attribution output mismatch')
            else:
                _save(directory / 'attributions.json', batch.payload)
            _save(directory / 'validation.json', {'status': 'VALID',
                'validation_scope': 'STRUCTURE_AND_REFERENCES_ONLY',
                'files': {name: _file_digest(directory / name) for name in FILES}})
            return batch
        except BaseException as exc:
            _save(directory / 'validation.json', {'status': 'INCOMPLETE', 'stage': 'VALIDATION',
                                                 'error_type': type(exc).__name__})
            raise
