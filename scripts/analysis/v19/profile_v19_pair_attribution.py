"""Profile an archived learner input without running models or modifying Replay."""
import argparse
from pathlib import Path
import statistics
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v19.attribution_pairs_v19 import profile, settings, token_count
from src.skill_evolution.v19.attribution_v19 import build_attribution_request
from src.skill_evolution.v19.evolution_replay_v19 import _load, _save, _file_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = _load(args.input)
    result = profile(data, settings())
    values = sorted(r['input_tokens_proxy'] for r in result['pairs'])
    result.update(source=str(args.input.resolve()), source_sha256=_file_digest(args.input),
                  legacy_single_call_tokens_proxy=token_count(build_attribution_request(data)),
                  min_input_tokens_proxy=min(values, default=0),
                  median_input_tokens_proxy=statistics.median(values) if values else 0)
    args.output.mkdir(parents=True, exist_ok=False)
    _save(args.output/'profile.json', result)
    (args.output/'report.md').write_text(
        '# Pair Attribution v19.2 输入审计\n\n'
        f"来源：`{args.input.resolve()}`；SHA256：`{result['source_sha256']}`。\n\n"
        f"完整 pair 数：{len(values)}；超预算：{result['over_budget_count']}。\n\n"
        '| 本地估算输入 token | 数量 |\n|---|---:|\n'
        f"| 旧版单次 | {result['legacy_single_call_tokens_proxy']:,} |\n"
        f"| 新版单次最小 | {result['min_input_tokens_proxy']:,} |\n"
        f"| 新版单次中位数 | {result['median_input_tokens_proxy']:,} |\n"
        f"| 新版单次最大 | {result['max_input_tokens_proxy']:,} |\n"
        f"| 新版整轮累计 | {result['total_input_tokens_proxy']:,} |\n\n"
        'cl100k_base 代理计数，不是网关实际用量。每个 packet 保留完整双侧事件、'
        '全部本轮 edit 的 before/after、Parent Skill 和本 pair 的完整领域 policy/tools。'
        '重复上下文会增加累计输入；目标是限制单次规模和失败重跑范围。'
        '此次仅统计旧输入，未发出模型请求；正式运行仍会重新校验账本和 Replay。\n', encoding='utf-8')
    print(args.output/'report.md')


if __name__ == '__main__':
    main()
