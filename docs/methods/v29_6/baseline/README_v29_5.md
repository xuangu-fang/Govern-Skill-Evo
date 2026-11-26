# v29.5：完整修正策略的提出、调整与实现

## 基线与改动范围

直接基线是 v29.4 的 Editor 32,768 版本，对应已完成实验 `v29_4_docvqa160_editor32768_20261104_015530`。实现前核对该实验记录的 46 个源码与提示词哈希均与当前文件一致，实验配置与当前 v29.4 配置逐字节一致。

v29.5 保留无 Grouping 的四阶段流程，仅接入第三步确认的 11 处提示词替换。Diagnosis 明确问题与既有指导的关系，提出完整修正；Preconditioner 在既有 Original 问题和 ID 边界内评估、调整修正策略；Editor 依照 Effective Update 实现必要的新增、修订、整合、替换或删除。

| 修订 | 具体变化 |
| --- | --- |
| D1 | 检查问题与 Parent/base 指导的关系，选择有依据的修正方式，并写入 Update text |
| D2 | 按共同决策问题与修正方向组织 Updates，保留必要的跨位置协调 |
| D3 | 明确受影响的旧指导、所需处理及应保留的有效分支 |
| D4 | 用清晰段落或列表表达完整行为，取消每行独立要求的偏好 |
| D5 | 修正需要修改旧指导时明确提出；合理新增仍然允许 |
| P1 | 同时评估行为、修正策略和旧指导处理，可在 Original 范围内调整 |
| P2 | Coordination 覆盖应改变或停止适用的旧指导，不合并或新增 Update IDs |
| P3 | KEEP 认可整个修正策略，局部需要修正时完整 REPLACE |
| P4 | REPLACE 将完整修正及必要删除写入 text，不依赖 reason 向 Editor 传递 |
| E1 | Editor 决定具体措辞、位置和 patch，忠实实现 Effective 策略 |
| E2 | 在受影响指导中清晰表达动作、条件、例外和优先关系，不重组整个 Skill |

实际提示词：[Diagnosis](../../../src/skill_evolution/v29_5/prompts/diagnosis.md)、[Preconditioner](../../../src/skill_evolution/v29_5/prompts/preconditioner.md)、[Editor](../../../src/skill_evolution/v29_5/prompts/editor.md)。逐项差异：[diagnosis.diff](diagnosis.diff)、[preconditioner.diff](preconditioner.diff)、[editor.diff](editor.diff)。Editor 的直接提示词基线是 v29.4 实际使用的 v29.2 文件；旧文件未修改。

没有引入 Workflow、Error Avoidance、固定章节、规则数量或长度目标，也没有增加测试集专项指导、新字段、规则 ID、额外评审阶段或自动压缩流程。

## 版本与接口

独立模块位于 `src/skill_evolution/v29_5`，配置为 `experiments/configs/v29_5_docvqa_optimization160.json`，运行入口为 `scripts/runs/run_v29_5_campaign.py`。

- 方法、阶段、运行时和最终测试归档使用 v29.5 标识；三份修改后的提示词使用独立版本标识。
- 结构契约、无损执行输入视图、Replay 提示词和 Memory 格式继续保留原标识，避免把未修改的格式标记成新协议。
- 各阶段绑定 v29.5 的上游模块。执行事实与视图代码保持基线实现，Actor I/O、引用解析和 Replay 视图继续复用既有资源。
- Diagnosis 仍输出 `decision/reason/plan`，Update 仍为 `id/text/basis`。Preconditioner 仍完整 KEEP/REPLACE/WITHDRAW，编译保持 Goal、顺序、IDs 和 basis。
- Editor 只接收 Parent 和 Effective Plan 的 `goal/updates[id,text]`。所有 patch 仍定位于原始 Parent；保留多 hunk、逐 Update 映射、冲突校验、空 patch 和 null 的既有契约。
- 仍允许单条执行支持合理提案，不要求每条执行产生 Update，不要求独立因果证明。
- no_change、全部撤回、无 hard 转换时跳过 Replay、Gate、Memory 提交、请求预算和恢复分支均保持基线实现。
- v29.4 与 v29.5 配置及 campaign 不允许交叉恢复。

## 固定实验设置

初始 Skill、空 Memory、训练 160 题及顺序、10×15+10 批次、测试 374 题、Actor 参数、评分、并发和重试策略保持 v29.4。训练并发 15，测试并发 60。Actor 与 Diagnosis、Preconditioner、Editor、Replay 的 max_tokens 均为 32,768，超时 300 秒；原有六次请求预算不变。

CLI 仍区分 train 和 test。完成训练本身不会自动启动测试。以下命令仅作为运行说明，本次实现未执行真实训练或测试集评测。

从项目根目录运行配置预检查，不读取凭据或创建 campaign：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_5_campaign.py train /tmp/v29_5_preflight --config experiments/configs/v29_5_docvqa_optimization160.json --validate-only
```

独立训练命令（campaign 路径必须是新的目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_5_campaign.py train experiments/campaigns/v29_5_docvqa160_run01 --config experiments/configs/v29_5_docvqa_optimization160.json
```

训练完成后，测试命令：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/runs/run_v29_5_campaign.py test experiments/campaigns/v29_5_docvqa160_run01 --output experiments/evaluations/v29_5_docvqa374_run01
```

## 离线验收

验收入口：[verify_v29_5_campaign.py](../../../scripts/verification/verify_v29_5_campaign.py)。阻断网络及子进程，仅用临时合成执行归档检查流程；真实数据仅用于配置和 CLI 只读预检查。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_5_campaign.py --output artifacts/verification/v29_5_implementation_20261104 --baseline artifacts/verification/v29_5_implementation_20261104/baseline.json
```

覆盖 v29 至 v29.5 回归、三份本地提示词实际加载、配置冻结、源码算法一致、跨版本拒绝、完整修正文本交接、单 Update 多位置修订与删除，以及既有 no_change、撤回、空 patch、null、Replay 跳过、Gate、Memory 原子提交、恢复和预算边界。

报告：[validation.json](../../../artifacts/verification/v29_5_implementation_20261104/validation.json)。详细日志：[unittest.log](../../../artifacts/verification/v29_5_implementation_20261104/unittest.log)。基线保护清单：[baseline.json](../../../artifacts/verification/v29_5_implementation_20261104/baseline.json)。

2026-11-04 验收结果：729 项全部通过，无失败、错误或跳过。其中 v29 110 项、v29.1 29 项、v29.2 332 项、v29.3 36 项、v29.4 109 项、v29.5 113 项。完整数据集配置及 CLI 只读预检查通过；183 个受保护基线文件哈希未变；无网络或子进程尝试，未启动真实训练或测试集评测。

这些检查验证接口、接入和执行行为。合成测试中的决策与 patch 为人工构造，不能证明模型会正确选择修正方式，也不能证明规则质量或测试成功率已提高；后者需要后续独立训练与测试验证。
