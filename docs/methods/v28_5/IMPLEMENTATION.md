# v28.5 独立实现与必要检查

## 当前接入：SearchQA 领域指导 Prompt v2（2026-11-05）

当前实现与结果以 [Prompt v2 修订记录](revisions/searchqa_guidance_v2_20261105/README.md) 为准。新离线入口为 `scripts/verification/verify_v28_5_prompt_v2.py`，覆盖当前 batch60 配置、审阅稿逐字绑定、Parent＋Memory 核心正文、源代码仅版本常量变化，以及旧 Prompt 检查点拒绝恢复。原 `verify_v28_5_campaign.py` 与旧报告保留为初次实现的历史材料，其 batch30／旧 Prompt 假设不适用于当前版本。

本次未调用真实模型，未启动训练、Test、supervisor 或自动化。下面的启动、暂停、完成、参数调整和原复现命令均为历史记录；不构成恢复实验的指令。

## 历史实现记录

2026-11-04：已基于 v28.3 完成独立运行实现和必要离线检查，直接绑定已定稿的四份 Prompt，包括 Preconditioner 关于指令强度与优先级的最后一句微调。实现阶段未运行真实训练或 Test。随后用户授权完整实验，22:09 已启动训练，Test 与比较等待训练完成；见 [运行状态](../../../experiments/automations/v28_5_searchqa600_batch30_20261104_220800/status.json)。未增加独立 Prompt 验收场景或固定输入模型对照。

历史状态：2026-11-04 22:38 用户要求暂停。已完成 R01–R05，R06 Preconditioner 中暂停；supervisor、训练进程和 heartbeat 均已暂停。此前启动说明保留为历史记录，尚无正式 Test 结果。

暂停后已按用户要求微调 Editor 的一段表达指导，运行器会直接加载修订稿。其余 Prompt、代码与实验参数不变；旧实验快照未改写，也未恢复或新启动训练。最新修订检查见 [editor_revision_validation.json](editor_revision_validation.json)。下文 258 项软件检查及其原快照属于微调前记录，不能视为对新 Prompt 压缩效果的验证。

后续又按用户认可的方案对 Preconditioner 与 Replay 各替换一段，澄清支持案例回查、basis 冻结、条件未知与被否定的区别。代码和参数仍不变；当前完整 Prompt 的离线核对见 [evidence_revision_validation.json](evidence_revision_validation.json)。以上 Editor 检查记录反映其修订时点，最新 Prompt 以当前文件及本条记录为准。

历史状态更新：2026-11-04 22:55，已核对配置和三处 Prompt 修订并启动独立新实验 `v28_5_searchqa600_batch30_revised_20261104_225519`，从初始 Skill、空 Memory 的第一轮开始；旧进程继续暂停。新实验完成训练后自动运行最终 Test 和对比，见 [新运行状态](../../../experiments/automations/v28_5_searchqa600_batch30_revised_20261104_225519/status.json)。前述暂停及修订记录保留为历史。

最新状态：修订后实验已由用户暂停。现已撤回 Editor 表达压缩段落及两处措辞细化，逐字恢复首次 v28.5 实验冻结版本；Preconditioner / Replay 证据一致性修订保留。运行代码、配置与两次实验归档未改动，两组进程及 heartbeat 均保持暂停，未重启训练。当前核对结果见 [editor_rollback_validation.json](editor_rollback_validation.json)；上述修订与启动说明保留为历史记录。

最新配置调整：训练改为 12×50；600 题顺序及其他参数不变，尚未启动。新增 batch50 配置并设为默认，CLI 从配置读取批次大小；共享数据层新增 50 题支持，保留 15/30 题原行为及 Actor 预算。v28.5 校验兼容旧 batch30 与新 batch50；旧实验归档保留。下述“仅版本替换”和 258 项检查为初次实现历史，当前修改检查见 [batch50_validation.json](batch50_validation.json)。

最新状态：Editor max_tokens 已调为 65,536；新实验 `v28_5_searchqa600_batch50_editor64k_20261104_232317` 于 23:24:30 启动，23:24:52 应用户要求暂停，supervisor 和训练进程均为 T 状态，Test 未启动，heartbeat 仍暂停。四份 Prompt 未改动。预检查通过；129 项测试中一处旧预算断言已同步，相关 7 项复查通过，无未解决失败。上述记录为历史，当前不得继续运行，等待用户指示。

当前配置更新：刚启动约 22 秒的 batch50 实验进程及实验数据已按用户要求终止、删除。已改为 10×60，训练并发 60、测试并发 15，Editor 65,536；四份 Prompt 不变。用户已授权检查通过后从头启动新实验，以上暂停记录为历史。当前状态以 README 与 source_map 为准。

最新运行状态：2026-11-04 23:28:09 已启动 `v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720`，supervisor PID 37771、训练 PID 37772，R01 实际批次 60 题且 workers=60；391 项离线检查通过。训练后自动执行最终 Test 和比较，heartbeat 已启用。

