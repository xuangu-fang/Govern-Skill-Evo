# R05 / R06 新视图真实 Replay 验证

日期：2026-10-22。**两轮均首次结构通过，2 次 HTTP、0 次重试；输入 token 下降约 40%，但语义仍有错误，原样 Memory 提案暂不采用。**

## 固定条件与运行

完全复用 `replay_input_view_001` 已冻结的 R05/R06 新模型视图：Actual Diff、Effective Plan、完整新配对执行、各轮原始历史 Memory 不变。没有加入旧 Replay 的预览条目、人工审查结论或 Original Plan。

沿用旧 Replay 的模型和参数：deepseek-v4.1-flash、temperature=1、thinking enabled/medium、max_tokens=32768。两个逻辑阶段顺序执行；每轮允许首次加三次技术重试，首次结构合法即停止。此次均 finish_reason=stop，无 429、长度或契约失败，无语义重采样。

本实验显式采用 1,200,000 字符请求上限容纳已冻结视图，生产默认 400,000 未改。实际请求字符数 R05 为 989,515、R06 为 959,309，均未截断。继续采用原独立评估事实链；新 Parent 执行没有生成旧 Diagnosis Plan，不冒充生产 Editor 原始谱系加载验证。

| 项目 | R05 | R06 |
|---|---:|---:|
| 当前任务对数 | 10 | 7 |
| HTTP / 技术重试 | 1 / 0 | 1 / 0 |
| 请求用时（秒） | 170.179 | 103.237 |
| 旧 Replay 输入 tokens | 480,881 | 462,460 |
| 本次输入 tokens | 285,825 | 276,249 |
| 输入降幅 | 40.56% | 40.27% |
| 本次输出 tokens（含推理） | 19,453 | 16,961 |
| 本次总 tokens | 305,278 | 293,210 |
| 原样提案 | 新增 1，修订 1 | 修订 2 |

两轮合计 562,074 输入、36,414 输出、598,488 总 tokens；旧两轮合计 981,782 总 tokens。均为 API 实际 usage，未估算货币费用。输入节省成立，但输出长度和推理量不同，不能把总 token 差额全部归于输入压缩。

## 语义结果

| 核查点 | 结果 |
|---|---|
| R05 历史搬杯/加热杯混淆 | 本次分清 R03 取杯与 R04 加热杯，旧误写未重复 |
| R05 desklamp 范围误归因 | 本次未重复，但也未充分讨论 Q2；不能视为该归因问题已彻底解决 |
| R06 步号强行同步 | 未再断言同一步取物，实际仍是第 3/4 步 |
| R06 温变局部/整体混淆 | 不再否认局部省步，但省略 plate 任务的 8→9 总步数及完整分解；仅部分改善 |
| 未找到 → 不存在 | 两轮均仍出现，是跨案例重复偏差 |
| 新偏差 | R05 遗漏 apple 14→11 并称 soapbar 是唯一明确步数差异；R06 把当前 cool tomato 写成 cool bread |

详细引用、事实反证、边界和未来 evidence 覆盖见 [语义核对](SEMANTIC_REVIEW.md)。目前不宜直接采用四条原样提案；未逐条人工修写或挑选发布。单次输出对照不足以证明稳定准确率提升或任何单项输入改动的独立贡献。

## Memory 往返与归档

两轮均通过：原始提案不变、结构/引用解析、隔离提交和重载、幂等提交、旧 archive 字节一致、原 Active Memory 不变、v3 全动作/反馈与详细状态/菜单一致、数字引用落入详细窗口、后续 Preconditioner 消费、后续 Replay 历史 Pair 恢复。

| 隔离预览 | 新条目 | 未来历史 Pair 数 |
|---|---|---:|
| R05 | 新 M10；M8 → M11 | 42 |
| R06 | M7 → M12；M10 → M13 | 33 |

上下文分别为 `v23_4_R05_view_replay_001` / `v23_4_R06_view_replay_001`。提交保存完整 evaluation bundle，保留本轮真实 Pair 来源。编号只属于各自预览，不与旧 Replay 实验同号条目混用。没有发布 Active Memory、更新 Candidate、重新执行 Actor 或修改核心 Prompt/算法。

审计材料：[调用审计](AUDIT.json)、[冻结清单](config/freeze.json)、[R05 Memory 审计](cases/R05/results/MEMORY_AUDIT.json)、[R06 Memory 审计](cases/R06/results/MEMORY_AUDIT.json)、[事实核对](FACT_CHECKS.json)。原始请求/响应、解析输出和隔离预览均保留。

仅离线复核（不会调用模型）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_input_view_live_001.run audit
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_input_view_live_001.check_memory R05
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_input_view_live_001.check_memory R06
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.replay_input_view_live_001.review_facts
```

本轮验证复用上一轮完成的输入实现与测试，不修改生产代码，不追加宽泛测试。新增事实断言已实际执行通过；语义结论来自上述人工核对，不由结构检查自动推导。
