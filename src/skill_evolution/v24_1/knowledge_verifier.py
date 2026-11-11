"""Obvious-fact Verifier output contract; promoted without semantic changes."""
import json

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
