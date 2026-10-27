# 用户提供的 Replay 主 Prompt：正式候选验证 001

日期：2026-10-22。**R05/R06 均首次结构通过，2 次 HTTP、0 次技术重试；重要比较有所改善，但原样 Knowledge 仍有事实/范围/比较完整性问题，五条提案均暂不发布。**

## 候选与不变量

用户附件 `/Users/didi/Downloads/replay_prompt_v23_4.md` 已按字节原样冻结为 [candidate_prompt.md](candidate_prompt.md)，作为本轮正式候选。主文件没有复制 Actor 背景和两份视图说明，也没有为个别案例补句子。

实验程序按顺序拼接：候选主 Prompt → 原 Actor execution context → 原 Memory v3 说明 → 原 Replay paired-view 说明，每份恰好一次。原基础模板将 execution context 放在开头介绍之后；本候选依附件表述将它追加。因此本次比较包含主文改写及背景位置变化，不单独归因于某一句指令。

R05/R06 User 消息与 `replay_input_view_live_001` **逐字一致**；完整事实 bundle、Actual Diff、Effective Plan、历史 Memory 快照、历史 Pair 来源和模型参数均相同。没有输入上一轮提案、人工审查结论或新的 Actor 结果。[不变量检查](config/comparison.json)和[冻结清单](config/freeze.json)已通过。

采用独立实验目录和候选加载器，没有覆盖生产默认 Prompt、Replay 模块或旧实验文件。保留原独立评估事实链限制：本轮新 Parent 执行没有产生原 Diagnosis Plan，不宣称生产原始谱系加载通过。

## 真实调用

沿用 deepseek-v4.1-flash、temperature=1、thinking enabled/medium、max_tokens=32768，以及相同 transport、超时、结构验证和技术重试策略。顺序运行 R05/R06；每轮首次加最多三次技术重试，首次合法即停止。本次均 stop，无重试、无语义重采样。请求上限仍为 1,200,000 字符，无输入截断。

| 指标 | R05 | R06 |
|---|---:|---:|
| HTTP / 技术重试 | 1 / 0 | 1 / 0 |
| 请求耗时（秒） | 137.760 | 126.590 |
| 上一轮新视图输入 tokens | 285,825 | 276,249 |
| 本候选输入 tokens | 286,106 | 276,567 |
| 本候选输出 tokens，含推理 | 22,696 | 21,812 |
| 本候选总 tokens | 308,802 | 298,379 |
| Memory 提案 | 新增 1，修订 2 | 修订 2 |

合计 562,673 输入、44,508 输出、607,181 总 tokens；输入较上一轮仅增加 599 tokens。API 报告 R06 命中 3,072 cached input tokens，未人为改变缓存设置。没有估算货币费用，不以单次时长推断速度改进。

## 三项重点结论

| 审查重点 | 实际结果 |
|---|---|
| 事实准确性 | R06 tomato 身份正确、plate 的局部节省与总步数净增加区分清楚；但 R05 否认实际出现的直接动作回退，仍有 absent-target 表述，R06 仍混用“空”与“无目标” |
| 重要比较完整性 | R05 恢复 apple 14→11、两项各 +1 的比较；R06 保留 plate 9 对 8 和 book 修复前循环。仍遗漏 cool tomato 两侧温变相同，以及历史 heat plate 的 13 步成功对 50 步失败 |
| Knowledge 可采用性 | 两轮所有结构/归档检查通过，但五条原样提案仍各有需要处理的语义问题，暂不直接采用；不通过额外生成或人工改写掩盖问题 |

逐项原文、事实反证、范围边界和采用判断见 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)。这次不是仅靠减少描述避开旧错误：若干重要比较确实重新出现并描述正确；同时也不能把“比较变完整”当成“整体知识已可靠”。每种 Prompt 每轮仅一个输出，不足以证明稳定准确率或可自动发布。

## 隔离 Memory 验证

两轮均通过：原样提案结构/引用、隔离提交与重载、幂等性、旧 archive 字节不变、原 Active Memory 不变、v3 全动作/反馈保留、详细状态及菜单一致、数字引用窗口、后续 Preconditioner 投影、未来 Replay Pair 来源恢复。

- R05：新 M10，M6 → M11，M8 → M12；未来历史 Pair 为 40。
- R06：M10 → M12，M7 → M13；未来历史 Pair 为 35。

上下文为 `v23_4_R05_prompt_candidate_001` / `v23_4_R06_prompt_candidate_001`；编号仅属于各自隔离预览，不与旧实验同号条目混用。没有自动发布 Memory、提升 Candidate 或执行新 Actor。

复核命令（均不调用模型）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_prompt_candidate_001.run audit
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_prompt_candidate_001.check_memory R05
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_prompt_candidate_001.check_memory R06
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_prompt_candidate_001.review_facts
```

本轮没有生产代码变更；验证聚焦实际请求不变量、完整归档、Memory 往返和事实断言，未重复无关测试。调用记录见 [AUDIT.json](AUDIT.json)。完整拼接 Prompt 可分别查看 [R05](config/R05/system_prompt.md) / [R06](config/R06/system_prompt.md)。
