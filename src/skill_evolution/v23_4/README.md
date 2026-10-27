# Govern V23.4

## 当前集成状态（2026-10-22）

V23.4 独立 Campaign 与最终 Test 入口已接通并完成离线验收；真实 57 条优化 / 134 条 Test 尚未启动。正式配置显式采用 P4 Replay、多 Knowledge Memory 和 Memory v3，模型为内部代理 `deepseek-v4.1-flash`。运行步骤、冻结配置、发布规则和验收边界见 [Benchmark 运行说明](../../../docs/methods/v23_4/BENCHMARK_RUNBOOK.md)。

下方为分阶段实现记录，其中“尚未调用模型”等描述对应各阶段当时状态，不代表当前实验进度。

P4 候选学习 Prompt 已登记为 `v23_4_replay_multi_knowledge_v1`，使用新 Memory 契约时仍需显式传入 `prompt_version` 才会启用。旧默认和 P3 模板保留；R05/R06 仅完成待发送消息冻结，未调用模型。用法与验收见 [P4 说明](../../../docs/methods/v23_4/MULTI_KNOWLEDGE_P4.md)。

多 Knowledge P2 存储与 P3 链路适配已完成，须显式选择 `memory_contract="entries_sources_multi_knowledge_v1"`。下列默认示例仍采用旧格式；新格式贯通 Replay、Memory v3、历史 Pair、Preconditioner 编译和 Editor 交接。接口见 [P3 说明](../../../docs/methods/v23_4/MULTI_KNOWLEDGE_P3.md)。新契约的默认仍是 P3 结构适配模板；P4 候选须显式选择，尚未运行真实模型。

更新日期：2026-10-22（Asia/Shanghai）。状态：已补充 Replay 输入视图设计、实现与离线验证；新视图尚未运行真实模型，未注册默认方法。

| 文件 | 职责 |
|---|---|
| [preconditioner_prompt.md](preconditioner_prompt.md) | 历史响应驱动的 D/S/C 决策与扁平 v2 输出协议 |
| [update_patch.py](update_patch.py) | v2 结构、覆盖、引用、Keep/to 校验；冻结 Original 上严格应用 Patch；派生旧编译器对象并编译 |
| [preconditioner.py](preconditioner.py) | 注入式单次生成、模型视图装配、原始/派生归档、版本化重载与上游核验 |
| [editor.py](editor.py) | V23.4 上游加载边界；复用 V23 Editor 输入、Prompt、校验与 Patch 逻辑 |
| [diagnosis.py](diagnosis.py)、[diagnosis_prompt.md](diagnosis_prompt.md) | 原 Schema 下强化行为粒度与关键边界证据，独立 Prompt 版本归档 |
| [replay.py](replay.py)、[replay_prompt.md](replay_prompt.md) | 实际编辑—条件—响应知识微调，复用配对与 Memory 校验，复核 V23.4 Editor 上游 |
| [replay_view.py](replay_view.py)、[replay_view_prompt.md](replay_view_prompt.md) | Replay 确定性模型视图：当前 Pair 相邻与结果统计、原 Memory v3、真实历史 Pair 索引；不增加学习调用 |

设计依据：[输入输出契约](../../../docs/methods/v23_4/INPUT_OUTPUT_CONTRACT.md)、[D/S/C 决策规则](../../../docs/methods/v23_4/DSC_DECISION_RULES.md)。契约仍为 `v23_4_transformations_v2`，模型只输出 adjustments/checks，每项为 target/focus/change/reason/to。

## 调用入口

上游采用 [V23 Grouping](../v23/grouping.py)，新请求默认使用本目录的 V23.4 Diagnosis。调用 `run_diagnosis(grouping_directory, diagnosis_directory, generate=...)` 生成新版归档；若显式使用 V23.3 Diagnosis，在 `run_preconditioner` 传入 `diagnosis_version="v23_3"`。第三步没有 diagnosis_version 字段的既有 v2 归档固定按 V23.3 读取，不试探版本或迁移内容；新归档记录实际版本，即使两个版本生成相同 Plan 也拒绝跨版本复用。

