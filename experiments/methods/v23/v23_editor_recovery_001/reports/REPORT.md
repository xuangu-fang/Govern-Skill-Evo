# V23 Editor 相同请求技术恢复报告

本次额外一次调用由用户明确授权：保留原始失败，复用相同 Parent、Effective Plan、Prompt 与模型参数，不追加失败反馈、不自动修补 Patch。恢复独立存放于 `v23_editor_recovery_001`；没有覆盖原实验或建立新算法版本。

新模型输出通过严格补丁应用，生成完整 Candidate。**技术恢复成功不代表已经消除语义问题或验证行为收益。** 本次到此停止，未运行 Replay、上游模块或 ALFWorld。

## 请求一致性与原档案保护

调用前核对当前 `load_preconditioner()` 返回的 Parent、Effective Plan 和完整上游交接，与原 Editor 保存输入一致；重新渲染的 messages 与原 `request.json.body.messages` 完全一致。当前相关源码和 Prompt 与原实验冻结快照逐字节一致，未重新运行测试；沿用原来的 384 项测试与 19 个子测试通过记录。

调用后核对完整 `request.json`，端点、messages、模型参数、输出预算、超时和单次请求设置与原次完全一致：

| 项目 | 配置 |
|---|---|
| 模型 | deepseek-flash |
| temperature / thinking / reasoning_effort / stream | 1.0 / enabled / medium / false |
| max_tokens / timeout | 16,384 / 300 秒 |
| 实际输入／输入限制 | 11,005 / 100,000 字符 |
| 新增请求／自动重试 | 1 / 0 |
| 失败反馈／补丁修补 | 无 / 无 |

完整冻结请求保存在 [frozen_request.json](../../../../../artifacts/methods/v23/v23_editor_recovery_001/frozen_request.json)。[配置](../config/plan.json)中的恢复授权与实验说明仅用于程序侧归档，没有添加到模型消息中。

原实验的完整精选材料、原始失败目录和上游 Grouping／Diagnosis／Preconditioner 文件均在调用前后进行字节比较，保持不变；[保护清单](../../../../../artifacts/methods/v23/v23_editor_recovery_001/protected_files.json)记录了其文件摘要。保留[原始失败报告](../../v23_editor_001/reports/REPORT.md)，不将本次成功回写为原次成功。

## 实际输出与应用

[模型输出](../results/editor.json)只有 `patch / reason`。Patch 使用 `/dev/null → b/SKILL.md`，Hunk 声明 `@@ -0,0 +1,23 @@`，实际新增 23 行，末尾换行正确。原应用器一次严格应用成功，没有改行号、删除文本或补换行。

生成的 [Candidate Skill](../results/candidate.md) 含目标搜索、清洁交付、动作候选三个部分；[模型 Patch](../results/patch.diff)与[实际 Diff](../results/actual.diff)分别保留。本次 Parent 为 null，因此是初始创建，不能据此证明对已有 Skill 的局部编辑质量。

`load_editor()` 可读取并重新校验该结果。相同输入、Prompt 和配置下，以禁止请求的 generator 验证复用成功，零新增调用，文件不变。

```python
from src.skill_evolution.v23.editor import load_editor
saved = load_editor("artifacts/methods/v23/v23_editor_recovery_001/live")
candidate = saved["candidate_text"]
plan = saved["effective_plan"]
```

该接口提供后续 Replay 所需的有效文本产物、Plan 和来源。本次没有执行 Replay。

## 语义核查

- **u1：** 保留确定性搜索、避免循环、扩展容器类型以及回访例外。但仍要求区分全局已检查／未检查位置，有限历史如何支持这一判断尚未说明。模型没有返回阻碍，也没有解决这一能力限制。
- **u2：** 保留清洁先于交付、开目的容器、核对目标及不替代物品等要求。但“Follow dependency order”下第 1 项已经要求取得目标，第 2 项才写关闭源容器时先开再取，编号顺序仍有冲突。虽然第 2 项包含 before taking，不能据此认定整个流程表达一致。
- **u3：** 可用替代动作是具体恢复指导；第一句仅从当前候选中选择动作，仍重复基础协议。
- **其他：** 未发现轨迹编号、证据引用、任务具体答案、收益保证或独立的 Check 指令被加入 Skill。没有已有 Parent 内容可用于检验保留能力。

这些问题原样保留，没有针对当前结果修改 Prompt、Effective Plan 或 Candidate。相同请求的随机输出差异不构成模型质量提升或策略收益的因果证据。

## 消耗与停止边界

| 项目 | 本次实际值 |
|---|---|
| finish_reason / validation | stop / valid |
| 输入 Token | 2,147，其中缓存命中 1,920 |
| 输出 Token | 2,308，其中推理 1,889 |
| 总 Token | 4,455 |
| 耗时 | 9.395296 秒 |
| 含原失败的请求数／总 Token | 2 / 9,432 |
| 账单金额 | API 未返回，未估算 |

完整 [summary.json](../results/summary.json) 和 [HTTP 原始响应](../../../../../artifacts/methods/v23/v23_editor_recovery_001/live/http_response.txt)保留用量。本次源码与 Prompt 无修改，没有新增算法测试、环境执行、自动修复或第三次请求。
