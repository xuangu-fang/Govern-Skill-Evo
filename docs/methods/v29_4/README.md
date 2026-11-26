# v29.4：Diagnosis 直接分析完整批次

v29.4 以当前 v29.2 为基线，删除独立 Grouping 模型阶段，由 Diagnosis 直接比较当前批次执行并构造 Original Plan。没有新增中间报告。初始实现通过离线验收后启动了独立训练。2026-11-04 用户随后要求中断并删除该次运行，将 Editor 输出上限提高至 32,768，从初始 Skill 和空 Memory 重新训练，成功后自动运行 held-out Test。尚不能判断方法效果是否优于 v29.2。

## 方法边界

正常主流程为 Parent 批次执行 → Diagnosis → Preconditioner → Editor → Candidate 批次执行 → Replay → Gate → Memory/下一轮 Parent。

Diagnosis 模型输入恰为 `parent`、`runs`、`shared_initial`，保留完整成功和失败执行及无损共享文本视图。输出仍为 `decision/reason/plan`，Plan 为 `goal/updates`，Update 为 `id/text/basis`。Diagnosis 不读取历史 Memory、Candidate 执行、图片内容或隐藏推理。

在 v29.2 的当前证据分析部分加入：

> Compare common decision problems and important differences across current-batch executions. Use relevant and available successes, failures and counterexamples to form evidence-grounded Updates and determine their applicability conditions and preservation boundaries. A single execution can also support a reasonable proposal. Put direct execution references supporting these judgments in the corresponding Update basis. Not every execution needs to produce an Update.

这不要求每条 Update 同时具备成功、失败和反例，也不要求每条执行产生 Update。其余 Update 构造和历史调整指导保持 v29.2，不引入 v29.3 或 SearchQA `_v2` 的提示词修订。

`basis` 只接受合法当前执行引用。Diagnosis 的 reason、Plan goal、Update text/basis，以及 Preconditioner 的 reason/REPLACE text 不再授权 Group 来源。共享引用解析器保留对 `Group:` 的识别以拒绝它，不把旧引用当作普通文本放行。

Preconditioner 继续接收 Parent、Original Plan、Plan 直接引用的完整执行和历史 Memory。沿用 v29.2 从整个 Plan（goal/text/basis）选择执行的行为，Diagnosis reason 不参与选取。提示词仍要求重要支持案例和保护边界的依据明确写入 basis。

## 事实入口与版本接线

- [facts.py](../../../src/skill_evolution/v29_4/facts.py)：`build_parent_bundle(records, round_id)` 构建 `facts/background/sources/round_id`；`validate_parent_bundle(saved)` 复用 DocVQA 原始归档验证，拒绝旧 Grouping 交接对象。
- [diagnosis.py](../../../src/skill_evolution/v29_4/diagnosis.py)、[execution_input_view.py](../../../src/skill_evolution/v29_4/execution_input_view.py)：完整批次直接输入；输入投影和恢复保持无损。
- [preconditioner.py](../../../src/skill_evolution/v29_4/preconditioner.py)：使用新 Diagnosis 来源校验，保留 KEEP/REPLACE/WITHDRAW 编译行为。
- [output_feedback.py](../../../src/skill_evolution/v29_4/output_feedback.py)：事实和来源错误继续作为技术错误停止，只有识别出的输出错误进入原重试策略。
- [evolution.py](../../../src/skill_evolution/v29_4/evolution.py)、[stages.py](../../../src/skill_evolution/v29_4/stages.py)：四阶段接线、版本化请求日志、来源记录和中断恢复。
- [campaign.py](../../../src/skill_evolution/v29_4/campaign.py)、[evaluation.py](../../../src/skill_evolution/v29_4/evaluation.py)：独立训练和 Test 接线，沿用当前 v29.2 的轻量检查点行为。

Editor、Replay、Gate、Memory 使用本版本的接线副本，因为它们会逐层重新校验上游来源；直接整模块导入 v29.2 会再次要求 Grouping。其函数/类算法保持原样，验收比较 AST；Editor/Replay 继续读取原版提示词。Actor I/O、执行引用解析和 Replay 无损投影直接复用 v29.2。没有全局 monkeypatch，也没有改写旧版本实现或归档。

| 身份 | v29.4 |
| --- | --- |
| Method | `v29_4_campaign_v1` |
| Stage | `v29_4_stages_v1` |
| Runtime | `v29_4_light_runtime_v1` |
| Diagnosis Prompt | `v29_4_docvqa_diagnosis_v1` |
| Diagnosis Contract | `v29_4_diagnosis_direct_evidence_v1` |
| Preconditioner Prompt | `v29_4_docvqa_preconditioner_v1` |
| Preconditioner Contract | `v29_4_preconditioner_direct_evidence_v1` |
| Diagnosis/Preconditioner 输入视图 | `v29_4_shared_execution_text_v1` |

Editor、Replay、Gate、Memory 的原合同身份保留，Memory 持久化格式不变。跨版本 campaign 恢复由 Method/Stage/Prompt/Contract 配置身份拒绝，不能把 v29.2 响应静默当作 v29.4 使用。新版本不产生 Grouping 请求、结果或目录。

## 分支与恢复

