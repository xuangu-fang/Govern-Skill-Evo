"""Reviewed SearchQA runtime: exact recovery order, raw responses and stage budgets.

The order and HTTP recorder implementations were verified in the batch-15
recoveries. No provider calls happen on import and no authentication headers
are written to the archive.
"""
from datetime import datetime, timezone
from dataclasses import replace
import json
from pathlib import Path
from skilladam.core.momentum import MomentumTracker


def restore_problem_order(tracker, archived_user):
    start = '# Current Problem Tracker\n\n'
    end = '\n\n# Ordered Condensed Training Trajectories'
    if archived_user.count(start) != 1 or archived_user.count(end) != 1:
        raise ValueError('Ambiguous archived Momentum tracker boundaries')
    expected = archived_user.split(start, 1)[1].split(end, 1)[0]
    if tracker.render_for_agent_input() == expected:
        return
    positions = []
    for key, entry in tracker.problems.items():
        single = MomentumTracker()
        single.problems = {key: entry}
        block = single.render_for_agent_input()
        if expected.count(block) != 1:
            raise ValueError('Momentum tracker content differs, not just order')
        positions.append((expected.index(block), key, entry))
    reordered = {key: entry for _, key, entry in sorted(positions)}
    probe = MomentumTracker()
    probe.problems = reordered
    if probe.render_for_agent_input() != expected:
        raise ValueError('Momentum tracker cannot reproduce archived text exactly')
    tracker.problems = reordered


def attach_recorder(client, directory):
    root = Path(directory)

    def record(response):
        response.read()
        root.mkdir(parents=True, exist_ok=True)
        index = len(list(root.glob('response_*'))) + 1
        folder = root / f'response_{index:04d}'
        folder.mkdir(exist_ok=False)
        (folder / 'request_body.json').write_bytes(response.request.content)
        (folder / 'response_body.json').write_bytes(response.content)
        summary = {'at': datetime.now(timezone.utc).isoformat(),
                   'status_code': response.status_code,
                   'request_id': response.headers.get('x-request-id')}
        try:
            payload = response.json()
            summary['usage'] = payload.get('usage')
            summary['choices'] = [
                {'finish_reason': c.get('finish_reason'),
                 'content_chars': len(c.get('message', {}).get('content') or ''),
                 'reasoning_chars': len(c.get('message', {}).get('reasoning_content') or ''),
                 'tool_calls': len(c.get('message', {}).get('tool_calls') or [])}
                for c in payload.get('choices', [])]
        except (ValueError, TypeError, AttributeError):
            summary['json_summary_unavailable'] = True
        (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    client._client.event_hooks.setdefault('response', []).append(record)
    return client


class StageBudgets:
    """Apply the frozen per-stage budget, restoring the backend even on errors."""
    def __init__(self, backend, budgets):
        self.backend, self.budgets = backend, dict(budgets)

    def generate(self, request):
        if request.stage not in self.budgets:
            raise ValueError('Unsupported SearchQA optimizer stage')
        original = self.backend._config
        self.backend._config = replace(original, max_completion_tokens=self.budgets[request.stage])
        try:
            return self.backend.generate(request)
        finally:
            self.backend._config = original
