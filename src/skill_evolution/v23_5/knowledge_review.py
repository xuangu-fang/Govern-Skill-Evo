"""Pre-publication Knowledge fact screen and one targeted Repair, with raw evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.memory import MULTI_KNOWLEDGE_CONTRACT, validate_entries
from src.adapters.alfworld.skill_runtime import write_record
from . import knowledge_evidence as evidence, knowledge_verifier as verifier, knowledge_repair as repair
from . import output_feedback as feedback

POLICY = 'obvious_fact_verifier_targeted_repair_v1'
HERE = Path(__file__).parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def freeze(path, value):
    path = Path(path)
    if path.exists():
        require(repair.exact(read(path)) == repair.exact(value), f'Frozen review value changed: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_record(path, value)


def prepare_input(bundle, candidate, memory_root):
    targets, _ = evidence.select_targets(candidate, bundle['payload']['memory'])
    # Historical context IDs come only from allowed target citations. No historical
    # trajectory catalog is loaded or sent to the model.
    repair.validate_candidate(candidate, bundle['payload'])
    contexts = {ref.rsplit('/', 1)[0] for t in targets for ref in t['knowledge']['evidence'] if '/' in ref}
    historical, provenance = {}, {}
    for cid in sorted(contexts):
        require(cid and '/' not in cid and '..' not in cid, 'Unsafe historical context')
        path = Path(memory_root)/'archive'/f'{cid}.json'
        raw = path.read_bytes()
        archive = json.loads(raw)
        require(archive['context_id'] == cid and archive.get('memory_contract') == MULTI_KNOWLEDGE_CONTRACT,
                'Historical archive identity/contract mismatch')
        saved = archive['context']
        validate_entries(archive['result'], saved['payload'], memory_contract=MULTI_KNOWLEDGE_CONTRACT)
        historical[cid] = saved
        provenance[cid] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest()}
    original, inventory = evidence.build_input(bundle, candidate, historical)
    return evidence.compact(original), inventory, provenance


def run_model(name, value, directory, *, generate, call_config, validate, max_input_chars):
    """Use the common technical/output-validation retry budget; reload never retries
    semantics or treats saved-file corruption as fresh model-output feedback.
    """
    require(name in ('verifier', 'repair'), 'Unknown Knowledge review stage')
    prompt = (HERE/f'knowledge_{name}_prompt.md').read_text(encoding='utf-8')
    context = (feedback.saved_context(directory) if Path(directory).exists()
               else feedback.generation_context(generate))
    messages = feedback.request_messages(verifier.messages_for(value, prompt), context)
    require(len(json.dumps(messages, ensure_ascii=False)) <= max_input_chars, 'Review input exceeds capacity')
    directory = Path(directory)

    def parse(response, *, fresh=False):
        require(response.get('finish_reason') == 'stop', 'Review response did not finish normally')
        if fresh:
            result = feedback.output_call(f'{name} response', verifier.parse_output, response.get('content'))
            feedback.output_call(f'{name} output', validate, result)
        else:
            result = verifier.parse_output(response.get('content'))
            validate(result)
        return result

    if directory.exists():
        require(read(directory/'input.json') == value and read(directory/'messages.json') == messages,
                'Saved review input/Prompt changed')
        meta = read(directory/'run.json')
        require(meta['status'] == 'valid' and meta['call_config'] == call_config, 'Review status/config differs')
        result = parse(read(directory/'response.json'))
        require(result == read(directory/f'{name}.json'), 'Saved review result changed')
        return result
    directory.mkdir(parents=True)
    feedback.save_context(directory, context)
    write_record(directory/'input.json', value)
    write_record(directory/'messages.json', messages)
    (directory/'prompt.md').write_text(prompt, encoding='utf-8')
    meta = {'stage': name, 'policy': POLICY, 'call_config': call_config, 'status': 'requesting'}
    write_record(directory/'run.json', meta)
    try:
        response = generate(messages, directory)
        write_record(directory/'response.json', response)
        (directory/'raw_output.txt').write_text(response.get('content') or '', encoding='utf-8')
        result = parse(response, fresh=True)
        meta['output_validated'] = True
        write_record(directory/f'{name}.json', result)
        write_record(directory/'validation.json', {'valid': True, 'semantic_truth_verified': False})
        meta['status'] = 'valid'
        return result
    except BaseException as exc:
        meta.update(status='invalid', error_type=type(exc).__name__)
        write_record(directory/'validation.json', {'valid': False, 'error_type': type(exc).__name__,
                                                  'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__})
        raise
    finally:
        write_record(directory/'run.json', meta)


def review(bundle, candidate, memory_root, directory, *, model, max_input_chars):
    """Return the only candidate eligible for Memory; never alter Replay output."""
    directory = Path(directory)
    value, inventory, provenance = prepare_input(bundle, candidate, memory_root)
    freeze(directory/'input.json', {'candidate': candidate, 'verifier_input': value,
                                   'inventory': inventory, 'historical_sources': provenance})
    result, verdicts, repaired = deepcopy(candidate), None, None
    if value['targets']:
        _, verdicts = model('verifier', lambda path, gen, cfg: run_model(
            'verifier', value, path, generate=gen, call_config=cfg,
            validate=lambda output: verifier.validate_result(output, value), max_input_chars=max_input_chars))
        repair_input = evidence.build_repair_input(value, verdicts, candidate)
        if repair_input['targets']:
            freeze(directory/'repair_input.json', repair_input)
            _, repaired = model('repair', lambda path, gen, cfg: run_model(
                'repair', repair_input, path, generate=gen, call_config=cfg,
                validate=lambda output: repair.merge(output, repair_input, candidate, bundle['payload']),
                max_input_chars=max_input_chars))
            result = repair.merge(repaired, repair_input, candidate, bundle['payload'])
    repair.validate_candidate(result, bundle['payload'])
    freeze(directory/'candidate.json', result)
    freeze(directory/'result.json', {'policy': POLICY, 'targets': len(value['targets']),
        'conflicts': sum(row['verdict'] == 'CONFLICT' for row in verdicts['results']) if verdicts else 0,
        'repair_applied': repaired is not None, 'second_semantic_verification': False,
        'candidate_sha256': hashlib.sha256(repair.exact(result).encode()).hexdigest()})
    return result