| 分支 | 保留的行为 |
| --- | --- |
| Diagnosis no_change | 保留 Parent，推进轮次，不新增 Memory 轮记录 |
| Preconditioner 全部 WITHDRAW | 保留 Parent，推进轮次，不新增 Memory 轮记录 |
| Editor 全部空补丁 | 不执行 Candidate；记录 Effective Updates，gate_decision=null；提交 Memory |
| Editor 任一 patch=null | 语义停止，不执行 Candidate，不以重新采样绕过 |
| Candidate 没有 hard 转换 | 不分配 Replay 请求槽；继续 Gate 和 Memory；非空补丁 G=L=0、Defer，空补丁 gate_decision=null；Knowledge 为空 |
| Candidate 存在 hard 转换 | 正常 Replay → Gate → Memory |

已完成响应可直接恢复，重试计数不重置；Memory HEAD 先提交、游标落后一轮时，复用本轮已有结果完成发布。已发布历史轮次不重新执行，Memory 加载不重新打开历史 Actor 来源，保持当前 v29.2 的保障范围。

## 实验配置

配置为 [v29_4_docvqa_optimization160.json](../../../experiments/configs/v29_4_docvqa_optimization160.json)，基线为 `v29_2_docvqa_optimization160_references_v4.json`。初始实现仅删除 Grouping 配置及其预算；2026-11-04 按用户后续要求，将 Editor max_tokens 从 16,384 提高至 32,768，其余参数保持不变。当前实验同时包含删除 Grouping 和提升 Editor 预算两项变化，不再是严格的单因素对照。

| 模块 | max_tokens | timeout_seconds |
| --- | ---: | ---: |
| Diagnosis | 32768 | 300 |
| Preconditioner | 32768 | 300 |
| Editor | 32768 | 300 |
| Replay | 32768 | 300 |

初始 Skill、空 Memory、160 题及其顺序、10×15+10 的批次划分、Actor、评分、温度、推理设置、六次请求额度、重试间隔及输入容量均保持原值。CLI 仍区分 train 和 test，训练完成不自动运行 Test。

## 离线验收

入口：[run_v29_4_campaign.py](../../../scripts/runs/run_v29_4_campaign.py)。仅检查完整数据集配置、不会创建 campaign 或读取凭据：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_4_campaign.py train /tmp/v29_4_preflight --config experiments/configs/v29_4_docvqa_optimization160.json --validate-only
```

离线测试与配置验收入口：[verify_v29_4_campaign.py](../../../scripts/verification/verify_v29_4_campaign.py)。阻断网络和子进程，使用临时合成归档，覆盖新版本及 v29/v29.1/v29.2/v29.3 回归，并比较本次修改前冻结的 122 个基线文件哈希：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_4_campaign.py --output artifacts/verification/v29_4_implementation_20261104 --baseline artifacts/verification/v29_4_implementation_20261104/baseline.json
```

专项覆盖单条执行提案、完整批次与成功/反例交接、Group 来源拒绝、事实篡改检测、输出错误边界、四阶段调用、无 hard 转换仍提交 Updates、全部空补丁、语义停止、各发布边界恢复、请求预算保持、跨版本拒绝、Selected Skill 导出和 Test 隔离。

验收结果见 [validation.json](../../../artifacts/verification/v29_4_implementation_20261104/validation.json) 和 [unittest.log](../../../artifacts/verification/v29_4_implementation_20261104/unittest.log)。提示词差异见 [diagnosis.diff](diagnosis.diff)、[preconditioner.diff](preconditioner.diff)。离线结果仅验证合同与执行行为，不证明跨执行分析质量或最终任务分数提升。

2026-11-04 验收：616 项全部通过，其中 v29 110 项、v29.1 29 项、v29.2 332 项、v29.3 36 项、v29.4 109 项；无失败、错误或跳过。完整 160 题配置的 CLI 只读预检查通过，122 个基线文件哈希一致，无网络或子进程尝试，未启动真实训练或 Test。

## Editor 预算调整与重新训练

上述 616 项结果对应首次实现的 Editor 16,384 配置。用户随后明确要求停止并删除首次真实运行，将 Editor max_tokens 改为 32,768 后从头训练，成功后测试。已终止旧训练与监督进程，删除旧 campaign 和该次运行的监督脚本/日志目录；当时尚未开始 Test。方法源码、原始数据集和离线验收产物保留。

预算调整后，Binding/Evaluation 共 22 项相关测试全部通过，完整配置预检查通过；方法源码与首次验收哈希一致。新运行采用初始 Skill、空 Memory，不继承旧 Selected 或执行结果。训练并发 15、Test 并发 60，仍为 160 题/11 轮训练后执行 374 题 held-out Test。失败时停止，不自动重新启动。

新运行目录为 `experiments/campaigns/v29_4_docvqa160_editor32768_20261104_015530`；实时进度见 [status.json](../../../experiments/automations/v29_4_docvqa160_editor32768_20261104_015530/status.json)，配置与预算验证见 [preflight.json](../../../experiments/automations/v29_4_docvqa160_editor32768_20261104_015530/preflight.json)，删除和重新启动的记录见 [reset_receipt.json](../../../experiments/automations/v29_4_docvqa160_editor32768_20261104_015530/reset_receipt.json)。
