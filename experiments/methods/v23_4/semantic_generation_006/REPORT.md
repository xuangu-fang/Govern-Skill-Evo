# R05 冻结输入与当前版本 Preconditioner → Editor

日期：2026-10-22（Asia/Shanghai）。

**完成用户指定的两步：复用可用 Original Plan 并冻结输入；使用当前版本完成一轮 Preconditioner → Editor。两阶段均首次结构通过，共 2 次 HTTP、0 次重启。语义审查未完全通过，原始结果保持不变。**

## 输入与实验边界

- 使用原 V23.3 R05 Diagnosis，来源为 `experiments/methods/v23_3/p3a_first_live_comparison_001/runs/diagnosis`。通过原版本 loader 核验响应、Grouping、Prompt、Plan；本次未重新生成 Diagnosis。
- 重建后的 Parent、Original Plan、当前事实、Grouping、Memory 与 study 001 的 R05 case 完全相同；Preconditioner user message 也完全相同。
- Plan 引用筛选了六条完整当前轨迹：P1/P3/P6/P7/P8/P10；原始批次不限于这六条，未替换或重新采样任务。
- Memory 为 M1/M2/M3/M6/M7/M8/M9；未混入 R06 未采用的 M12/M13，未写入任何 Active Memory。
- 本轮没有改动生产源码或 Prompt。相对旧 study 001，复用已经完成的四处版本变化：Preconditioner Prompt、Check 引用校验、facts/memory 的空动作兼容。旧冻结归档未覆盖，新旧 SHA256 明确记录在 [provenance](config/provenance.json)。
- Preconditioner 输入 968,366 字符，本实验预算 1,200,000；Editor 输入 14,119 字符，预算 200,000。生产 Preconditioner 默认 100,000 未改变。
- 通过独立实验适配器调用当前生产 Prompt/校验/Patch 编译函数；不声称完成了生产持久化加载器的全链路验收。旧 R05 的输出和审查意见未提供给本轮模型。

生成前 Original 可复用的理由见 [INPUT_REVIEW.md](INPUT_REVIEW.md)。

## 运行与结果

| 阶段 | HTTP / 重启 | 耗时 | 结果 |
|---|---|---|---|
| Preconditioner | 1 / 0 | 275.384 秒 | u1 KEEP；u2 进行 S 变换；u3 KEEP；Checks 保留 |
| Editor | 1 / 0 | 89.019 秒 | 生成非空严格 Patch，Candidate 和真实 Diff 均已保存 |

API 报告用量：282,475 prompt + 48,595 completion = **331,070 tokens**，金额未知。两个阶段的 `finish_reason` 均为 stop，未升高输出预算，没有 HTTP 429、技术失败或语义重采样。

u2 的主要变化是将跨类型扩展要求调整为“优先尚未尝试的类型”，并把反回访条件更多限定到当前/近期可见信息及短循环。没有沿用旧 R05 输出的“两次后切换”阈值。u1/u3 文本和 basis 与 Original 完全相同。

## 语义发现

Preconditioner 的 `change` 与 Update Patch 基本对应，但理由有三处明确问题：

1. 称 P8 从未访问 countertop，实际第 7、13、20 步都访问过。
2. 称三个非法导航都紧接同位置直接动作，实际 P1:4 后去了 desk；只有另两个例子支持该序列。
3. 把支持保留 u3 的动机表述成“不会造成退化”，超出了证据。

Editor 读取了正确的 Effective Plan，但再次将完整 u3 放在非 desklamp 章节之内，静默缩小了未被 Preconditioner 缩小的适用范围。**因此不能把此 Candidate 判定为忠实实现全部 Effective Updates。** u1/u2 基本落实，未发现另外新增的主要行为策略。

历史引用具体性、Original 跨类型要求的解释、局部历史窗口仍未彻底解决的限制，详见 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)。这些问题均原样记录；没有修改输出或 Prompt 来制造通过。

## 已完成的检查

- 原 Diagnosis 重载、原始输入精确相等、Memory 身份与消息投影检查。
- 当前源码与输入冻结 SHA256；两个阶段请求、原始输出、JSON 解析、首次合法选择和严格 Patch 校验。
- 每个 Original Update 对应一个 Adjustment，u1/u3 Keep 原文与 basis 未变，Checks 保留。
- Editor 输入精确等于编译出的 Effective Plan 与冻结 Parent。
- Editor 作者 Patch 构建 Candidate；规范化实际 Diff 独立重建 Candidate 完全相等。
- 独立 handoff 快照与 SHA256 已保存，标明需要语义审查，不作为自动准入。

本轮未修改生产实现，因此未重复运行上一轮已通过的整套测试；针对本轮真实产物进行了上述归档、引用、编译、交接与重建验证。检查结果见 [AUDIT.json](AUDIT.json) 和 [HANDOFF_AUDIT.json](HANDOFF_AUDIT.json)。

## 交付产物

- [Original Plan](handoff/original_plan.json)
- [Effective Plan](handoff/effective_plan.json)
- [Editor 输入](handoff/editor_input.json)
- [Candidate Skill](handoff/candidate.md)
- [实际 Skill Diff](handoff/actual.diff)
- [输入冻结清单](config/freeze.json) / [交接快照清单](handoff/freeze.json)

离线复核：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.semantic_generation_006.run audit
```

当前工作到此止于用户指定的两步。未运行 Actor、Replay 或完整消融，未采用任何新 Memory。后续若评估当前 Candidate，必须明确 u3 的范围实现偏差，不能将其行为结果直接视为完整 Effective Plan 的执行效果。
