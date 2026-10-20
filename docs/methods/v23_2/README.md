# Govern V23.2：研究基线与优先级

日期：2026-10-19。**第一项：Update 可执行性优化——暂缓，尚未解决。后续开发恢复正式 V23 原始方法基线。**

V23.2 的核心方向仍是 **Diagnostic Preconditioning**：Diagnosis 提出原始更新，Preconditioner 根据当前条件与历史编辑—行为响应调整更新，Editor 落实修改，Replay／Memory 从真实行为中积累依据。可执行性审核不作为新的主要创新点，也不作为继续 V23.2 研究的必要前提。

## 当前实际基线

| 内容 | 后续默认来源 |
|---|---|
| Diagnosis | [原始 V23 Prompt](../../../src/skill_evolution/v23/diagnosis_prompt.md) |
| Preconditioner | [原始 V23 Prompt](../../../src/skill_evolution/v23/preconditioner_prompt.md) |
| Execution Context | [原始 V23 能力说明](../../../src/skill_evolution/v23/execution_context.md) |
| Actor | 保持现有最近两组历史及全部执行设置 |
| Grouping、Editor、Replay、Memory、Gate、Orchestrator | 完全继承 V23，不修改 JSON 契约、Effective Plan 编译及模块职责 |

V23 原始文件与正式冻结版本核对一致，无需覆盖恢复。[V23.2 局部入口](../../../src/skill_evolution/v23_2/local_validation.py)的默认 Prompt 路径直接引用 V23 模块的 `PROMPT_PATH`，未指定 `context_path` 时仍由 V23 原始共享背景渲染。旧实验模板保留在原位置，但不再默认生效；没有复制整套框架或创建新的正式 Campaign 入口。