完成状态：训练、Test 和比较已于 2026-11-05 00:37:03 完成；Test 1150/1400，最终 Skill 14,151 字符。自动跟进已删除，以上运行中说明为历史。现有归档分析见 [analysis.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/analysis/v28_5_searchqa600_batch60_workers60_editor64k_20261104_232720_failure_analysis/analysis.json)，未新调用模型或改写 Prompt。

## 1. 实现入口

| 部分 | 文件 |
|---|---|
| 独立运行包 | [src/skill_evolution/v28_5](../../../src/skill_evolution/v28_5/) |
| train/test CLI | [run_v28_5_campaign.py](../../../scripts/runs/run_v28_5_campaign.py) |
| 运行配置 | [v28_5_searchqa_train600_batch60.json](../../../experiments/configs/v28_5_searchqa_train600_batch60.json) |
| 离线检查入口 | [verify_v28_5_campaign.py](../../../scripts/verification/verify_v28_5_campaign.py) |
| 软件测试 | [tests/skill_evolution/v28_5](../../../tests/skill_evolution/v28_5/) |

20 个 Python 运行源文件和 CLI 从 v28.3 派生，只替换版本名、内部导入与 Prompt 路径。核对时对这些身份进行替换后逐字比较；没有更改算法。不同版本使用独立的 method/stage/runtime/contract/view 身份，旧配置和旧 campaign 不能重标记后恢复为 v28.5。

四份 Prompt 从本目录 `prompts/` 加载，和实现前保存的定稿逐字比较。完整 Parent 原本就在 Preconditioner 输入中；本次增强其使用方式，不增加输入字段。Memory、Gate、逐 Update patch、共享执行视图、请求额度、重试与恢复行为均继承 v28.3。

## 2. 实验参数

运行配置与冻结 v28.3 配置在替换版本身份后完全相同，包括 600 题的 ID、顺序与 20×30 批次、104 字符初始 Skill、Actor 参数、方法参数、输入限制和重试策略。

- Actor、Editor：max_tokens=32,768。
- Diagnosis、Preconditioner、Replay：max_tokens=65,536。
- 全部模型：deepseek-flash，temperature=1.0，thinking enabled，reasoning_effort=medium。
- Train/Test workers：15/15；最终 Test 保留 1,400 题。
- 初始 Memory 为空；不继承旧实验的最终 Skill 或 Memory。

完整参数见 [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) 和运行配置。

## 3. 检查范围与结果

检查结果以 [validation.json](../../../artifacts/verification/v28_5_implementation_20261104/validation.json) 为准，逐项日志见 [unittest.log](../../../artifacts/verification/v28_5_implementation_20261104/unittest.log)。

**258 项全部通过**：v28.3 回归 129 项、v28.5 检查 129 项；失败、错误和跳过均为 0。完整配置只读预检查通过。20 个运行源文件及 CLI 仅有版本替换；76 个受保护文件逐字不变，包含 v28.3 基线、四份定稿 Prompt 及冻结副本。没有网络或子进程调用尝试。

检查覆盖继承的 v28.3 软件回归和 v28.5 接线、版本隔离、完整输入传递、KEEP/REPLACE/WITHDRAW 编译、patch 应用、Replay 事件边界、Gate、Memory 原子发布，以及中断恢复和六次总请求额度。测试中的响应由本地手写函数提供，使用临时合成数据，不向模型发送请求，也不是对 Prompt 决策质量的场景验收。

运行检查期间阻断网络连接与子进程创建。真实 600 题配置仅做只读预检查：检查数据与冻结参数，不读取凭据、不创建 campaign。实现前快照用于核对 v28.3 源文件、旧配置和四份定稿 Prompt 未被修改。

## 4. 复现离线检查

在仓库根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python scripts/verification/verify_v28_5_campaign.py --output artifacts/verification/v28_5_implementation_20261104 --baseline artifacts/verification/v28_5_implementation_20261104/baseline.json
```

只做完整配置预检查：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/SearchQA/bin/python scripts/runs/run_v28_5_campaign.py train /tmp/v28_5_preflight_not_created --config experiments/configs/v28_5_searchqa_train600_batch30.json --validate-only
```

第二条命令保留 `--validate-only` 时不启动训练或读取凭据。正式实验由后续授权的独立 supervisor 执行，详见 [启动记录](../../../experiments/automations/v28_5_searchqa600_batch30_20261104_220800/README.md)；以上离线检查报告仅记录实现阶段，不覆盖实时实验状态。

设计阶段的 [design_validation.json](design_validation.json) 保留当时的静态记录；当前实现检查以本页链接的报告为准。软件检查不能证明 Skill 会变短、重复冲突减少或测试成绩提高，这些结果留待实际实验。
