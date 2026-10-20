# V23 Replay / Memory 实现与真实验证报告

日期：2026-10-18。状态：离线通过，四对真实执行通过配对核验，一次 Replay 输出 3 条有效 Memory，Archive／Active 与来源读取已提交并验证复用。未实现 Gate，未运行完整多轮自进化。

## 1. 实现及范围

| 文件 | 作用 |
|---|---|
| [memory.py](../../../../../src/skill_evolution/v23/memory.py) | 三字段提案校验、历史引用解析、不可变提交档案、原子 Active 索引、完整执行来源装配、同结果幂等提交 |
| [replay.py](../../../../../src/skill_evolution/v23/replay.py) | 复用 facts.py 构造配对输入、P/Q 独立身份、菜单共享、Diff 与 Candidate 核验、单次调用、失败保存及严格复用 |
| [replay_prompt.md](../../../../../src/skill_evolution/v23/replay_prompt.md) | 用户指定的完整英文 Prompt；无 u1/u2/u3 特殊补丁 |
| [preconditioner.py](../../../../../src/skill_evolution/v23/preconditioner.py) | 新运行使用正式 Memory 对象，允许真实 M ID 作为 Adjustment 依据，保持确定性编译；旧无历史档案使用已冻结旧模板只读核验 |
| [preconditioner_prompt.md](../../../../../src/skill_evolution/v23/preconditioner_prompt.md) | 只更新历史响应章节，明确 entries／sources、条件适用性、可修订性及合法 Keep |
| [test_replay_memory.py](../../../../../tests/skill_evolution/v23/test_replay_memory.py) | 新增、修订、合并、崩溃恢复、原子性、来源、失败保留、零调用复用、真实旧档案及非空 Memory 交接测试 |
| [test_preconditioner.py](../../../../../tests/skill_evolution/v23/test_preconditioner.py) | 将新请求的空 Memory 预期改为对象；原有非法引用与编译契约继续测试 |

Grouping、Diagnosis、Editor、facts.py、ALFWorld Adapter 的算法和执行代码未修改。新调用前的源码快照在 [config/source](../config/source/)。

Replay 模型输入严格为 `parent / diff / plan / command_sets / runs / pairs / memory`；Plan 读取视图不带 basis。模型只输出 `entries: [{revises, knowledge, evidence}]`。完整 Candidate、原始 Plan、Adjustments、Grouping 和来源审计仍在程序档案中。

## 2. 离线验证

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

运行前结果：**432 passed, 19 subtests passed**，无失败或跳过。真实运行后新增两项只读实际产物交接测试，最终为 **434 passed, 19 subtests passed**，见 [final_tests.txt](../../../../../artifacts/methods/v23/v23_replay_memory_001/final_tests.txt)。日志见 [offline_tests.txt](../../../../../artifacts/methods/v23/v23_replay_memory_001/offline_tests.txt)。

已测试空输出、新增、单条修订、多条合并、重复修订／非法来源拒绝、旧档案只读、完整历史执行展开、菜单缺失拒绝、断点恢复和幂等性。提交被模拟中断于 Active 切换前时，读者仍看到旧快照；恢复相同输入提交只产生一次 M ID。真实实验只验证首次新增，跨轮自然语言认识修订尚未真实验证。

## 3. 冻结对象及配对核验

Parent 复用四条历史轨迹，共 93 步，未新增 Parent 执行。Candidate 来自 `v23_editor_recovery_001/live`，完整文本仍为原来的 23 行，SHA256 为 `3f232fcbbe18fc7dba3b489ea161bc67440fde776d710fbb4a35b21ffd5e51a6`，未修改。

新增 Candidate 执行恰好四条，共 133 步；独立 Q 引用与 P 引用通过任务身份显式配对。Actor 使用原有 `run_task_skill` 入口、deepseek-flash、temperature=1、thinking enabled、reasoning_effort=medium、stream=false、每请求 16,384 输出 Token、300 秒超时、环境 seed=42、每任务 50 步。实际服务返回模型均为 deepseek-flash。

四对的任务、游戏文件及清单内容、真实初始观察和原始动作菜单、协议、模型路由、预算及依赖版本一致。Parent 的用途标签是旧开发入口的 development，Candidate 为现有 train/learning；这不改变 Actor 提示词或环境行为。源码哈希差异经 [implementation_review.json](../config/implementation_review.json) 中完整 Diff 核查：用途访问标记、入口路径、源码记录，以及等价 Prompt 渲染提取；真实每步 Prompt 仍由 facts.py 精确核验。没有把文件哈希不同直接视为执行协议相同。

[配对审计](../../../../../artifacts/methods/v23/v23_replay_memory_001/pair_audit.json) 保留双方身份、Skill、终止原因、步骤菜单来源和源码核对。Parent 与 Candidate 的中间状态不强行按步号对齐。相同的苹果轨迹仍为两次独立执行。