2026-10-20 端点配置更新：后续新运行共用 [V23 模型路由](../../../src/skill_evolution/v23/README.md#v23--v232-端点路由)。内网 `http://llm-proxy.intra.xiaojukeji.com` 统一使用 `deepseek-v4.1-flash`，官方 `https://api.deepseek.com` 统一使用 `deepseek-flash`，涵盖 Actor 和进化模块。局部验证从环境解析实际配置后归档；旧实验的配置、响应和源码快照保留原值，源码冻结检查会拒绝直接重跑这些旧入口。上段“源码与冻结版本一致”描述的是基线恢复时的状态，当前新增路由后不再成立，Prompt 基线保持不变。

## 暂缓第一项的依据

历史材料确实存在对 Actor 无法获得的累计搜索进度的依赖。三次局部尝试有部分文本改善，但没有可靠解决完整 Update 的可执行性问题。根据用户已完成的比较方法核查，SkillOpt、SkillAdam 公开优化后 Skill 中也存在类似依赖；该外部核查作为用户提供的研究背景记录，本次未重新检索验证。因此现阶段不把它视为 Govern 独有的核心缺陷或优先创新目标。不扩大 Actor 历史窗口，不增加复杂的信息依赖审核机制。

| 历史实验 | 尝试与结论 |
|---|---|
| [v23_2_executability_001](../../../experiments/methods/v23_2/v23_2_executability_001/reports/REPORT.md) | 强化 Diagnosis／Preconditioner 可执行性要求；最终仍有全局进度依赖 |
| [v23_2_executability_002](../../../experiments/methods/v23_2/v23_2_executability_002/reports/REPORT.md) | 检查全部最终 Updates；Keep 项及替代策略仍有信息依赖 |
| [v23_2_capability_001](../../../experiments/methods/v23_2/v23_2_capability_001/reports/REPORT.md) | 原始 V23 Prompt 加共享能力澄清；R03 技术停止，R06 仍有续行依赖及过窄回源限制 |

上述目录中的冻结配置、Prompt、原始响应、失败尝试、Effective Plan、核查和用量记录全部保留，不覆盖或重生成。它们记录历史尝试，不构成当前方法设计。单次固定材料的局部改善也不证明 ALFWorld 成功率提升。

历史读取继续使用严格的 `load_attempt`，显式传入对应 `prompt_path`；第三次实验还须传入对应 `context_path`。第一轮用原位置 `src/skill_evolution/v23_2/{diagnosis,preconditioner}_prompt.md`，第二轮用其实验配置中的 Preconditioner 模板，第三轮用原 V23 Preconditioner 模板和其实验配置中的 Execution Context。读取前与各实验 `config/implementation.json` 冻结内容核对；不要用当前默认配置代替历史配置，也不要重新运行旧实验入口。

## 后续优先级

| 问题 | 当前安排 |
|---|---|
| ① Update 可执行性 | 暂缓 |
| ② 历史反例未有效约束更新 | 已完成历史核查及支持范围、构造、对称约束、证据校准局部验证；原取舍与替代范围／强度尚未稳定对齐，默认仍为V23 |
| ③ 多项更新捆绑 | 暂缓 |
| ④ Memory 事实概括不严谨 | 后续轻量改善 |
| ⑤ Memory 输入成本增长 | 暂缓 |
| ⑥ 消融与重复实验 | 后续安排 |

第二项研究关注历史编辑—行为响应是否实际改变当前 Update 的方向、范围与实现方式，仍以最终更新为判断对象。[历史证据分析](../../../experiments/methods/v23_2/v23_2_memory_analysis_001/reports/REPORT.md)之后，已完成[支持范围对齐的独立局部验证](../../../experiments/methods/v23_2/v23_2_response_alignment_001/reports/REPORT.md)：仅替换 Preconditioner 一处历史使用要求，固定 R04/R05/R06 各调用一次。R04 保留有效温度经验，R05 允许新探索，R06 识别并修改了类内穷尽策略；但替代 Update 又出现缺乏依据的类别采样终止条件，尚不能认定完整语义验证通过。该模板仅作为待验证研究候选归档，不叠加第一项修改，当前默认仍为上表原始 V23 文件。此次验证已停止，未运行 Editor、Candidate、Replay 或 ALFWorld，也未更新 Memory。

正式训练、最终 Skill、Memory 与 Test 结果保持原样；未来使用同一 Test 比较仍属于同基准回归。

后续授权的 [R06 小规模行为验证](../../../experiments/methods/v23_2/v23_2_response_behavior_001/reports/REPORT.md)已完成：固定上述 R06 Effective Plan，由原 Editor 生成 Candidate 并执行原七条优化任务。新 Candidate 5/7、162 步，原 Candidate 5/7、202 步，Parent 6/7、178 步。plate 搜索和温度操作有局部改善，但 apple/book 搜索失败未修复；未观察到类别采样后提前停止。温度 u1 两版相同，Editor 表达与 Actor 随机性无法隔离，故仍仅保留待验证候选，默认基线不变；不自动进入完整六轮实验。

随后完成[证据约束的 Update 构造验证](../../../experiments/methods/v23_2/v23_2_response_construction_001/reports/REPORT.md)：统一修订同一位置的要求，固定 R04/R05/R06 各一次逻辑调用。R04 保留有效操作与计数，R05 允许新启发式；R06 却保留类内穷尽与保证进度，未延续上一轮的关键策略区分。没有稳定改善原始取舍（A），也未验证替代构造的依据对齐（B）；未机械禁止大改或探索（C），但仍有假设／事实混淆。该版仅保留为研究记录，不晋升为下一优先候选，默认 V23 不变；完成后停止，未开展行为实验或追加补丁。

原基线恢复的离线核验与保护结果见[基线恢复记录](BASELINE_RESTORE.md)；第二项验证的测试、用量及保护记录见上述独立报告。

本次完成[原始与替代 Update 的对称证据约束验证](../../../experiments/methods/v23_2/v23_2_response_symmetric_001/reports/REPORT.md)：先核查R06及M6/M10实际Diff与轨迹，再冻结仅一处替换的通用Prompt。固定R04/R05/R06各一次调用，均首次合法。R06重新识别类内穷尽风险并改动最终Update，A有局部改善；但替代的表面→设备→柜子→抽屉排序及续行限制仍未充分说明依据／假设，B未解决。R04有效操作与R05新探索保留，但R05出现历史遗漏的因果过度解释。保留对称约束的研究信号，不将该完整Prompt晋升为下一优先候选或默认；三次完成后停止，没有追加补丁或行为实验。

随后完成[证据校准验证](../../../experiments/methods/v23_2/v23_2_evidence_calibration_001/reports/REPORT.md)：先离线比较既有最终Updates，再冻结统一校准策略、条件和强制程度的一处Prompt替换。R04保留有条件的直接加热；R06调整为预算约束跨类采样，没有整套固定类别排序、类别采样终止和显式保证，但尺度与假设仍不清楚；R05将同类遗漏反例转成查完该类再换类的倾向。A/B/C仅局部改善，尚未共同通过，不晋升下一优先候选或默认。3次逻辑调用、2次技术重试后均合法；所有失败与输出保留，完成后停止，未追加Prompt修订或行为实验。
