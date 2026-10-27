"""Cost and structural statistics, with explicit unresolved semantic review material."""
from collections import Counter
import csv
import json
from pathlib import Path
import re

from .comparison_inputs import ARMS, ROUNDS, STAGES, case_path, read, save, verify


def usage_totals(attempts):
    """Unknown usage is null, never silently zero or estimated from characters."""
    result = {'requests': len(attempts), 'retry_requests': max(0, len(attempts)-1),
              'invalid_attempts': sum(a['status'] == 'invalid' for a in attempts)}
    for output, source in [('input_tokens', 'prompt_tokens'), ('output_tokens', 'completion_tokens'),
                           ('total_tokens', 'total_tokens')]:
        values = [a.get('usage', {}).get(source) for a in attempts]
        known = [v for v in values if type(v) is int and v >= 0]
        result[output] = sum(known) if len(known) == len(values) else None
        result['known_'+output] = sum(known)
        result['missing_'+output+'_requests'] = len(values)-len(known)
        failed = [a for a in attempts if a['status'] != 'valid']
        costs = [a.get('usage', {}).get(source) for a in failed]
        result['unsuccessful_'+output] = (sum(costs) if all(type(v) is int and v >= 0 for v in costs) else None)
    return result


def semantic_material(stage, material, parsed, validated):
    """Expose decisions and exact carryover signals without pretending to judge meaning."""
    if stage == 'preconditioner':
        updates = {u['id']: u for u in material['diagnosis']['plan']['updates']}
        decisions = []
        counts = Counter()
        effective = validated['effective_plan']
        after = {u['id']: u['text'] for u in effective['updates']} if effective else {}
        for a in parsed['adjustments']:
            mode = 'keep' if a['change'] == 'KEEP' else 'withdraw' if a['to'] == [] else 'modify'
            counts[mode] += 1
            for focus in a['focus']: counts[focus] += 1
            decisions.append({**a, 'mode': mode, 'original_text': updates[a['target']]['text'],
                              'effective_text': after.get(a['target']),
                              'actual_diff': validated['actual_diffs'].get(a['target'])})
        text = ' '.join(a['reason'] for a in parsed['adjustments'])
        metrics = {k: counts[k] for k in ('keep', 'modify', 'withdraw', 'D', 'S', 'C')}
        metrics['memory_ids_cited'] = sorted(set(re.findall(r'\bM[1-9]\d*\b', text)))
        metrics['historical_ids_cited'] = sorted(set(re.findall(r'[A-Za-z0-9_-]+/(?:diff|[PQ]\d+(?::\w+)?)', text)))
        metrics['checks'] = len(effective['checks']) if effective else 0
        detail = {'goal': material['diagnosis']['plan']['goal'], 'decisions': decisions,
                  'effective_plan': effective, 'history': material['memory']['entries']}
        questions = ['D/S/C 是否针对当前问题，且理由与修改一致？', '历史知识的条件、反例和不确定性是否保留？',
                     '是否把历史转述说成已重新核查，或增加无依据事实？', '是否出现不可执行条件、过宽恢复或跨阶段冲突？']
    else:
        old = material['payload']['memory']['entries']
        proposals = parsed['entries']
        replacement = {mid: proposal for proposal in proposals for mid in proposal['revises']}
        checks = []
        for entry in old:
            revised = entry['id'] in replacement
            for index, item in enumerate(entry['knowledge']):
                exact = revised and item in replacement[entry['id']]['knowledge']
                checks.append({'memory_id': entry['id'], 'old_item_index': index, 'old_knowledge': item,
                               'entry_revised': revised, 'exact_item_retained': exact,
                               'review_status': 'requires_semantic_review' if revised and not exact else
                                                'exact_copy' if revised else 'entry_untouched'})
        metrics = {'new_entries': sum(not e['revises'] for e in proposals),
                   'revised_entries': len(replacement), 'output_entries': len(proposals),
                   'output_knowledge': sum(len(e['knowledge']) for e in proposals),
                   'old_knowledge': len(checks),
                   'old_items_exact_carryover': sum(c['exact_item_retained'] for c in checks),
                   'old_items_in_untouched_entries': sum(not c['entry_revised'] for c in checks),
                   'old_items_requiring_review': sum(c['review_status'] == 'requires_semantic_review' for c in checks)}
        detail = {'old_item_review': checks, 'proposed_entries': proposals}
        questions = ['新断言是否由本轮实际 Diff 和行为支持？', '历史对照、条件、反例与不确定性是否忠实保留？',
                     '非逐字保留项是合理修订、合并，还是遗漏？', '是否过度泛化、虚构历史细节或改写旧实验事实？']
    return metrics, {'structural_validation_only': True, 'semantic_verdict': None,
                     'questions': questions, **detail}