| 任务 | Parent 结果 / 步数 | Candidate 结果 / 步数 |
|---|---|---|
| train:0012 | success / 7 | success / 7 |
| train:0013 | step_limit / 50 | step_limit / 50 |
| train:0014 | success / 24 | step_limit / 50 |
| train:0015 | success / 12 | success / 26 |

没有技术中断，两个 step_limit 不是技术错误。描述性成功数从 3/4 变为 2/4，不能据此估计稳定效果或单条编辑因果效应。

完整动作与观察抄录见 [paired_evidence.md](../results/paired_evidence.md)。关键行为：

- P1／Q1 完全相同，7 步完成；均先开冰箱再取苹果。
- P2／Q2 均 50 步未找到目标。Q2 扩展到 shelf 2、cabinet 4/5，但仍反复访问已有位置。
- P3:19 发现浴盆中的目标，P3:24 完成；Q3 在初始菜单已提供浴盆机会的情况下，全程未到浴盆，50 步仍在货架、水槽、推车之间循环。
- Q4 在柜子搜索上花费更多动作，26 步成功，而 P4 是 12 步。P4:5 与 Q4:20 都发出菜单中不存在的 stoveburner 3，均返回 Nothing happens；不能把额外合法动作文字当作已产生可靠约束。

## 4. 唯一一次 Replay 输出

实际输出全文如下，未修补或重新采样；另存于 [replay.json](../results/replay.json)。

```json
{
  "entries": [
    {
      "revises": [],
      "knowledge": "The Candidate introduced a new Skill (the Parent had no Skill) whose search section instructed a deterministic forward sweep, avoidance of revisiting checked locations, and expansion across distinct receptacle classes when a target was not initially visible. Adherence was mixed. In a paired bathroom task to clean a dishsponge and put it on a shelf, the no-Skill Parent eventually reached the bathtubbasin, took the dishsponge, cleaned it at the sinkbasin, and succeeded in 24 steps; the Candidate never visited the bathtubbasin despite it being listed from the start, instead cycling among shelf 1-4, sinkbasin, and cart until the 50-step limit. In a paired kitchen dishsponge search, both Parent and Candidate hit the step limit, but the Candidate did cover a few additional sites such as shelf 2 and cabinets 4-5 while still repeatedly returning to sinkbasin, countertop 1, and cabinets 1-3 and never inspecting several available receptacle classes or cabinets 7-13. In a paired kettle task, the Candidate instead appeared to perform a long cabinet sweep (cabinets 1-7 and 9) before resuming the stoveburners; it still found and cleaned the kettle and placed it in cabinet 1, but took 26 steps versus the Parent's 12. The evidence supports a conditional understanding: the added search guidance did not reliably prevent repetitive search or ensure coverage of a distinct unchecked receptacle class, and in a scene with many cabinets it could be associated with a costly class sweep before returning to a plausible surface. Single paired instances and the bundled edit leave causal attribution uncertain.",
      "evidence": [
        "diff",
        "P3:19",
        "P3:20",
        "P3:24",
        "Q3:1",
        "Q3:15",
        "Q3:18",
        "Q3:50",
        "P2:50",
        "Q2:13",
        "Q2:24",
        "Q2:26",
        "Q2:50",
        "P4:12",
        "Q4:3",
        "Q4:16",
        "Q4:21",
        "Q4:26"
      ]
    },
    {
      "revises": [],
      "knowledge": "The Candidate's new Skill also included an admissible-action section instructing it to select only actions present in the current admissible list and to choose an available alternative when an intended action is absent. In the paired kettle task, both conditions nevertheless attempted 'go to stoveburner 3' when that action was absent from the current admissible set: the Parent did so at step 5 and the Candidate at step 20, immediately after being at stoveburner 2 and before both corrected to the available stoveburner 4. Each attempt produced 'Nothing happens' and consumed one step, with action_in_admissible_commands recorded as false. The Candidate then recovered and completed the task successfully. This shows that the admissibility guidance did not prevent the same numeric-sweep continuation error in this instance, although it does not establish that the guidance caused any other behavior.",
      "evidence": [
        "diff",
        "P4:5",
        "P4:6",
        "Q4:20",
        "Q4:21",
        "Q4:26"
      ]
    },
    {
      "revises": [],
      "knowledge": "The Candidate's new Skill added explicit clean-and-place dependency ordering: acquire the matching target, open a closed source container, clean the held target at a cleaning fixture, open a closed destination if needed, then place the target. In the straightforward paired clean-apple task, the no-Skill Parent and Candidate executed exactly the same seven-step successful sequence: open the fridge, take apple 2, go to the sinkbasin, clean it, go to the diningtable, and move it there. In the paired kettle task, the Candidate eventually followed the same acquire-clean-place order and succeeded; it had already opened the destination cabinet during its earlier search, so it did not reopen it immediately before placement. These observations show the added dependency guidance was compatible with the successful workflow and did not introduce a regression in these tasks, but they do not show improvement over the no-Skill Parent, which already performed the same order.",
      "evidence": [
        "diff",
        "P1:1",
        "P1:7",
        "Q1:1",
        "Q1:7",
        "P4:8",
        "P4:9",
        "P4:12",
        "Q4:4",
        "Q4:22",
        "Q4:24",
        "Q4:26"
      ]
    }
  ]
}
```

