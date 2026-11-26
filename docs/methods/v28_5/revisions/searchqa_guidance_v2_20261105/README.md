# v28.5 SearchQA 领域指导 Prompt v2 接入记录

日期：2026-11-05。状态：**已冻结旧版、接入审阅稿并通过离线验证；没有启动实验。**

## 1. 当前绑定

| 模块 | 当前 Prompt 标识 | 接入结果 |
|---|---|---|
| Diagnosis | `v28_5_searchqa_diagnosis_v2` | 与最终审阅稿逐字一致 |
| Preconditioner | `v28_5_searchqa_preconditioner_v2` | 与最终审阅稿逐字一致，保留 Parent＋Memory 的 D/S/C 预条件机制 |
| Editor | `v28_5_searchqa_editor_v1` | 正文、标识及代码均未改 |
| Replay | `v28_5_searchqa_replay_v2` | 与最终审阅稿逐字一致，仅调整答案变化解释段 |

正式正文：[Diagnosis](../../prompts/diagnosis.md) / [Preconditioner](../../prompts/preconditioner.md) / [Editor](../../prompts/editor.md) / [Replay](../../prompts/replay.md)。采用了审阅确认的 `conventional answer form` 与 `smallest sufficient answer unit`，仅删除真正冗余内容；未采用以 `shortest unambiguous` 为主导目标的初稿措辞。

方法仍为 `v28_5_campaign_v1`，stage 为 `v28_5_stages_v1`，runtime 为 `v28_5_light_runtime_v1`。contract、输入视图、Memory、Gate 均保留原身份与算法。方法源文件的唯一修改是三个模块的 `PROMPT_VERSION` 常量；不是另换一套预条件方法。

## 2. 旧版冻结与可审阅差异

- [旧版冻结清单](baseline_manifest.json)：38 个文件的精确副本与 SHA-256，包括全部 20 个运行 Python 源文件、四份 Prompt、三个配置、CLI、原验收脚本、涉及的测试及说明。
- `baseline/` 使用仓库相对路径保存副本；用于追溯与恢复原文件，不是脱离仓库依赖的独立运行环境。
- 清单还记录历史 v28.5 campaign／automation／evaluation 的 48 个顶层 JSON／Markdown 身份文件哈希；离线检查确认未变化。既有实验目录没有被本次接入写入。
- [Prompt 差异](prompts.diff)、[运行绑定差异](binding.diff)、[接入完整差异](implementation.diff)。Editor 在 Prompt diff 中没有变化。
- [当前文件清单与哈希](release_manifest.json)，以及 [已采纳的方案](../../proposals/searchqa_guidance_20261105/README.md)。方案和当时的静态验证记录保持冻结，本次运行接入检查以本页报告为准。

上游材料及许可保存在 [SkillAdam 来源快照](../../proposals/searchqa_guidance_20261105/reference/skilladam/)。本次没有修改 SkillAdam 或 SkillOpt 的实现、Prompt 或实验结果。

## 3. 参数与机制保持范围

当前默认 [batch60 配置](../../../../../experiments/configs/v28_5_searchqa_train600_batch60.json) 仅改变三个 `method.prompts` 值。优化池、题目顺序、10×60、训练／测试并发 60/15、Actor max_tokens=32,768、四个方法模块 max_tokens=65,536、初始 104 字符 Skill、重试和容量限制均保持。

Preconditioner 从 `Historical Memory by round` 到文件末尾的原正文逐字保留，包含完整 Parent／Original／引用执行／Memory 的输入、历史解释、D/S/C、KEEP／REPLACE／WITHDRAW、编译和输出合同。新增领域分类只是自然语言分析词汇，不进入字段或 Gate 条件。

程序仍执行：当前 Parent 批次 → Diagnosis → Preconditioner → Editor → 完整 Candidate 批次 → Replay → 原逐 Update Gate → Memory 与 Selected 发布。没有新增模型阶段、压缩器、分类状态、Selected 子集复测或 Memory 重写。

旧 batch30／batch50 配置和实验内部的冻结配置保留原文。新实现拒绝旧 Prompt v1 配置；不能通过在旧检查点中替换标识来继续训练。未来若运行 v2，应创建独立目录、使用共同初始 Skill 和空 Memory；本次未创建真实 campaign。

## 4. 离线验证结果

[机器报告](../../../../../artifacts/verification/v28_5_prompt_v2_20261105/validation.json) / [逐项测试日志](../../../../../artifacts/verification/v28_5_prompt_v2_20261105/unittest.log)

- **260 项全部通过**：v28.3 回归 129 项、v28.5 回归与修订隔离检查 131 项；失败、错误、跳过均为 0。
- 四份运行时渲染 Prompt 与最终审阅稿逐字一致。
- 对比旧版冻结源文件：20 个运行源文件只允许三个版本常量变化；CLI 未变；Parent＋Memory、Gate、Memory 和执行算法未变。
- 检查当前真实数据配置、10×60 顺序和 1,400 题测试划分，但不执行这些任务。
- CLI `--validate-only` 通过，凭据读取和真实 train/test 函数均被阻断，临时目标 campaign 未创建。
- 新增检查覆盖旧 Prompt 标识拒绝、旧 v1 检查点在 v2 下拒绝恢复，并验证没有 Actor／生成器调用及检查点改写。
- 现有合成回归覆盖 Parent／Memory 传递、提案和 patch 合同、Replay 的 EM-only 事件、F1-only 不投票、null 关联、Gate 选择、原子发布及恢复。
- 网络连接和子进程创建在离线检查期间被阻断；尝试次数为 0。真实模型调用为 0，真实训练／Test 启动为 false；没有新增或唤醒自动化。

合成测试使用本地手写响应，临时目录中的流程不属于 benchmark 实验。这些结果验证接线和软件合同，不证明模型会遵循领域指导，也不证明泛化或准确率提高。历史 1150/1400 是 Prompt v1 的结果，当前 v2 没有实验成绩。

## 5. 离线复核入口

在仓库根目录执行以下命令，只运行离线检查；输出目录可换成新的审计目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/SearchQA/bin/python scripts/verification/verify_v28_5_prompt_v2.py --output artifacts/verification/v28_5_prompt_v2_20261105
```

原 `verify_v28_5_campaign.py` 保留为初次实现时的历史脚本，其中旧版配置假设不适用于本修订；当前应使用上面的新入口。

本次授权的冻结、接入、离线验证均已完成，实验维持未启动状态。
