"""Offline Verifier prompt/message preparation and output validation. No transport."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_input_001 import prepare as inputs

PROMPT_PATH = Path(__file__).with_name('verifier_prompt.md')
PROMPT_VERSION = 'v23_5_statement_verifier_v1'
DEFAULT_OUTPUT = ROOT/'artifacts/methods/v23_5/verifier_contract_001'


class OutputValidationError(ValueError):
    """A complete response failed the deterministic Verifier output contract."""


def check(condition, location, message):
    if not condition:
        raise OutputValidationError(f'{location}: {message}')


def fields(value, expected, location):
    check(isinstance(value, dict), location, 'must be an object')
    check(set(value) == set(expected), location, f'must have exactly {", ".join(expected)}')


def position(value, location):
    fields(value, ('entry_index', 'knowledge_index'), location)
    for name in ('entry_index', 'knowledge_index'):
        check(type(value[name]) is int and value[name] >= 0, f'{location}.{name}', 'must be a nonnegative integer')
    return value['entry_index'], value['knowledge_index']


def nonempty(value, location):
    check(isinstance(value, str) and bool(value.strip()), location, 'must be a nonempty string')


def parse_output(content):
    """Parse the entire body, rejecting silent key overwrite and non-JSON values."""
    nonempty(content, 'response.content')

    def object_pairs(pairs):
        obj = {}
        for key, value in pairs:
            check(key not in obj, 'response.content', f'duplicate JSON key {key!r}')
            obj[key] = value
        return obj

    def invalid_constant(value):
        raise OutputValidationError(f'response.content: invalid JSON constant {value}')

    try:
        return json.loads(content, object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f'response.content: invalid JSON at line {exc.lineno}, column {exc.colno}') from exc


def validate_result(result, model_input):
    """Validate structure, exact coverage, source keys and verbatim issue locations.

    This does not establish the truth of a verdict or the adequacy of its reason.
    model_input must come from the checked frozen input package.
    """
    expected = {}
    for index, item in enumerate(model_input['targets']):
        key = position(item['target'], f'input.targets[{index}].target')
        check(key not in expected, 'input.targets', 'duplicate target')
        expected[key] = item['knowledge']['text']
    allowed = set(model_input['source_records'])
    fields(result, ('results',), 'output')
    check(isinstance(result['results'], list), 'output.results', 'must be an array')
    seen = set()
    for index, row in enumerate(result['results']):
        loc = f'results[{index}]'
        fields(row, ('target', 'verdict', 'issues'), loc)
        key = position(row['target'], f'{loc}.target')
        check(key in expected, f'{loc}.target', f'unknown target {key}')
        check(key not in seen, f'{loc}.target', f'duplicate target {key}')
        seen.add(key)
        check(row['verdict'] in ('SUPPORTED', 'CONFLICT'), f'{loc}.verdict', 'must be SUPPORTED or CONFLICT')
        check(isinstance(row['issues'], list), f'{loc}.issues', 'must be an array')
        check(bool(row['issues']) == (row['verdict'] == 'CONFLICT'), f'{loc}.issues',
              'must be empty for SUPPORTED and nonempty for CONFLICT')
        for issue_index, issue in enumerate(row['issues']):
            iloc = f'{loc}.issues[{issue_index}]'
            fields(issue, ('statement', 'reason', 'evidence'), iloc)
            nonempty(issue['statement'], f'{iloc}.statement')
            check(issue['statement'] in expected[key], f'{iloc}.statement',
                  'must be a verbatim contiguous excerpt from this target Knowledge')
            nonempty(issue['reason'], f'{iloc}.reason')
            check(isinstance(issue['evidence'], list), f'{iloc}.evidence', 'must be an array')
            refs = set()
            for ri, ref in enumerate(issue['evidence']):
                nonempty(ref, f'{iloc}.evidence[{ri}]')
                check(ref in allowed, f'{iloc}.evidence[{ri}]', f'unprovided source key {ref!r}')
                check(ref not in refs, f'{iloc}.evidence[{ri}]', f'duplicate source key {ref!r}')
                refs.add(ref)
    check(seen == set(expected), 'output.results', f'missing targets {sorted(set(expected) - seen)}')
    return result


def validate_response(response, model_input):
    """Reject truncation before parsing; never concatenate reasoning into content."""
    check(isinstance(response, dict), 'response', 'must be an object')
    check(response.get('finish_reason') == 'stop', 'response.finish_reason', 'must be stop')
    return validate_result(parse_output(response.get('content')), model_input)


def messages_for(model_input, prompt):
    return [{'role': 'system', 'content': prompt},
            {'role': 'user', 'content': json.dumps(model_input, ensure_ascii=False, separators=(',', ':'))}]


def prepare_messages(input_root, output):
    inputs.require(not output.exists(), 'Output exists; choose a fresh output directory')
    input_validation = inputs.verify(input_root)
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    output.mkdir(parents=True)
    (output/'prompt.md').write_bytes(PROMPT_PATH.read_bytes())
    (output/'verifier.py').write_bytes(Path(__file__).read_bytes())
    manifest = {'prompt_version': PROMPT_VERSION, 'input_root': str(input_root.resolve()),
                'input_manifest_sha256': inputs.digest(input_root/'manifest.json'),
                'prompt_sha256': inputs.digest(output/'prompt.md'),
                'validator_sha256': inputs.digest(output/'verifier.py'), 'cases': []}
    for name in inputs.ROUNDS:
        source = input_root/'cases'/name/'verifier_input.json'
        case = output/'cases'/name
        case.mkdir(parents=True)
        (case/'verifier_input.json').write_bytes(source.read_bytes())
        model_input = inputs.read(case/'verifier_input.json')
        messages = messages_for(model_input, prompt)
        inputs.save(case/'messages.json', messages)
        manifest['cases'].append({'round': name, 'targets': len(model_input['targets']),
                                  'input_sha256': inputs.digest(source),
                                  'messages_sha256': inputs.digest(case/'messages.json'),
                                  'messages_size': inputs.size(messages), 'api_prompt_tokens': None})
    inputs.save(output/'manifest.json', manifest)
    inputs.save(output/'input_validation.json', input_validation)
    report = verify_messages(output)
    inputs.save(output/'validation.json', report)
    return report


def verify_messages(output):
    manifest = inputs.read(output/'manifest.json')
    input_root = Path(manifest['input_root'])
    inputs.require(manifest['prompt_version'] == PROMPT_VERSION, 'Unsupported Verifier prompt version')
    inputs.verify(input_root)
    inputs.require(inputs.digest(input_root/'manifest.json') == manifest['input_manifest_sha256'], 'Input manifest changed')
    inputs.require(inputs.digest(output/'verifier.py') == manifest['validator_sha256'] == inputs.digest(__file__),
                   'Verifier implementation differs from frozen version')
    inputs.require(inputs.digest(output/'prompt.md') == manifest['prompt_sha256'] == inputs.digest(PROMPT_PATH),
                   'Verifier prompt differs from frozen version')
    inputs.require([row['round'] for row in manifest['cases']] == list(inputs.ROUNDS), 'Case list differs')
    prompt = (output/'prompt.md').read_text(encoding='utf-8')
    for row in manifest['cases']:
        case = output/'cases'/row['round']
        source = input_root/'cases'/row['round']/'verifier_input.json'
        inputs.require(inputs.digest(case/'verifier_input.json') == row['input_sha256'] == inputs.digest(source),
                       'Frozen Verifier input changed')
        model_input = inputs.read(case/'verifier_input.json')
        messages = messages_for(model_input, prompt)
        inputs.require(inputs.digest(case/'messages.json') == row['messages_sha256'], 'Message file changed')
        inputs.require(inputs.read(case/'messages.json') == messages, 'Messages differ from prompt/input')
        inputs.require(len(model_input['targets']) == row['targets'] and inputs.size(messages) == row['messages_size'],
                       'Message statistics differ')
    return {'valid': True, 'prompt_version': PROMPT_VERSION, 'rounds': list(inputs.ROUNDS),
            'targets': sum(row['targets'] for row in manifest['cases']),
            'input_package_unchanged': True, 'model_calls': 0, 'actor_calls': 0, 'memory_commits': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('prepare')
    build.add_argument('--inputs', type=Path, default=inputs.DEFAULT_OUTPUT)
    build.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    verify = sub.add_parser('verify')
    verify.add_argument('--root', type=Path, default=DEFAULT_OUTPUT)
    validate = sub.add_parser('validate')
    validate.add_argument('--root', type=Path, default=DEFAULT_OUTPUT)
    validate.add_argument('--round', choices=inputs.ROUNDS, required=True)
    validate.add_argument('--response', type=Path, required=True, help='JSON envelope with finish_reason and content')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            report = prepare_messages(args.inputs.resolve(), args.output.resolve())
        elif args.command == 'verify':
            report = verify_messages(args.root.resolve())
        else:
            verify_messages(args.root.resolve())
            # Parse envelopes strictly too; provider metadata is otherwise retained/ignored.
            response = parse_output(args.response.read_text(encoding='utf-8'))
            result = validate_response(response, inputs.read(args.root/'cases'/args.round/'verifier_input.json'))
            report = {'valid': True, 'result': result, 'semantic_truth_verified': False}
    except ValueError as exc:
        print(json.dumps({'valid': False, 'error_type': type(exc).__name__, 'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(report, ensure_ascii=False, indent=2))
