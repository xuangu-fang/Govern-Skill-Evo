# V23.4 第四步：Diagnosis / Memory 协同与离线检查

日期：2026-10-21（Asia/Shanghai）。范围：Prompt 微调、版本化交接与合成材料检查；不是参数训练、真实模型遵循率评估或 Actor 收益实验。

## 1 实际调整

| 部分 | 改动 | 保持的边界 |
|---|---|---|
| [Diagnosis Prompt](../../../src/skill_evolution/v23_4/diagnosis_prompt.md) | 按连贯行为问题组织 Update，保留相关触发/依赖；basis 包含决定重要边界的成功或反例执行 | 沿用 Goal/策略分离、多行字符串、当前事实输入和原 Schema；不接入 Memory、不提前生成 D/S/C |
| [Replay Prompt](../../../src/skill_evolution/v23_4/replay_prompt.md) | 明确实际行为指导的前后变化；区分未触发/未遵守/遵守后未改善；具体保留正负响应；引用支撑条件与响应的步骤 | knowledge 仍是一段可修订理解，输出仍为 revises/knowledge/evidence；不生成未来更新指令或 D/S/C 标签 |
| Memory 存储与投影 | 复用现有不可变提交、Active 修订和 Memory v3 投影 | 不增加字段、检索器、摘要器或额外模型调用；不改变 ±2 窗口与完整 trace |
| 运行边界 | 新增 V23.4 Diagnosis/Replay Prompt 版本归档；Preconditioner 明确选择 Diagnosis 版本；Replay 复核 Editor 上游 | Preconditioner 的 v2 契约、Prompt 和 D/S/C 方法不变，旧 Prompt 不改写 |

现有 Diagnosis 已明确“Goal 不绑定未验证实现”和“完整多行行为要求”，所以本步未重复添加相关段落。现有 Replay 已有联合归因、配对比较和保留历史正负观察规则，本步只强化容易丢失的信息。

唯一的旧生产文件改动位于 [V23 Replay](../../../src/skill_evolution/v23/replay.py)：把加载 Editor 之后的原有配对/事实装配原样提取为 `build_replay_from_editor`。V23 仍使用旧加载器；V23.4 先用自己的加载器验证链路，再复用同一装配函数，不复制配对算法或临时替换全局变量。

## 2 完整合成材料与逐案例走查

[offline_cases.py](../../../tests/skill_evolution/v23_4/offline_cases.py) 中的 `cases()` 构造八份完整材料，每份包含六字段 Preconditioner 输入、历史 Parent/实际 Diff、显式配对的合成执行、Replay 输入及示例 Memory 输出，以及一份可接受的 Adjustment 示例。案例 ID 和审查说明只存在于测试外壳，不进入模型业务 JSON。

所有动作、状态、反馈、知识和输出都是本次人为构造的离线材料，不是采集到的真实结果。示例输出是可行表达的见证，不是唯一正确答案。程序只核对数据/引用/Patch；下表是逐项阅读具体材料后形成的语义走查结论，没有自动审核 Agent。

| 案例 | 核对到的具体依据 | 示例决策与改善作用 | 走查不接受的推断 |
|---|---|---|---|
| A1 条件化重试 | `H_A1/Q1:2` 的锁未变且重复失败；`H_A1/Q2:2` 在可见解锁后打开成功 | S 限定无变化重复，同时允许修复后恢复推进；新条件规则未验证 | 永久禁止全部重试，或声称任意固定重试次数最优 |
| A2 方向重构 | 实际 Diff 加入全局回访禁止；第一组减少无信息重复，第二组 Parent 完成交付而 Candidate 未返回已知目的地 | D/S 转向抑制无信息重复，保留可见任务需要的返回 | 只堆任务例外；Patch 偷加“查完所有类别才能结束” |
| A3 扩大许可 | A 不可用且 B 明示提供所需精确信息；`H_A3/Q1:1` 获取到信息 | S 解除 A 的独占条件，同时保留替代信息适用性检查 | 将许可加强为永远优先 B，或假设所有来源可互换 |
| A4 协调 | 实际文本同时包含放弃和修复后重试；`H_A4/Q1:2` 显示修复后仍未尝试 | 分别调整 u1 的当前就绪检查、u2 的有条件放弃，两项同时应用 | 只改 u1；把等待单独归因为某个条款，而忽略联合干预不确定性 |
| A5 有依据的 Keep | 历史禁止所有失败后重试，反例发生在已修复条件；Original 明确允许该条件 | Keep 解释了反例为何不落在当前禁止范围，保留已有改善意图 | 仅说“证据不足”，或宣称当前规则已经证实有效 |
| A6 探索 | 实际同时增加切换许可和永久放弃旧分支；有新分支进展，也遗漏旧分支物品 | D/S 允许切换并保留未完成分支；“最近一次尝试无新信息”在 change 与 Patch 中一致，明确为新假设 | 宣称历史证明阈值/排序最优，或只在 Patch 里发明阈值 |
| A7 错误历史归因 | Replay Plan 提出修复再试，但实际 Diff 只改目标措辞；故意提供的旧 knowledge 错称修复指导有害 | Keep 拒绝这一归因，同时保留当前可执行的修复提议；示例 Replay 输出纠正为实际观察 | 把未落实的意图当作干预，或从“没有落实”推出“已经证明无害” |
| A8 合法撤回 | Parent 已完整包含精确目标识别，当前两条合成执行都保留识别行为 | C 撤回重复提议，Checks 明确清空，必要能力由 Parent 保留 | 仅因收益未知就删唯一覆盖，或以全部撤回掩盖互相矛盾的 Goal |

