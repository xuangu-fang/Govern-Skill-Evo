# SkillAdam DocVQA：与 v29 对齐的适配与离线验收

更新：2026-11-02。适配实现及离线验收已完成；未调用真实模型，未启动试跑、正式训练或最终 Test。

## 实验边界

这是使用相同 Actor、数据和模型条件的 SkillAdam 对照实验。优化算法来自本地开源 SkillAdam 的 DocVQA main-result 配置；模型替换、Actor 输出预算以及跳过 Stage0 是明确的实验差异，因此不称为论文结果的原样复现。

| 项目 | 当前配置 |
| --- | --- |
| 环境 | `/Users/didi/miniforge3/envs/DocVQA/bin/python`，复用现有环境 |
| 数据版本 | `539088ef8a8ada01ac8e2e6d4e372586748a265e`，复用现有本地数据 |
| 数据划分 | 原 Train 107 + Val 53，顺序合并为优化池 160；独立 Test 374 |
| 初始 Skill | SkillOpt DocVQA 原始 `initial.md`，与 v29 内容一致；不运行 Stage0 |
| 调度 | seed 42，顺序、不打乱，batch 15，10 批 15 题 + 1 批 10 题，共 11 次迭代 |
| 验证题目 | 每轮 Gate 使用同一批题目，保持开源 `same_batch` |
| 并发 | 原生 workers 60；实际训练批次最多 15 个并行任务；Test workers 60 |
| 模型/API | `deepseek-flash`，DeepSeek 官方 Chat Completions，temperature 1，medium reasoning，thinking enabled |
| Actor 输出上限 | 32,768 |
| 优化器输出上限 | 每次生成 16,384，适用于 iteration patch 和 Momentum update |
| 超时 | 300 秒；连接超时 10 秒 |
| Actor 重试 | v29 原实现：技术失败和 length 共享最多 6 次请求，恢复不重置，错误答案不重采样 |
| 优化器请求重试 | 保持 SkillAdam OpenAI-compatible 后端默认 `max_retries=2`；不套用 v29 五模块重试规则 |
| 补丁重试 | 原生 `patch_attempts=3`，错误反馈及后续请求由 SkillAdam 处理 |
| 上下文 | deterministic 轨迹压缩，估计上下文上限 110,000，原生上下文重置行为 |
| Momentum | 开源 Issue Tracker、DocVQA taxonomy、工具 schema、更新流程 |
| 动态编辑预算 | base 4、minimum 1、beta 0.9、metric hard、v_max 0.04 |
| 停止配置 | max_iterations/min_iterations/max_consecutive_failures 均为 11 |

Gate 使用 `gate_profile=main-result`，由上游映射到 `DocVQAAcceptanceGate.for_v2()`：hard 或 soft 至少提升 0.01，同时两项下降都必须严格小于 0.05。soft 就是 ANLS。浮点边界处理直接由原生 Gate 执行，不使用 v29 的 hard 严格提升 Gate，也不使用 DocVQA 类的 v1 默认值。

原生流程每批分别执行 training rollout、validation Parent 和 validation Candidate。题目相同，但它们是三次独立执行，不合并 Parent 结果；补丁无法应用时沿用上游处理。因此，完整合成验收的 160 题流程包含 480 次 Actor 执行，这不是生产请求预算承诺：真实请求还受补丁结果及技术重试影响。

## 实现位置与复用边界

- 配置：[docvqa_skilladam160_epoch1_deepseek_flash.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/configs/docvqa_skilladam160_epoch1_deepseek_flash.json)
- 适配层：[skilladam.py](/Users/didi/Desktop/Govern-Skill-Evo/src/adapters/docvqa/skilladam.py)
- 入口：[run_docvqa_skilladam.py](/Users/didi/Desktop/Govern-Skill-Evo/scripts/runs/run_docvqa_skilladam.py)
- 验收：[verify_docvqa_skilladam_offline.py](/Users/didi/Desktop/Govern-Skill-Evo/scripts/verification/verify_docvqa_skilladam_offline.py)

Actor 直接复用 v29 的 `protocol`、`DocVQAActorAdapter`、归档和评分实现，保留完整问题、原始图片、auto detail 和普通响应。SkillAdam adapter 使用同一普通响应重新按原生 ANLS/hard 规则评分；隐藏 reasoning 不传给优化器。

优化器接收原生 sanitized trajectory 和 deterministic condensed trajectory；图片在原生解析中替换为文件名占位符。没有引入 v29 五模块、Plan/补丁合同、Replay 或 Memory。优化器 Prompt 模板保留原生版本，其中 vendor prompt 字段引用实际执行的 v29 Actor 基础协议；注入的 Skill Writing Policy 仅对初始 Skill 的结构要求作本地兼容调整，见下文。

本次只新增独立适配文件，没有修改 `external/SkillAdam`、v29 源码、v29 正式配置或已完成的实验数据。复用了现有的 Momentum 顺序恢复辅助函数及原始 HTTP 响应记录辅助函数。

