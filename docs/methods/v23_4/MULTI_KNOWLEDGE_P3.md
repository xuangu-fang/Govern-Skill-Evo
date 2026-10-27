# 多 Knowledge P3：契约贯通与模型视图适配

日期：2026-10-22。P3 完成技术链路适配，所有新格式入口须显式启用；生产默认仍为旧格式。P4 学习 Prompt、P5 整体验收和 P6 真实语义验证尚未完成。

## 贯通的路径

```text
load_memory(memory_contract=NEW)
  → Preconditioner 输入校验
  → Memory v3 投影与逐 Knowledge 证据
  → Adjustment 校验、引用可见性
  → 独立 Patch 应用与旧格式 Adjustment 适配
  → compile_effective_plan(memory_contract=NEW)
  → Effective Plan
  → Editor 交接时再次编译核验
```

每个校验/投影/适配/编译函数都显式接收并传递同一 `memory_contract`，不能只改变模型 User JSON。`run.json` 保存契约，重载据此重建整个过程。`expected_memory_contract` 可用于明确校验复用版本；即使 Memory 为空，运行归档也不能跨版本复用。

`memory_contract` 仍为程序参数及元数据，不进入模型的 Adjustment、Patch 或 Effective Plan。低层纯函数的空 Memory 对两种契约具有相同形状；它们不能凭空推断调用方的版本意图。因此通过调用参数贯通、编译边界测试及归档元数据共同保证版本一致，而不是声称空 JSON 自带版本。

## 具体改动

| 层 | 实现与边界 |
|---|---|
| `v23.preconditioner` | `preconditioner_input`、`compile_effective_plan` 增加默认旧值的契约参数；新契约不接受旧归档专用的 `memory=[]` 宽限 |
| `v23_3.memory_view` | `compact_memory`、`project_payload`、`project_messages` 按指定契约校验；通过 P2 的 `entry_evidence` 从所有 Knowledge 汇总引用；逐条绑定保留 |
| `v23_4.preconditioner/update_patch` | 构建输入、模型投影、理由引用、Patch 应用、共享编译器和重载全部传递契约；D/S/C 与 v2 输出保持原样 |
| `v23_4.replay_view` | 历史快照使用指定契约加载；各 archive 按其 own memory_contract 核验 payload/result，再核对实际编辑、执行、任务身份及哈希；当前 Pair 组织不变 |
| `v23.replay` | 共享完整事实构建函数接受契约，继续校验完整 payload；旧默认入口不切换 |
| `v23_4.replay` | build/validate/messages/run/load 贯通契约；新 run 保存版本、逐 Knowledge 校验输出；完整 input 与 model_input 分开保存；不自动提交 Memory |
| `v23.editor`、`v23_4.editor` | Editor 接口内部原本再次编译 Effective Plan，现显式传递已核验上游的契约；新 Editor run 保存并核对契约。Editor Prompt、模型输入、实际 Diff 算法不变 |

新读取与新视图不能用字符串/数组形状猜测版本；未知版本明确报错。旧 commit 未记录版本时按旧契约读取，不原地迁移。

## Memory v3 与历史 Pair

详细窗口仍为固定 ±2。所有历史动作与反馈、初始状态、结果、菜单池去重和无定位引用的处理方式不变。

多条 Knowledge 对同一执行的引用决定窗口并集，来源只投影一次；Entry 内仍各自保留完整 `text/evidence`，不添加聚合 evidence 字段，也不把文本拼成一条。历史 Pair 仍来自归档真实配对表，仅在两侧轨迹都已提供时加入；未提供侧不会被自动扩充。

对冻结 R05/R06 输入，离线检查要求：将旧 Memory 经 N 转成数组后，新旧 model_input 除 `memory.entries` 表示外完全相等；包括当前完整 runs、任务结果、历史 sources、窗口、command_pool、pairs 与 unpaired_runs。另验证旧 messages 仍可逐字重建。

## P3 格式模板与 P4 的区分

旧默认 Prompt 文件及旧共享说明保持字节不变。新格式分支使用：

- `replay_multi_knowledge_contract_prompt.md`：对当前旧主 Prompt 作结构适配，将 Entry 改为数组、证据移到每条 Knowledge，并明确完整数组替换。
- `multi_knowledge_view_prompt.md`：解释输入中的逐 Knowledge 绑定及证据边界；同时供 Replay 和 Preconditioner 追加。
- `replay_multi_knowledge_view_prompt.md`：保留既有 Pair 说明，仅澄清输出由版本化主 Prompt 定义。

P3 使用独立的技术装配版本 **`v23_4_replay_multi_knowledge_contract_v1`**。P1 为完整学习 Prompt 预留的 **`v23_4_replay_multi_knowledge_v1`** 仍留给 P4，避免把本轮格式适配误标为已完成学习设计。P4 应登记新的版本映射，保留 P3 版本的模板和重载能力，而不是覆盖 P3 文件。

Actor 执行背景、v3 和 Pair 说明仍由程序拼接。没有增加 Replay 调用、审核 Agent 或新的学习阶段。本轮未进行真实生成；结构模板不是已经通过语义验证的正式研究候选。

## 调用方式

```python
from src.skill_evolution.v23 import memory
from src.skill_evolution.v23_4 import preconditioner, editor, replay

NEW = memory.MULTI_KNOWLEDGE_CONTRACT
active = memory.load_memory(isolated_memory_directory, memory_contract=NEW)

pc_result = preconditioner.run_preconditioner(
    grouping_directory, diagnosis_directory, preconditioner_directory,
    generate=preconditioner_generate,
    memory=active, memory_contract=NEW,
)
preconditioner.load_preconditioner(
    preconditioner_directory, expected_memory_contract=NEW,
)
if pc_result['effective_plan'] is not None:
    editor.run_editor(preconditioner_directory, editor_directory, generate=editor_generate)

# 在获得真实、已验证的配对记录之后；本轮测试只使用离线合成记录。
bundle = replay.build_replay(
    editor_directory, parent_records, candidate_records,
    memory=active, memory_contract=NEW,
)
sources = replay.history_pair_sources(isolated_memory_directory, active, memory_contract=NEW)
saved = replay.run_replay(
    bundle, replay_directory, generate=replay_generate,
    memory_contract=NEW, history_sources=sources,
    max_input_chars=declared_budget,
)
# run_replay 不发布；确需隔离存储时由调用方显式提交。
memory.commit_memory(
    isolated_memory_directory, context_id='isolated_R1',
    context=bundle, result=saved['replay'], memory_contract=NEW,
)
```

`model_input`、`messages_for`、`normalize_update_patches` 等独立调用也必须传入契约，不根据 Entry 形状猜测。已存在旧 Replay/Preconditioner 运行目录不能用于新契约；应新建隔离目录。

## 验证与限制

[链路测试](../../../tests/skill_evolution/v23_4/test_multi_knowledge_chain.py) 使用注入式响应，检查 Replay→提交→重载→多轮 Pair→Preconditioner 调整→Patch→Effective Plan→Editor 的完整交接；同时检查错误契约、空 Memory、后续 Knowledge 窗口、逐条引用、Patch 原子失败、预算、异常输出和归档篡改。

[报告](../../../experiments/methods/v23_4/multi_knowledge_p3_001/REPORT.md) 记录回归结果、既有历史冻结失败及保护文件哈希。技术链路通过不代表模型学出的 Knowledge 准确，也不证明 Editor 真实生成时会忠实实现语义；这些仍需后续独立验证。