这些判断只适用于所构造的材料。A2/A4/A6 的条件比较与联合编辑都不能排除其他原因；示例 reason 保留了相应未知。

## 3 证据变化与语义边界

[test_offline_cases.py](../../../tests/skill_evolution/v23_4/test_offline_cases.py) 保留以下对照，未执行模型生成：

- **A1 改变前提事实**：把历史重复失败改成“已经解锁仍失败”。原来把失败解释为锁未改变的理由不再成立。当前事实仍可支持条件化尝试，因此同一 Patch 可保留，但 reason 必须承认历史解释失效和机制未知。
- **A3 改变信息质量要求**：历史 B 仅满足粗略估计，当前任务需要精确读数。历史不能直接证明适用；当前可见事实仍可能支持允许合格替代来源。示例保留修改，改变证据解释，而不强制换 focus 或 Patch。
- **三种相同 step_limit 结果**：未见相关容器、见到但没检查、已检查却没找到目标，分别构造不同 knowledge。终局结果相同不意味着编辑响应相同；最后一种仍存在局部检查行为，不能直接宣布指导无效。
- **必要证据窗口**：关键响应位于第 8 步，仅引用第 1 步时模型看到 trace 而没有第 8 步状态。补充真正支撑条件的第 8 步引用后，既有投影保留了其 before/after。没有修改投影算法，也没有把完整归档可见性当作模型可见性。
- **A8 反向边界**：删除 Parent 的必要能力覆盖，或构造不可同时满足的固定 Goal 后，原撤回理由均不能成立。结构校验仍可能返回 null；这些输入在语义走查中判为不可接受，不把程序通过算作方法成功。

测试明确保留“过时理由结构仍通过”的结果。它证明程序边界存在，不证明模型会主动重判。当前没有自动识别全部语义失败的能力；需要后续生成输出抽查，不新增假装能证明语义的校验器。

## 4 离线交接与版本核验

[test_diagnosis_replay.py](../../../tests/skill_evolution/v23_4/test_diagnosis_replay.py) 通过合成记录与注入式响应检查：

1. V23.4 Diagnosis → Preconditioner → Editor → Replay 构建/调用/重载。Editor 的实际 Diff 与 Candidate 进入 Replay，Adjustment 的预期效果不进入 Memory 证据。
2. Replay 输出通过原 Memory 提交/加载；qualified Diff 与执行引用保留；既有 v3 投影可以送入下一次 Preconditioner。
3. 一次 Memory 修订保留仍需支持旧观察的历史引用，Active 更新为新 ID，同时旧来源可恢复。测试只在临时目录提交，不写真实 Active Memory。
4. Diagnosis 的重要成功轨迹若只有 Group 提及，不能保证进入下游；补齐直接执行引用后可进入。只改 Prompt 引用规范，不扩大现有输入选择算法。
5. 第三步未记录 diagnosis_version 的 v2 归档仍明确按 V23.3 Diagnosis 加载。新请求默认 V23.4；显式旧版需指定。即使两个版本的 parsed Plan 相同，也不能跨版本静默重用。
6. Diagnosis/Replay 的截断、字段/引用错误、调用异常明确失败；原目录不可隐式重试；Prompt 版本、配置、原始响应和 Editor 归档不一致会被拒绝。

## 5 执行结果与剩余验证

2026-10-21 使用已有 τ² Python 环境：**341 passed，5 deselected**。其中 V23.4 共 122 项（第三步 86 项，本步新增 36 项），V23 编译器/Editor/Replay/Memory 回归 219 项；排除的 5 项依赖历史实验归档。本轮未读取这些归档作为测试结果，也未调用真实模型或 Actor。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/v23_4 \
  tests/skill_evolution/v23/test_editor.py \
  tests/skill_evolution/v23/test_preconditioner.py \
  tests/skill_evolution/v23/test_replay_memory.py \
  -k 'not real_handoff_and_legacy_readonly and not real_archives_handoff_readonly and not frozen_real_readonly_interfaces and not actual_replay_sources_and_readonly_reuse and not actual_memory_control_changes_only_memory'
```

结论限于：新表达要求能在现有 Schema 内表示，合成案例的证据与决策可以逐项核对，版本化链路和 Memory 生命周期可离线运行。尚未验证真实模型是否遵循新 Prompt、D/S/C 是否稳定影响实际决策、Skill 是否持续改善；未运行消融、真实跨轮执行或 Gate，也未注册默认方法。
