# ALFWorld v24.2

[正式实验、最终 Skill 与两次 Test](../../../experiments/methods/v24_2/v24_2_alfworld_20261106_195800/README.md) · [方法源码](../../../src/skill_evolution/v24_2/) · [自动化测试](../../../tests/skill_evolution/v24_2/) · [本次目录调整](LAYOUT.md)

本稿固定四模块的交接、逐 Update 选择和发布语义。实验基线取自 [V24.1 官方模型配置](../../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/campaign.json)。从原初始 Skill、空 Memory 开始，复用 ALFWorld Actor、任务顺序、步数限制和评分方式。

## 一轮

Parent 同批执行 → [Diagnosis](../../../src/skill_evolution/v24_2/prompts/diagnosis.md) 直接读全批 → [Preconditioner](../../../src/skill_evolution/v24_2/prompts/preconditioner.md) 读原 Plan 引用的完整执行和已发布 Memory → 程序编译有效 Plan → [Editor](../../../src/skill_evolution/v24_2/prompts/editor.md) 对同一 Parent 逐 ID 生成补丁 → 联合 Candidate 同批独立执行 → 全批校验 → [Replay](../../../src/skill_evolution/v24_2/prompts/replay.md) 解释翻转 → Gate 选择 → 原子发布 Selected Skill 与本轮 Memory。

Editor 动态输入仅含 Parent 和有效 Plan。固定上下文的 system、首步和带历史模板由 V24.1 的 `output_protocol(campaign.actor_output_format)` 生成。运行配置与该快照须匹配。

## Gate、Memory 与发布

1. 先校验完整任务覆盖、同题配对、实际 Skill、不同执行身份、Actor 条件与环境终局。正常耗尽步数且未成功的 `step_limit` 可作为失败侧。中断、技术错误、缺失终局或任一校验失败，停止计票与发布。
2. 只把原生成功标志翻转的题送 Replay，每题恰好一条 Knowledge。若双方均失败，即使 Candidate 完成了额外中间步骤，也只保留原始轨迹。无翻转时跳过 Replay，有翻转但无法归因时保留 null 事件。
3. 每个翻转至多投给一个非空补丁。对每个这样的 Update 单独计算 G（明确关联的失败转成功）和 L（明确关联的成功转失败）。仅 G 为正则 Retain，仅 L 为正则 Reject，两者都正或都零则 Defer。null 事件零票。空字符串补丁的决定为 null。
4. 将 Retain 补丁按有效 Plan 顺序重新应用于原 Parent。选出文本与 Parent 或实际 Candidate 完全一致时分别记录 parent 或 candidate；新组合记录 `selected_execution_source=null`，本轮成功率留空。子集无法合法组合则阻止发布。
5. Memory 按轮追加所有有效 Update 的 ID、文本及 Gate 决定，每道翻转事件按冻结配对顺序单独获得稳定 Memory ID，包括 null 关联。Selected Skill 与 Memory 共用一个原子发布点。恢复从同一已发布状态继续，重试同一轮不得重复追加事件。
6. 无提案或全部撤回时沿用原 Parent 与 Memory，进入下一批。所有补丁为空字符串时记录有效 Updates、空决定与空事件，发布原 Parent。任一补丁为 null 表示实施阻塞，本轮不发布。

## 首个离线验收案例

同批四次翻转：第一题收益、第二题退化均关联 u1，第三题退化且关联为 null，第四题收益关联 u2。预期 u1 为 Defer，u2 为 Retain；四条事件各有一个 Memory ID。两个补丁都产生实际文字修改时，Selected 仅应用 u2，执行来源为空。再加入一道同败但有局部进步的题，事件数仍为四。将完整执行替换为 interrupted 后，发布点须保持上一轮状态。

这组案例可用固定轨迹与预设模型响应验收程序合同。领域语义另查三项：Diagnosis 交接决定例外的成功案例，Preconditioner 在原 Parent 上检查单条独立成立，Editor 对空补丁指出协议或 Parent 依据。

## 运行与复核

独立入口为 `python -m src.skill_evolution.v24_2`。从仓库根目录运行。调度进程使用 Python 3.10+（需要 requests、python-dotenv），正式 Actor 子进程仍使用 V24.1 配置指定的 ALFWorld Python 3.9 环境。

复现一轮合成验收（需要 pytest；脚本阻断网络连接与子进程）：

```sh
/Users/didi/miniforge3/bin/python -m tests.skill_evolution.v24_2.test_round --campaign /tmp/alfworld-v24-2-offline
```

真实配置可用 `python -m src.skill_evolution.v24_2 prepare --campaign <新目录>` 准备，用 `status` 读取已发布游标。`run-round` 显式执行一批；中断后再次执行同一命令会核验已保存轨迹与模型响应，从未发布的轮次恢复。正式配置有六批，全部发布后导出 `final_skill.md`。离线验收和正式 campaign 使用独立目录。

`rounds/R01/` 保存逐模块实际输入、各尝试的消息与响应、全批配对核验、Gate 结果和选出的 Skill。`HEAD.json` 指向包含 Skill、Memory 和下一轮游标的提交。针对中断、无提案、全部撤回、空补丁、冲突、无翻转、跨题引用与跨轮继承的回归测试位于 `tests/skill_evolution/v24_2/`。

## 独立 Test

正式训练六轮发布后，从仓库根目录运行。将两个路径替换为实际目录。Test 从训练 HEAD 的提交链读取最终 Selected Skill，复用 V24.1 相同的 134 道保留题、Actor 和逐题校验。输出目录应与训练目录分开。

```sh
/Users/didi/miniforge3/bin/python scripts/runs/v24_2/run_v24_2_test.py \
  --campaign /path/to/completed-training --evaluation /path/to/test-output
```

加 `--validate-only` 可只读核验训练发布链、Test 清单和本机 Actor 环境，不发送模型请求。中断后使用相同路径加 `--resume`，复用已完成的轨迹。全部完成后，Test 目录下的 `summary.json` 给出成功数、成功率和逐题结果；`input.json` 保存训练 HEAD 和实际评估的 Skill。