2026-11-02 结构兼容修订：本地 [skill_structure.md](/Users/didi/Desktop/Govern-Skill-Evo/src/adapters/docvqa/skill_structure.md) 替换注入 policy 的第 1、2 节。允许沿用当前 Skill 的章节名称及无 YAML 格式；Workflow / Error Avoidance 表示指导内容的职责，不强制作为章节名称；不应仅为符合模板而重排结构或添加元信息。第 3–6 节仍直接使用上游原文。初始 Skill、Actor、Momentum Prompt、评分、Gate、预算及其余上游表述均未调整。

## 归档与恢复

训练输出放在 `experiments/baselines/docvqa_skilladam/<run-name>/`，Test 放在 `experiments/evaluations/docvqa_skilladam/<run-name>/`。

- `config.json`：此次运行配置。
- `native/checkpoint.json`：原生当前 Skill、下一轮位置、Momentum、方差 EMA 和待完成的 post-decision 操作。
- `native/iterations/`：原生训练轨迹、补丁、Gate 结果和优化器对话。
- `execution/rollouts/iter_NNN/`：training、validation_parent、validation_candidate 各自的 v29 Actor 归档。
- `execution/optimizer/`：实际优化器输入和已完成的普通文本/工具调用结果；恢复时复用已完成结果。
- `execution/raw_optimizer/`：优化器 HTTP 请求和原始响应正文，不写鉴权头。
- `execution/usage_events.json`、`native/usage.jsonl`：按阶段记账，复用完成结果不重复累计。
- `final_skill.md`、`training_summary.json`：11 批完成后导出。

首次外部请求前保存原生 checkpoint，因此第 0 轮也可恢复。`--resume` 恢复原目录的原生状态；已完成 Actor 题目和优化器生成被复用。优化器在远端完成但本地尚未保存结果的请求仍可能在恢复时重新发送，这是本地归档不能消除的窗口；未新增跨进程优化器请求总额度机制。

最终 Test 必须读取完整训练导出的最终 Skill，并与原生 checkpoint、原生 final_skill 核对一致。Test 不调用优化器，也不更新训练目录和 Momentum；未完成训练不能启动 Test。

## 离线验收

2026-11-02 首次适配验收 46 项通过。结构兼容修订后的当前验收：**47 项通过，0 failures，0 errors，0 网络尝试，0 真实模型请求**。包括 22 项适配检查和 25 项共享 v29 Actor 检查；新增检查验证实际组装 Prompt 的结构兼容表述、初始 Skill 内容保留及 policy 第 3–6 节不变。

- 534 题实际消息与 v29 一致，439 张图片可读，划分及顺序与当前本地 SkillAdam profile 一致。
- 原生 v2 Gate：hard 提升、soft 单独提升、持平、下降边界。
- 合成完整迭代、ACCEPT/RETAIN 的 Momentum 更新、原生空补丁流程。
- 非零逐题方差驱动编辑预算从 4 变为 1，跨轮恢复保留 EMA、预算和对话历史。
- 合成 11 批完整运行，包含最后 10 题；Stage0 未调用。
- Actor 批次中断、六次额度耗尽、首次补丁中断、Candidate 中断、pending Momentum 恢复，已完成步骤不重复请求或记账。
- Mock HTTP 验证优化器模型、thinking、预算、超时和工具调用；原始归档不含测试密钥。
- 合成 Test 使用固定最终 Skill；中断/完成后可恢复，训练未完成时阻止执行，训练目录保持不变。

验收通过 socket 阻断网络，并禁止启动子进程。合成实验保存在自动清理的临时目录；真实数据仅只读检查。

当前报告：[validation.json](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/verification/docvqa_skilladam_structure_compat_20261102/validation.json)

详细日志：[unittest.log](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/verification/docvqa_skilladam_structure_compat_20261102/unittest.log)

只读预检和离线验收命令：

```sh
/Users/didi/miniforge3/envs/DocVQA/bin/python /Users/didi/Desktop/Govern-Skill-Evo/scripts/runs/run_docvqa_skilladam.py preflight
/Users/didi/miniforge3/envs/DocVQA/bin/python /Users/didi/Desktop/Govern-Skill-Evo/scripts/verification/verify_docvqa_skilladam_offline.py --output /Users/didi/Desktop/Govern-Skill-Evo/artifacts/verification/docvqa_skilladam_structure_compat_20261102
```

入口默认就是 `preflight`，不读取凭据。`train` 和 `test` 是显式子命令，支持 `--resume`；不存在自动训练转 Test。正式 11 批入口已实现；一批试跑的停止入口尚未添加，后续获准试跑时再补充，不通过修改正式配置的 11 批参数冒充正式训练。

下一步是单独授权的一批真实试跑，验证模型实际输出、长度和耗时；本轮离线通过不代表已经验证了真实模型兼容性或优化效果。
