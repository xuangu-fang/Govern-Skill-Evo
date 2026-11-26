#!/usr/bin/env python3
"""Audit saved real trajectories and request sizes offline; never call a model."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v25 import output_feedback as feedback
from src.skill_evolution.v25 import grouping, diagnosis, preconditioner
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmarks.spreadsheetbench import timeline


def size(messages):
    serialized = json.dumps(messages, ensure_ascii=False)
    return {'serialized_chars': len(serialized),
            'serialized_utf8_bytes': len(serialized.encode('utf-8')),
            'message_content_chars': sum(len(m['content']) for m in messages)}


def audit(round_directory, output):
    rd = Path(round_directory).resolve()
    output = Path(output).resolve()
    pilot = rd.parents[3]
    if output == pilot or pilot in output.parents:
        raise ValueError('Audit output must be outside the original pilot archive')
    # Refuse to overwrite any prior report or touch the experiment's files.
    output.mkdir(parents=True, exist_ok=False)
    sources = {}

    def read(path):
        path = Path(path)
        raw = path.read_bytes()
        sources[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def save(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    facts = read(rd / 'grouping/attempts/001/input.json')['facts']
    run_checks = []
    for run in facts['runs']:
        marker = rd / 'parent_runs' / run['task_id'].replace(':', '_') / 'result.json'
        record = read(Path(read(marker)['trajectory']))
        compact_run = timeline.project({'runs': [run]})['runs'][0]
        reconstructed = list(timeline.requests_for(compact_run))
        assert record['run_id'] == run['run_id']
        assert timeline.exact(run['initial']['messages']) == timeline.exact(record['initial_messages'])
        assert len(reconstructed) == len(record['attempts'])
        for actual, original in zip(reconstructed, record['attempts']):
            assert timeline.exact(actual) == timeline.exact(original['request_messages'])
        # Round-trip includes raw responses, actual code, execution, feedback,
        # post-execution scoring and every evidence ID, not only requests.
        assert timeline.exact(timeline.restore({'runs': [compact_run]})) == timeline.exact({'runs': [run]})
        run_checks.append({'ref': run['ref'], 'task_id': run['task_id'],
                           'attempts': len(reconstructed), 'all_requests_equal': True,
                           'entire_run_round_trip_equal': True})

    rows = []
    with using_benchmark(SpreadsheetBenchAdapter()):
        for stage, loader in [('grouping', grouping.load_grouping),
                              ('diagnosis', diagnosis.load_diagnosis),
                              ('preconditioner', preconditioner.load_preconditioner)]:
            selected = read(rd / stage / 'result.json')['path']
            loader(rd / stage / selected)  # Read-only legacy archive compatibility.
            for directory in sorted((rd / stage / 'attempts').iterdir()):
                if not (directory / 'messages.json').exists():
                    continue
                before = read(directory / 'messages.json')
                request = read(directory / 'request.json')
                assert before == request['body']['messages']
                context = read(directory / 'request_context.json')
                assert feedback.request_messages(before[:2], context) == before
                after = feedback.request_messages(before[:2],
                    {**context, 'execution_view': feedback.TIMELINE})
                before_payload, after_payload = (json.loads(m[1]['content']) for m in (before, after))
                assert timeline.exact(timeline.restore(after_payload)) == timeline.exact(before_payload)
                assert after[2:] == before[2:]  # Retry responses/diagnostics unchanged.
                response = read(directory / 'response.json')
                original_size, projected_size = size(before), size(after)
                label = f'{stage}_{directory.name}'
                save(output / f'{label}_timeline_messages.json', after)
                rows.append({'stage': stage, 'attempt': directory.name,
                    'selected': directory == rd / stage / selected,
                    'original_usage': response.get('usage'),
                    'original_finish_reason': response.get('finish_reason'),
                    'before': original_size, 'after': projected_size,
                    'serialized_char_reduction_percent': round(100 *
                        (1 - projected_size['serialized_chars'] / original_size['serialized_chars']), 2),
                    'after_prompt_tokens': None,
                    'entire_payload_round_trip_equal': True,
                    'retry_messages_unchanged': True})

    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest
               for p, digest in sources.items())
    report = {'round_directory': str(rd), 'execution_view': feedback.TIMELINE,
        'model_calls': 0, 'actor_executions': 0, 'source_files_unchanged': True,
        'source_sha256': sources, 'tasks': len(run_checks),
        'requests_reconstructed': sum(r['attempts'] for r in run_checks),
        'attempt_distribution': dict(Counter(r['attempts'] for r in run_checks)),
        'legacy_selected_stages_reload': True, 'run_checks': run_checks, 'requests': rows,
        'token_measurement_note': 'Before tokens are saved API usage. After tokens are unknown: no model call or matching model tokenizer was used. Character and UTF-8 byte sizes are exact and include the timeline instruction; no character-to-token conversion is reported.'}
    save(output / 'report.json', report)
    lines = ['# V25 连续时间线离线验证', '',
        f'- 来源：`{rd}`',
        f'- {len(run_checks)} 题、{report["requests_reconstructed"]} 次实际 Actor 请求逐轮还原一致。',
        '- 全部执行事实 round-trip 一致，证据 ID、反馈边界及重试消息不变。',
        '- 旧版三个模块的已选归档加载通过；读取的源文件 SHA-256 未变。',
        '- 模型调用 0，Actor 执行 0。', '',
        '| 模块／请求 | 原始 API 输入 Token | 原字符数 | 时间线字符数 | 减少 |',
        '|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["stage"]}/{r["attempt"]} | {r["original_usage"]["prompt_tokens"]:,} | '
                     f'{r["before"]["serialized_chars"]:,} | {r["after"]["serialized_chars"]:,} | '
                     f'{r["serialized_char_reduction_percent"]}% |')
    lines += ['', '字符数按完整 messages JSON 序列化计算，含新增时间线说明和已有重试反馈。',
        '修改后精确模型 Token 数未知；未使用字符换算冒充 Token 测量。',
        '本批尚无真实 Replay 请求，本报告不把构造配对视为真实 Replay 测量；Replay 接入由离线回归覆盖。',
        '本报告及派生 messages 位于独立目录，未修改原始归档、候选快照或冻结配置。', '']
    (output / 'REPORT.md').write_text('\n'.join(lines))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round', type=Path, required=True, dest='round_directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.round_directory, args.output)
    print(json.dumps({k: report[k] for k in ('tasks', 'requests_reconstructed', 'model_calls', 'source_files_unchanged')}))


if __name__ == '__main__':
    main()