## 5. 逐条语义核查

| 条目 | 实际支持 | 边界与偏差 |
|---|---|---|
| M1 搜索指导的混合响应 | 浴盆未访问、重复循环、额外柜子／货架覆盖以及 kettle 的长柜子搜索均能在原始执行中核对；浴盆从 Q3:1 的行动前菜单就可用 | 这是多个搜索要求和其他规则共同加入后的观察。不能分离单条规则的效应；“更可信的搜索表面”属于解释。涉及同批特定环境，尚未验证跨任务适用性 |
| M2 合法动作约束未阻止相同错误 | P4:5 和 Q4:20 的 action_in_admissible_commands 均为 false，之后都改去 stoveburner 4；事实与菜单吻合 | 基础协议本已要求选合法动作。只说明本例仍发生相同错误，不证明新增指导无任何价值，也不证明它造成其他变化 |
| M3 清洁依赖行为保持 | P1／Q1 实际七步完全相同；Q4:22 取物、24 清洁、26 放置，柜子已在 Q4:4 打开 | 文字列举“七步流程”省略初始 go to fridge，属于列举不完整；概述“先 acquire 再 open source”容易沿用 Candidate 编号歧义，但实际两侧都先开再取。“没有退化”只适用于这里的清洁／放置子流程，不能扩展到 Q4 全任务效率（12→26 步） |

三条都形成编辑与行为关系，而非下一轮强制 Skill 指令；M1 跨多个任务，不是程序按 Update 强制分配。没有把未发生的清洁顺序错误写成已观察退化，没有把全局搜索历史归给 Actor。仍存在实例细节较多、M3 表述精度与作用范围需要谨慎解释的问题；原输出保持原样。

## 6. Memory 提交与读取

一次真实提交生成 M1、M2、M3，context_id 为 `v23_replay_memory_001_R1`。实际 [Active 索引](../../../../../artifacts/methods/v23/v23_replay_memory_001/memory/active.json) 包含 active_ids 和已提交上下文列表；后者用于断点恢复与幂等提交，不是模型输出字段。

Archive 使用不可变的按轮提交文件，内含正式五字段 MemoryEntry、本轮完整来源和原始提案。先保存提交文件，再原子切换 Active 索引；未被索引提交的中断文件不进入有效读取，必须以相同请求恢复后才能提交另一轮。没有原地改写旧条目。

[Memory 读取视图](../results/memory_view.json) 含 3 条 Active Entry 和 9 个共享来源：1 份实际编辑／背景及 8 条完整历史执行。步骤级引用展开完整执行和它使用的菜单；同一执行跨条目只展开一次。程序给当前证据加实验轮次前缀，未自动继承旧证据。

真实 Replay 结果再读取以及同轮 Memory 再提交均已验证：新增模型调用 0、新增重复条目 0。该结果可直接输入 Preconditioner。历史修订／合并目前是离线验证，不能声称真实持续修订已经完成。

## 7. 调用、消耗和失败情况

| 工作 | 次数 | 输入 Token | 输出 Token（含推理） | 推理 Token | 总 Token |
|---|---:|---:|---:|---:|---:|
| Candidate Actor | 133 请求 / 4 episode | 115243 | 41637 | 32040 | 156880 |
| Replay 学习 | 1 | 47119 | 10403 | 9496 | 57522 |

Replay 输入 166,609 字符，耗时 51.844 秒。四个 Candidate 并行执行，最长约 140.8 秒；原始记录含逐请求时间和 usage。Actor 本次 133 次传输，无状态码重试；Replay 无重试。完整 HTTP 响应和推理内容在原始产物中。API 返回 Token 明细但无货币账单金额，本报告不虚构费用。

冻结上限：4 个 Candidate、1 次 Replay、两侧各 1 次 Preconditioner；每学习调用 max_tokens=16,384、timeout=300、max_input_chars=300,000，脚本另查 UTF-8 输入字节上限 400,000。未截断任何轨迹或 Memory。预算与语义检查标准见 [plan.json](../config/plan.json)。

冻结脚本首次离线准备时遇到旧 run_task_upstream.py 位于另一快照目录，修正来源路径并核对原哈希后才冻结；此准备错误未发出任何模型请求或环境执行。真实环境与 Replay 无技术失败。

## 8. 下一步边界

已验证首次真实响应学习和持久化交接；有 Memory 的 Preconditioner 结果单独见 [报告 B](../../v23_preconditioner_with_memory_001/reports/REPORT.md)。本次不执行新 Effective Plan 的 Editor／Candidate，不实现 Gate。跨轮修订质量、独立任务泛化、真实行为收益和完整状态推进仍未验证。
