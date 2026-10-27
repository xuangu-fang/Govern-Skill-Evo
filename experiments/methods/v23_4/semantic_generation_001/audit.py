"""Revalidate study archives locally; never send a model request."""
import json

from . import run as study


def audit():
    _, config = study.verify()
    stages, totals = [], dict(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    for root in study.archive_glob(study.HERE / 'runs', '*'):
        label, stage = root.name.rsplit('_', 1)
        material, messages = study.inputs(label, stage)
        assert study.read(root / 'material.json') == material
        assert study.read(root / 'messages.json') == messages
        row = {'label': label, 'stage': stage, 'input_chars': len(json.dumps(messages, ensure_ascii=False)),
               'attempts': [], 'selected': None}
        attempts = list(study.archive_glob(root, 'attempt_*'))
        assert len(attempts) <= 4
        max_tokens = 32768
        for n, path in enumerate(attempts, 1):
            meta = study.read(path / 'attempt.json')
            request = study.read(path / 'http/request.json')
            expected = {k: v for k, v in config.items() if k not in ('endpoint', 'timeout_seconds')}
            expected.update(messages=messages, max_tokens=max_tokens)
            assert request['body'] == expected and request['endpoint'] == config['endpoint']
            assert request['transport_retries'] == 0 and request['allow_redirects'] is False
            assert meta['attempt'] == n and meta['max_tokens'] == max_tokens
            response = study.read(path / 'response.json') if study.resolve(path / 'response.json').exists() else {}
            usage = response.get('usage') or {}
            for key in totals:
                totals[key] += usage.get(key, 0)
            row['attempts'].append({**meta, 'usage': usage, 'usage_available': bool(usage),
                                    'archive': str(study.source_path(path).relative_to(study.HERE))})
            if response.get('finish_reason') == 'length':
                max_tokens = 65536
        if study.resolve(root / 'selected.json').exists():
            selected = study.read(root / 'selected.json')['attempt']
            assert selected == len(attempts)
            assert all(a['status'] != 'valid' for a in row['attempts'][:-1])
            result = study.load(label, stage)
            row['selected'] = selected
            if stage == 'editor':
                conditioned = study.load(label, 'pc')
                assert material['plan'] == conditioned['effective_plan']
                candidate = result['candidate_text']
                if candidate is not None:
                    dest = attempts[selected - 1]
                    assert study.resolve(dest / 'candidate.md').read_text() == candidate
                    assert study.resolve(dest / 'actual.diff').read_text() == result['actual_diff']
                    if result['actual_diff']:
                        assert study.old_editor.apply_patch(material['parent'], result['actual_diff']) == candidate
        stages.append(row)
    count = sum(len(s['attempts']) for s in stages)
    assert len(stages) <= 13 and count <= 52
    result = {'checked_at': study.now(), 'logical_stages': len(stages), 'http_attempts': count,
              'technical_restarts': count - len(stages),
              'structurally_valid_stages': sum(s['selected'] is not None for s in stages),
              'reported_usage_totals': totals, 'cost': None, 'stages': stages}
    (study.HERE / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return {k: v for k, v in result.items() if k != 'stages'}


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
