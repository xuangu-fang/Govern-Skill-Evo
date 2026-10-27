# Knowledge Only 单轮冻结对照 001：材料与归档

[实验协议](PROTOCOL.md) · [配置](config/protocol.json) · [历史准备记录](results/preparation.json) · [逐单元统计](reports/summary.json) · [统计表](reports/cells.csv)

## 批次关系与实际范围

原始固定预算组，max_tokens=32,768。运行在 R03 Preconditioner 阶段中止；没有有效输出。后续 [002](../knowledge_only_single_round_002/README.md) 是输出预算调整的新组，[003](../knowledge_only_single_round_003/README.md) 是完善输出协议后重新开始的新组，均不能当作 001 的普通 resume。

读取已有记录：本目录有 **5 次尝试、0 个选中有效输出、1 次未保存响应的尝试**，输出上限为 32,768。无响应的中断尝试仍占用原尝试编号，usage 未知，不能按零消耗或未调用处理。

配置和输入准备覆盖 R03–R06 的 16 个单元，不代表本组全部执行。下表只列实际创建尝试的单元，其余单元为未运行；没有 result.json 的单元不补造成功标记。

| 实际单元 | 本组尝试数 | 未保存响应 | 原选择记录与有效输出 |
|---|---:|---:|---|
| [R03/preconditioner/knowledge_only](evidence/runs/R03/preconditioner/knowledge_only/attempts/) | 2 | 1 | 无选择记录；失败／中断证据保留 |
| [R03/preconditioner/memory_v3](evidence/runs/R03/preconditioner/memory_v3/attempts/) | 3 | 0 | 无选择记录；失败／中断证据保留 |

## 保留材料与证据

- 配置、原协议、原有 results/ 研究结论和人工报告保持各自历史阶段含义。prepared_no_live_calls 描述准备阶段，不代表后来没有运行。
- [历史自动统计报告](reports/REPORT.md)、[summary.json](reports/summary.json) 与 [cells.csv](reports/cells.csv) 从归档原样复制，包含失败成本和未知 usage。自动报告中的 partial 按全部 16 个准备单元统计；semantic_quality 未评审是生成器字段，人工审阅另列，不替换历史记录。
- [逐次证据](evidence/runs/) 保留全部已有 attempt.json、validation.json 和 response.json。有效尝试另保留 parsed.json、validated.json 及原 result.json；失败正文不作为有效方案，三次以内的失败链完整保留供诊断与成本解释。

原有报告及人工审阅入口：

- [reports/PREPARATION.md](reports/PREPARATION.md)
- [reports/R03_STOPPED.md](reports/R03_STOPPED.md)
- [results/interrupted_run.json](results/interrupted_run.json)

## 十个批次导航

| 批次 | 关系 | 输出上限 | 实际边界 |
|---|---|---:|---|
| [001](README.md) | 原始组；中止 | 32,768 | R03 Preconditioner 已开始，未取得有效输出 |
| [002](../knowledge_only_single_round_002/README.md) | 001 后的预算调整新组；中止 | 65,536 | R03 Preconditioner 已开始，未取得有效输出 |
| [003](../knowledge_only_single_round_003/README.md) | 输出协议完善后的 R03 原始组 | 32,768 | 4 单元；原组 1 个有效 |
| [004](../knowledge_only_single_round_004/README.md) | 003 的 Preconditioner Knowledge Only 追加 | 32,768 | 原 3 次＋追加 2 次 |
| [005](../knowledge_only_single_round_005/README.md) | 003 的 Replay Memory v3 追加 | 32,768 | 原 3 次＋追加 1 次 |
| [006](../knowledge_only_single_round_006/README.md) | 003 的 Replay Knowledge Only 追加 | 32,768 | 原 3 次＋追加 2 次 |
| [007](../knowledge_only_single_round_007/README.md) | R04 独立历史输入对照 | 32,768 | 4 单元；3 个有效 |
| [008](../knowledge_only_single_round_008/README.md) | R05 独立历史输入对照 | 32,768 | 4 单元；本组 3 个有效 |
| [009](../knowledge_only_single_round_009/README.md) | R06 独立历史输入对照 | 32,768 | 4 单元；4 个有效 |
| [010](../knowledge_only_single_round_010/README.md) | 008 的 Preconditioner Memory v3 追加 | 32,768 | 原 3 次＋追加 1 次 |

## 原始归档、读取与写入

[原始归档](../../../../artifacts/methods/v23_5/knowledge_only_single_round_001/) 保留完整 cases/ 输入、各轮 Memory、model_input、messages、Prompt、request、HTTP 正文、raw_output 和运行锁。已经归档的原始数据不再搬动，历史来源路径保持原值。

[comparison 运行器](../../../../src/skill_evolution/v23_5/comparison.py)、[输入构造](../../../../src/skill_evolution/v23_5/comparison_inputs.py) 和 [统计生成器](../../../../src/skill_evolution/v23_5/comparison_stats.py) 继续使用协议中给定的 artifacts 根目录。evidence/ 与 reports/ 是静态研究副本，不作为运行、恢复或自动更新入口。JSON 内历史绝对路径指向原归档；README 的链接提供本地证据入口。

[局部忽略例外](.gitignore) 仅放行本批次已保存编号中的 JSON 证据，完整运行数据仍被 Git 忽略。仅克隆仓库可阅读研究材料，但不包含完整原始输入与运行环境。

2026-10-27 整理没有发请求、运行实验／测试／生产校验或计算哈希；只读取已有记录、复制研究证据并补充导航。历史测试数字不代表本次重新验证。Preconditioner 与 Replay 独立评估，Replay 始终使用历史实际 Diff 与配对执行；本次没有发布 Skill 或 Memory。