`generate(messages, directory)` 由调用方注入，返回至少含 `content` 和 `finish_reason` 的响应；正常结束要求 `finish_reason == "stop"`。通过生成器的 `call_config` 属性或显式参数记录配置，两者同时存在时必须一致。

```python
from src.skill_evolution.v23_4.preconditioner import run_preconditioner
from src.skill_evolution.v23_4.editor import run_editor
from src.skill_evolution.v23_4.diagnosis import run_diagnosis

diagnosed = run_diagnosis(grouping_directory, diagnosis_directory,
                         generate=diagnosis_generate)
if diagnosed["diagnosis"]["decision"] == "revise":
    saved = run_preconditioner(
        grouping_directory, diagnosis_directory, preconditioner_directory,
        generate=preconditioner_generate, memory=active_memory,
    )
    if saved["effective_plan"] is not None:
        edited = run_editor(preconditioner_directory, editor_directory,
                            generate=editor_generate)
```

这是装配示意，不会自行创建真实生成器或调用 Actor。省略 memory 使用合法空 Memory。默认 `memory_view="memory_evidence_view_v3"`，可显式选择既有 `entries_sources` 完整视图；归档重用要求视图一致。`max_input_chars` 默认 100000，不自动截断证据。

使用 [V23 render_prompt](../v23/prompts.py) 注入真实执行背景，再复用 [Memory v3 投影](../v23_3/memory_view.py) 追加格式说明并投影六字段输入。Editor 模型仍只接收 Parent、Effective Plan 与既有执行背景。

仅需离线适配时使用 `normalize_update_patches(raw_output, full_payload, memory_view=...)`，返回 `(legacy_result, effective_plan)`，不修改输入。全部 Keep 仍生成 Original Plan；只有合法全部撤回返回 null。同 ID 修改支持方向重构、扩大许可与协调，不设置修改比例限制。

已有真实配对执行记录时，可用本目录 `replay.build_replay(editor_directory, parent_records, candidate_records, memory=...)` 构建完整输入。2026-10-22 新增的 Replay 输入视图默认采用 `v23_4_replay_pairs_memory_v3_v1`：当前轨迹按真实 Pair 交错排列，pairs 中记录 task_id 和双方 status/success/steps；历史 Memory 复用 v3，再增加归档来源确认的 Pair 索引。Replay 仍输出 `entries[{revises, knowledge, evidence}]`，只调用一次模型。

```python
from src.skill_evolution.v23 import memory
from src.skill_evolution.v23_4 import replay

active = memory.load_memory(memory_directory)
bundle = replay.build_replay(editor_directory, parent_records, candidate_records, memory=active)
sources = replay.history_pair_sources(memory_directory, active)
saved = replay.run_replay(bundle, replay_directory, generate=replay_generate,
                          history_sources=sources, max_input_chars=declared_budget)
```

`history_pair_sources` 核对 Memory 快照并冻结各历史 archive 路径/SHA256；每次视图重建检查来源与完整事实一致。非空 Memory 必须明确提供全部 context 的来源，确实不可用的来源可显式为 null；单侧或未知配对只进入 memory.unpaired_runs，不增加轨迹或猜测 Pair。空 Memory 不需要额外参数。`replay.model_input(bundle, history_sources=...)` 可单独离线投影；它不替代生产 `validate_bundle` 的 Editor 血缘核查。

完整 input.json 与 Memory 存储格式保持不变，新运行另存 model_input.json 和 history_pair_sources.json，并记录 input_view。旧归档缺少 input_view 时按原 `entries_sources` 视图读取；显式选择旧视图可用于复核，运行目录不能跨视图复用。基础 Replay Prompt 不改写，仅新视图追加现有 v3 和 Pair 格式说明。默认 400000 字符预算不变，超过预算明确失败，不裁剪当前事实。

