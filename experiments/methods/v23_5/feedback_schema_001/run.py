"""Historical schema continuation through the unchanged production retry scheduler."""
import argparse
import json
from pathlib import Path
import shutil

from src.skill_evolution.v23.editor import _read_text, _write_text
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_5 import comparison, evolution, feedback_retry, output_feedback as feedback
from src.skill_evolution.v23_5 import preconditioner as pc
from src.skill_evolution.v23_5.comparison_inputs import CONTRACT, read, save
from src.skill_evolution.v23_5.memory_view import KNOWLEDGE_ONLY

ROOT = Path('artifacts/methods/v23_5/feedback_schema_001').resolve()
CELL = {'round': 'R04', 'stage': 'preconditioner', 'arm': 'knowledge_only'}


def validate(content, *, output_boundary):
    def call(location, fn, *args):
        return feedback.output_call(location, fn, *args) if output_boundary else fn(*args)
    parsed = call('response', pc.parse_json_response, content)
    validated = call('Preconditioner output', comparison.validate_output, ROOT, CELL, parsed)
    return {'parsed': parsed, 'validated': validated}


def invoke(path, generate, cfg):
    """Evaluation adapter for frozen V23.4 material, not a fabricated V23.5 lineage."""
    context = feedback.saved_context(path) if path.exists() else feedback.generation_context(generate)
    messages = feedback.request_messages(read(ROOT/'base_messages.json'), context)
    if path.exists():
        require(read(path/'run.json')['status'] == 'valid', 'Evaluation result is incomplete')
        require(read(path/'run.json')['call_config'] == cfg, 'Evaluation configuration differs')
        require(read(path/'messages.json') == messages, 'Evaluation feedback messages differ')
        response = read(path/'response.json')
        require(response['finish_reason'] == 'stop', 'Evaluation response is incomplete')
        require(_read_text(path/'raw_output.txt') == response['content'], 'Evaluation raw output differs')
        value = validate(response['content'], output_boundary=False)
        require(value == read(path/'validated.json'), 'Evaluation result differs after reload')
        return value
    path.mkdir(parents=True)
    feedback.save_context(path, context)
    save(path/'messages.json', messages)
    meta = {'call_config': cfg, 'status': 'requesting', 'started_at': evolution.now()}
    save(path/'run.json', meta)
    print(json.dumps({'attempt': path.name, 'status': 'processing'}), flush=True)
    try:
        response = generate(messages, path)
        save(path/'response.json', response)
        _write_text(path/'raw_output.txt', response.get('content') or '')
        require(response.get('finish_reason') == 'stop', 'Model response did not finish normally')
        value = validate(response['content'], output_boundary=True)
        meta['output_validated'] = True
        save(path/'validated.json', value)
        save(path/'validation.json', {'valid': True})
        meta['status'] = 'valid'
    except (Exception, KeyboardInterrupt):
        meta['status'] = 'invalid'
        raise
    finally:
        meta['finished_at'] = evolution.now()
        save(path/'run.json', meta)
    return invoke(path, None, cfg)


def prepare():
    require(not ROOT.exists(), 'Experiment already exists')
    source = Path('artifacts/methods/v23_5/feedback_smoke_001').resolve()
    shutil.copytree(source/'cases/schema/cases', ROOT/'cases')
    cfg = read(source/'manifest.json')['spec']
    cfg['max_attempts'] = 3
    save(ROOT/'config.json', cfg)
    save(ROOT/'contract.json', evolution.frozen_contract())
    material = read(ROOT/'cases/R04/preconditioner/material.json')
    base = pc.messages_for(material, memory_view=KNOWLEDGE_ONLY,
                           memory_contract=CONTRACT, retry_policy=feedback.POLICY)
    require(base == read(source/'cases/schema/base_messages.json'), 'Initial Prompt/input changed')
    save(ROOT/'base_messages.json', base)
    seed = ROOT/'rounds/R04/preconditioner/attempts/001'
    response = read(source/'cases/schema/seed/response.json')
    save(seed/'response.json', response)
    save(seed/'messages.json', base)
    feedback.save_context(seed, {'policy': feedback.POLICY, 'feedback_from': None})
    save(seed/'run.json', {'call_config': cfg['call_config'], 'status': 'invalid', 'imported_seed': True})
    try:
        validate(response['content'], output_boundary=True)
    except feedback.OutputValidationError as exc:
        save(seed/'error.json', {'kind': 'output_validation', 'diagnostic': exc.diagnostic,
                                'error': str(exc), 'retryable': True, 'request_invoked': False})
    else:
        raise ValueError('Seed is no longer invalid')
    save(ROOT/'provenance.json', {'seed': str(source/'cases/schema/seed/response.json'),
         'seed_counts_as_attempt': 1, 'max_new_requests': 2,
         'scope': 'Frozen-material adapter using production scheduler and validators; no Actor/publication.'})
    print(json.dumps(read(seed/'error.json')['diagnostic']), flush=True)


def summarize():
    attempts = ROOT/'rounds/R04/preconditioner/attempts'
    rows = []
    for path in sorted(attempts.iterdir()):
        row = {'attempt': path.name, **read(path/'run.json')}
        if (path/'error.json').exists(): row['error'] = read(path/'error.json')
        if (path/'response.json').exists():
            response = read(path/'response.json')
            row.update(finish_reason=response.get('finish_reason'), usage=response.get('usage'))
            try:
                value = pc.parse_json_response(response['content'])
                row['missing_to'] = [a.get('target', i) for i, a in enumerate(value['adjustments']) if 'to' not in a]
            except (ValueError, KeyError, TypeError): pass
        rows.append(row)
    save(ROOT/'summary.json', {'attempts': rows,
         'new_requests': len(list(attempts.glob('*/request.json'))),
         'complete': (ROOT/'rounds/R04/preconditioner/result.json').exists()})
    return read(ROOT/'summary.json')


def run():
    cfg = read(ROOT/'config.json')
    gen = comparison.live_generator(cfg)
    try:
        feedback_retry.run_stage(ROOT, ROOT/'rounds/R04', 'preconditioner', invoke,
                                 cfg, gen, resume=True)
    except evolution.Stopped as exc:
        print(str(exc), flush=True)
    finally:
        print(json.dumps(summarize(), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'summarize'])
    args = parser.parse_args()
    {'prepare': prepare, 'run': run, 'summarize': summarize}[args.action]()