def reduction(before, after):
    return 100*(before-after)/before if before is not None and after is not None and before > 0 else None


def summarize(root):
    from .comparison import load_attempt, check_attempt_inputs
    root = Path(root).resolve()
    manifest = verify(root)
    rows = []
    for cell in manifest['cells']:
        label, stage, arm = cell['round'], cell['stage'], cell['arm']
        frozen = case_path(root, label, stage, arm)
        messages = read(frozen/'messages.json')
        view = read(frozen/'model_input.json')
        material = read(frozen.parent/'material.json')
        folder = root/'runs'/label/stage/arm
        attempts = []
        for dest in sorted((folder/'attempts').glob('[0-9][0-9][0-9]')):
            meta = check_attempt_inputs(root, cell, dest, manifest['spec'])
            response = read(dest/'response.json') if (dest/'response.json').exists() else {}
            attempts.append({'attempt': dest.name, 'status': meta['status'], 'usage': response.get('usage') or {},
                             'finish_reason': response.get('finish_reason'), 'response_model': response.get('response_model'),
                             'elapsed_seconds': meta.get('elapsed_seconds'), 'error_type': meta.get('error_type')})
        result = folder/'result.json'
        row = {**cell, 'status': 'valid' if result.exists() else 'unresolved' if attempts else 'not_run',
               'system_chars': len(messages[0]['content']), 'user_chars': len(messages[1]['content']),
               'message_chars': len(json.dumps(messages, ensure_ascii=False)),
               'message_utf8_bytes': len(json.dumps(messages, ensure_ascii=False).encode()),
               'history_chars': len(json.dumps(view['memory'], ensure_ascii=False, separators=(',', ':'))),
               'active_entries': len(view['memory']['entries']),
               'input_knowledge': sum(len(e['knowledge']) for e in view['memory']['entries']),
               'attempts': attempts, **usage_totals(attempts)}
        row['first_input_tokens'] = attempts[0]['usage'].get('prompt_tokens') if attempts else None
        row['semantic_verdict'] = None
        if result.exists():
            dest = folder/'attempts'/read(result)['attempt']
            validated = load_attempt(root, cell, dest, manifest['spec'])
            metrics, review = semantic_material(stage, material, read(dest/'parsed.json'), validated)
            row['structural_metrics'] = metrics
            save(root/'reports/review_material'/label/stage/(arm+'.json'), review)
        rows.append(row)
    comparisons = []
    for label in ROUNDS:
        for stage in STAGES:
            arms = {r['arm']: r for r in rows if r['round'] == label and r['stage'] == stage}
            a, b = arms['memory_v3'], arms['knowledge_only']
            comparisons.append({'round': label, 'stage': stage,
                'both_valid': a['status'] == b['status'] == 'valid',
                'message_char_reduction_pct': reduction(a['message_chars'], b['message_chars']),
                'history_char_reduction_pct': reduction(a['history_chars'], b['history_chars']),
                'first_input_token_reduction_pct': reduction(a['first_input_tokens'], b['first_input_tokens']),
                'all_attempt_input_token_reduction_pct': (reduction(a['input_tokens'], b['input_tokens'])
                    if a['requests'] and b['requests'] else None),
                'semantic_comparison': 'not_assessed'})
    totals = {}
    for arm in ARMS:
        selected = [r for r in rows if r['arm'] == arm]
        total = usage_totals([a for r in selected for a in r['attempts']])
        # Retries restart per logical cell, not once for the entire experiment.
        total['retry_requests'] = sum(r['retry_requests'] for r in selected)
        total['valid_cells'] = sum(r['status'] == 'valid' for r in selected)
        totals[arm] = total
    summary = {'format': manifest['format'], 'status': 'complete' if all(r['status'] == 'valid' for r in rows)
               else 'prepared' if not any(r['requests'] for r in rows) else 'partial',
               'call_config': manifest['spec']['call_config'], 'cells': rows, 'comparisons': comparisons,
               'arm_totals': totals, 'semantic_quality': 'not_assessed',
               'limitations': ['Characters are not tokens; actual token usage comes only from API responses.',
                              'Exact carryover is not a semantic knowledge-retention score.',
                              'Fixed historical trajectories are not outcomes of new Preconditioner proposals.',
                              'No Actor success-rate or generalization claim; one sample per cell.']}
    save(root/'reports/summary.json', summary)
    fields = ['round', 'stage', 'arm', 'status', 'message_chars', 'message_utf8_bytes', 'history_chars',
              'requests', 'retry_requests', 'invalid_attempts', 'first_input_tokens', 'input_tokens',
              'output_tokens', 'total_tokens', 'missing_input_tokens_requests']
    with (root/'reports/cells.csv').open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    lines = ['# Knowledge Only 单轮冻结对照', '', f"状态：`{summary['status']}`。语义质量：尚未评审。",
             '', '两组使用相同当前事实、轮前 Knowledge、模型配置及三次总尝试预算；只切换历史视图和配套 Prompt。',
             'Preconditioner 与 Replay 独立运行；Replay 固定使用历史实际修改与轨迹，不使用新 Preconditioner 输出。',
             '', '| 轮次 | 模块 | v3 消息字符 | KO 消息字符 | 字符下降 | 首次输入 token 下降 |',
             '|---|---|---:|---:|---:|---:|']
    for c in comparisons:
        arms = {r['arm']: r for r in rows if r['round'] == c['round'] and r['stage'] == c['stage']}
        percent = c['first_input_token_reduction_pct']
        token = '待 API usage' if percent is None else f'{percent:.2f}%'
        lines.append(f"| {c['round']} | {c['stage']} | {arms['memory_v3']['message_chars']:,} | "
                     f"{arms['knowledge_only']['message_chars']:,} | {c['message_char_reduction_pct']:.2f}% | {token} |")
    lines += ['', '| 组 | 有效单元 | 请求 | 重试 | 输入 token（含失败） | 输出 token（含失败） |',
              '|---|---:|---:|---:|---:|---:|']
    for arm, total in totals.items():
        values = [str(total[k]) if total[k] is not None and total['requests'] else '未获得' for k in ('input_tokens', 'output_tokens')]
        lines.append(f"| {arm} | {total['valid_cells']}/8 | {total['requests']} | {total['retry_requests']} | {values[0]} | {values[1]} |")
    lines += ['', '实际 usage 缺失时记为 null；known_* 仅为已知部分，不能当作完整成本。未计算货币价格。',
              '失败尝试与重试均计入成本；另列首次请求输入 token，避免把视图缩减与重试差异混为一项。',
              '', '结构统计与逐项核查材料在 summary.json、cells.csv 和 review_material/。',
              'D/S/C 数量、引用数量、逐字保留率不等于判断质量。非逐字保留项需要核查，不能自动判为遗漏。',
              '固定轨迹不证明新策略成功率或泛化能力提高。本次每单元一份有效输出，不代表稳定统计结论。', '']
    (root/'reports/REPORT.md').write_text('\n'.join(lines))
    return summary