由现有 `v23.memory.commit_memory` / `load_memory` 显式提交和加载，提交使用完整 bundle。运行 Replay 不自动写入 Active Memory，也不决定 Candidate 是否接纳。新视图契约见 [REPLAY_INPUT_VIEW.md](../../../docs/methods/v23_4/REPLAY_INPUT_VIEW.md)，本次合成测试与 R05/R06 离线投影见[报告](../../../experiments/methods/v23_4/replay_input_view_001/REPORT.md)；尚未执行新视图的真实 Replay。

Diagnosis 与 Replay 分别记录 `prompt_version="v23_4_diagnosis_v1"` 和 `"v23_4_replay_v1"`。旧 Prompt、Memory 存储格式和 v3 投影保持原样；具体变更与逐案例检查见[第四步离线报告](../../../docs/methods/v23_4/OFFLINE_REVIEW.md)。

## 归档与失败

| 文件 / 返回字段 | 内容 |
|---|---|
| `input.json` | 包含完整 Memory 的上游快照 |
| `model_input.json`、`messages.json`、`prompt.md` | 模型实际看到的视图与系统消息 |
| `response.json`、`raw_output.txt`、`parsed.json` | 原始响应与 v2 输出；Keep 理由保留于此 |
| `preconditioner.json` | 程序派生的旧编译器兼容对象，非模型原始输出 |
| `effective_plan.json` | 所有 Patch 与 Checks 通过后的完整 Plan；合法全部撤回为 null |
| `run.json`、`validation.json` | 契约版本、视图、调用配置、上游路径、状态与错误 |
| 返回 `raw_preconditioner` / `preconditioner` / `effective_plan` | 分别对应原始 v2 输出、内部兼容对象和最终 Plan |

`load_preconditioner` 重新读取上游、重建视图和 Prompt、解析原始响应、校验并应用全部 Patch，再与派生产物比较。`load_editor` 同样重新验证 V23.4 上游。旧版本加载器不能用于读取新归档。

结构、引用、Patch 或调用失败记录为 invalid 并抛出异常，不转成 Keep 或成功的 null；已存在目录只允许校验后复用，不隐式重试。目录内单个文件的存在不代表成功，须通过版本化加载器的整体检查。

## 验证与边界

[V23.4 离线测试](../../../tests/skill_evolution/v23_4/) 使用合成事实、合成 Memory 与注入式响应，不依赖历史实验产物。覆盖严格契约、Keep 理由引用、独立 Patch 原子编译、Checks、归档篡改、配置/版本拒绝重用，以及 Editor 交接。

2026-10-21：86 项 V23.4 测试与 172 项 V23 编译器/Editor 回归共 258 项通过；排除 2 项依赖历史归档的读取测试。命令：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/v23_4 tests/skill_evolution/v23/test_editor.py \
  tests/skill_evolution/v23/test_preconditioner.py \
  -k 'not real_handoff_and_legacy_readonly and not real_archives_handoff_readonly'
```

引用检查验证实际模型视图中的身份；trace 可见不等于详细状态可见。程序不能证明历史支持结论、Keep 回应了反例、D/S/C 实际决定了变换，或 Patch 与 change 双向语义一致；测试中明确保留结构通过但语义不忠实的反例。

第四步补充：共 **341 项通过、5 项历史归档测试排除**，其中 122 项 V23.4 测试与 219 项 V23 回归。覆盖八个完整合成案例、证据变化、三类未改善响应、版本交接、Replay 到 Memory 提交/修订及下一次 Preconditioner 输入；完整命令见[离线报告](../../../docs/methods/v23_4/OFFLINE_REVIEW.md)。上方 258 项记录为第三步基线。

未改变第二步 Preconditioner Prompt、v2 契约或 D/S/C 方法。旧 Replay 仅提取现有装配函数供版本化加载器复用，默认行为不变。未启动真实模型、Actor、Gate 或消融，未接入默认流程；接口可运行不代表研究收益已经成立。
