# V23 Grouping 与 Diagnosis Prompt 统一实现和验证报告

- 日期：2026-10-18。
- 范围：当前 V23 正式 Prompt、共享背景、Diagnosis Check 字段、持久化复用及兼容读取。
- 结果：210 项测试、19 个子测试通过；Grouping、Diagnosis 各一次真实调用均通过结构与引用校验。没有模型重试或新环境执行。

## 1. 实际修改文件

路径相对仓库根目录。仅新增共享 Prompt 装配，不修改事实转换或其他演化算法。

| 文件 | 改动 |
|---|---|
| `src/skill_evolution/v23/grouping_prompt.md` | 采用用户提供的完整英文基线，统一角色、Execution Context、编号任务和 Output Format |
| `src/skill_evolution/v23/diagnosis_prompt.md` | 采用完整英文基线，明确 Skill 可处理问题、已有指导、可观察触发条件、自足更新及 `update_ids` |
| `src/skill_evolution/v23/execution_context.md`（新增） | 唯一的当前共享背景模板 |
| `src/skill_evolution/v23/prompts.py`（新增） | 一次填入真实背景；另提供显式历史模板渲染，用于只读旧协议校验 |
| `src/skill_evolution/v23/grouping.py` | 接入共用背景，保存渲染 Prompt／解析结果，配置一致性复用，显式读取旧分组模板；五字段校验规则未放宽 |
| `src/skill_evolution/v23/diagnosis.py` | 去掉当前 Prompt 的标题截取，严格验证 `update_ids`；旧协议先验证后转换返回副本；配置一致性复用 |
| `tests/skill_evolution/v23/test_grouping.py` | 正式 Prompt 与已更新设计文档全文一致性测试 |
| `tests/skill_evolution/v23/test_diagnosis.py` | 全部当前 Check 用例迁移到 `update_ids`；更新共享背景及旧档案读取方式，原失败测试保留 |
| `tests/skill_evolution/v23/test_prompt_alignment.py`（新增） | 35 项共享装配、兼容、旧字段拒绝、配置／Prompt 变更拒绝复用、真实轨迹一致性测试 |
| `src/skill_evolution/v23/README.md` | 新用法、配置复用及只读旧档案示例 |
| `docs/methods/v23/AUTOMATIC_GROUPING_DESIGN.md`、`DIAGNOSIS_DESIGN.md` | 更新正式 Prompt 和当前接口说明 |
| `docs/methods/v23/PRECONDITIONER_DESIGN.md` | 仅将上游 `update_ids` 和旧结果交接说明更新为当前已实现状态 |
| V23 文档／实验索引、`docs/04_EXPERIMENT_LOG.md`、本实验目录 | 状态、冻结参数、全文／代码快照、差异和报告 |

`facts.py` 与修改前逐字节一致；ALFWorld Adapter 未修改。实验目录中的 before/current 是审计快照，正式运行始终使用当前 `src/skill_evolution/v23/`，没有新建 v1/v2、revision 模块或审核 Agent。

## 2. 两份 Prompt 全文及差异

以下文件保存完整内容，均已核对与真实请求所用源码一致：

| 材料 | 修改前全文 | 修改后全文 | 逐行差异 |
|---|---|---|---|
| Grouping | [旧模板](../config/before/grouping_prompt.md) | [新模板](../config/current/grouping_prompt.md) | [diff](../config/grouping_prompt.md.diff) |
| Diagnosis | [旧模板](../config/before/diagnosis_prompt.md) | [新模板](../config/current/diagnosis_prompt.md) | [diff](../config/diagnosis_prompt.md.diff) |

[共享 Execution Context 全文](../config/current/execution_context.md)。实际替换后的完整系统消息分别见 [Grouping Prompt](../../../../../artifacts/methods/v23/v23_prompt_alignment_001/grouping/prompt.md) 与 [Diagnosis Prompt](../../../../../artifacts/methods/v23/v23_prompt_alignment_001/diagnosis/prompt.md)。完整用户 JSON 保存在各目录的 `messages.json`。

两份新模板直接采用用户给定基线，没有叠加整份设计文档，也没有追加针对柜子状态或某一步的补丁。

- Grouping：先说明完整事实的时间与菜单语义，再比较具体决策问题；合并原来分散的目标和规则；保持互斥全覆盖、允许单例、不固定组数、非诊断职责和五字段输出。
- Diagnosis：区分新的 Skill 指导、已有规则未遵循、技术失败与成功行为；要求条件在 Actor 决策时可识别；避免机械重复已有充分指导；通过 goal／边界保留成功行为；继续积极提出联合初稿，不以效果未知作为停止理由。
- 两者统一使用 `# Module`、角色、`{{execution_context}}`、编号章节和 Output Format。
- 唯一模型数据接口变化是 `checks[].about → checks[].update_ids`。Grouping Schema、Diagnosis 其余字段、事实及引用保持不变。

这些是指令目标，不等于真实输出已经完全遵循。语义核查见第 6 节。

## 3. 共享执行背景和兼容边界

两个当前模块均调用 `prompts.render_prompt()`。它调用 `execution_context(background)`，从唯一的 `execution_context.md` 读取能力说明，将本批 `background` 中的 `system_prompt / initial_template / history_template / max_steps` 填入，再一次性替换模块的 `{{execution_context}}`。

替换仅处理原模板的占位符，不递归解释插入的 Actor 协议内容。实际协议中的 `{current_observation}`、`{action_history}` 等占位符原样保留；这是被分析的原始输入模板，不是未完成的 Diagnosis／Grouping 渲染。当前实际请求没有残留模块占位符或重复背景。测试还验证 Actor 原文中出现双花括号时不被误替换。

没有读取当前默认 Actor 配置去覆盖历史配置，也没有重新转换轨迹。四条 Parent 的重新装配结果与原 Grouping `input.json` 完全相同，93 个步骤的实际 Actor 请求均通过原有核验。

新 `validate_diagnosis()` 只接受 `update_ids`，旧 `about` 或同时带两个字段的模型输出都会失败并保存原文。默认 `load_*` 使用当前 Prompt；旧目录不能作为新 Prompt 的完成结果复用。

历史读取是显式操作：向 `load_grouping(..., legacy_template=...)` 或 `load_diagnosis(..., legacy_templates=...)` 提供可信的冻结旧模板。先核对完整历史 messages、输入、响应、结果和旧字段契约，再对 Diagnosis 返回副本做 `about → update_ids`，最后按新契约复核。旧磁盘文件不修改。历史渲染兼容函数仍使用冻结旧模板当时的段落标记来重现原文，当前模块不依赖这些标题，也不从当前 Grouping Prompt 截取背景。

新 `run.json.call_config` 记录非敏感调用参数。复用须同时匹配输入、Prompt、轮次及期望配置，包括模型、端点、max_tokens、timeout、temperature、reasoning_effort、thinking、stream。变化时拒绝复用，不调用模型“修复”。只读 `load_*` 可显式传入 `expected_call_config`；运行入口总是核对声明配置。没有使用哈希或创建额外模型字段。

## 4. 离线测试

从仓库根目录运行：

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

结果：**210 passed，19 subtests passed；0 失败，0 跳过**。[完整日志](../../../../../artifacts/methods/v23/v23_prompt_alignment_001/offline_tests.txt)。原有 175 项测试保留，新增 35 项。

覆盖共享背景全文一致、Diagnosis 不受 Grouping 标题变化影响、真实协议原文保留、占位符异常拒绝、事实装配无变化、Grouping 五字段、Diagnosis 三种决定、空及多关联 Checks、非法／重复引用、旧字段拒绝、解析／截断／调用失败归档、旧协议先校验后转换、不改变旧档案、Prompt／输入／配置变化拒绝复用、相同条件复用和 Grouping→Diagnosis 交接。

真实历史资料在本机存在，相关测试全部执行，没有因缺档跳过。旧两次实验目录与调用前副本逐字节一致；本次四个原始 `trajectory.json` 也逐字节不变。

## 5. 冻结配置及两次真实调用

[冻结配置](../config/plan.json)在第一次调用前写入，确定四条来源、事实、模型参数、预算及语义核查标准。原始输入另存 `frozen_input.json`。Diagnosis 必须使用本次新 Grouping，在第二次请求前保存完整 `diagnosis_preflight.json`；没有使用旧分组替代。

本批为 `train:0012–0015`，4 条 Parent、93 步，实际 `parent=null`。请求走 `https://api.deepseek.com/chat/completions`，模型 `deepseek-flash`；两阶段均 max_tokens 16,384、timeout 300 秒、temperature 1、reasoning_effort medium、thinking enabled、stream false、输入字符上限 100,000。

相对旧实验，Grouping 输出上限由 8,192 提高至 16,384，timeout 由 180 秒提高至 300 秒；Diagnosis 保持原来的 16,384 和 300 秒。没有自动重试。

| 阶段 | 次数 | 输入字符 | 输入 Token | 输出 Token（含推理） | 其中推理 Token | 总 Token | 耗时 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Grouping | 1 | 80,482 | 23,151 | 2,390 | 1,659 | 25,541 | 12.98 秒 |
| Diagnosis | 1 | 85,101 | 24,217 | 5,666 | 4,786 | 29,883 | 29.88 秒 |

合计 **55,424 Token**；两次均 `finish_reason=stop`，缓存命中 0。推理 Token 已计入输出，不重复相加。API 没有返回货币账单金额，未估造费用。

每阶段保存 `input.json / prompt.md / messages.json / request.json / http_response.txt / http_status.json / response.json / raw_output.txt / parsed.json / validation.json / run.json` 和有效结果 JSON。完整 HTTP 响应保留服务端返回内容及用量。凭据不归档。

两阶段完成后，用“一旦被调用就抛错”的 generator 核验同输入、同配置复用：正常返回，零新增请求，两个新目录也未改动。冻结的 Prompt 与代码快照未在真实调用后修改。

## 6. 原始结果及语义核查

### Grouping

[完整实际 JSON](../results/grouping.json)。仍为两组：G1 包含 P1／P4，G2 包含 P2／P3，覆盖全部执行且无重复。以下是对原文的人工核查，没有新增审核模型。

| 核查项 | 观察 |
|---|---|
| 共同决策问题 | G1 比较取物、清洁、放置及开容器前提；G2 比较寻找目标时重复原位置还是扩展位置。G2 含成功与步数耗尽两种结果，并非纯按成败划组 |
| 具体程度 | G2 具有明确搜索选择。G1 的 `decision_problem` 更像整个成功流程，具体决策条件不够集中；`shared_basis` 也接近逐段复述轨迹，简洁性目标未完全满足 |
| 时间与信息 | P1 先开 fridge 再取物，P4 先到关闭 cabinet、再 open、再 move，描述与事实一致。P3 扩展到 cart／bathtub 的顺序与 P3:18–19 一致；没有重复旧输出把 P3:10 放在 P3:1–17 之后的表述，但省略了 shelf 4 的访问 |
| 可见机会差异 | 正确指出 P3 有 cart／bathtub 候选，P2 的菜单没有这两处；没有直接要求 P2 复制另一场景的目标位置 |
| 事实偏差 | G2 最后一项差异提到 P2 未检查的“remaining cabinets and drawers”。P2 只暴露 drawer 1，且已经多次检查；“remaining drawers”没有事实支持。范围引用 P2:1–50、P3:1–20 可解析，但定位较宽 |

### Diagnosis

[完整实际 JSON](../results/diagnosis.json)。输出为 `revise`，3 项 Update、3 项 Check；所有 Check 使用 `update_ids`，各引用均合法，未增加协议外字段。

| 项目 | 有依据的部分 | 仍存在的问题 |
|---|---|---|
| reason／goal | 比较 P2 的反复访问、P3 扩展位置后找到目标以及 P1/P3/P4 的成功阶段，使用了真实行为差异；目标包含搜索改进与有效流程保持 | reason 仍把一次基础协议未遵循直接作为新 Update 的理由，未充分区分已有指令和缺失指导 |
| u1 搜索 | P2:5/8/11/21 及 outcome 支持无目标重复和步数耗尽；P3:18–20 支持转向其他位置后发现并取得目标。文本明确提到有限历史，给出最近观察动作中的位置作为局部判断条件 | 大部分要求仍使用全局 `unchecked / previously checked / unexamined`，没有完全限定为可见历史。“deterministic forward sweep”是新提出的策略假设，本批未观察或验证这种策略；没有明确给出有限历史下推进顺序的规则，不能把补偿记忆缺失当成已证明效果 |
| u2 取物清洁放置 | P1/P3/P4 的清洁与放置、P1 源容器打开及 P4 目的柜打开都提供直接依据；这些具体前提并未写在基础系统模板中，且 parent=null，因此不能仅因来自成功经验就断定它无用 | 当前批次没有暴露这条完整流程的缺失，模型主要将成功行为重新写为独立 Update；“不替换成无关物体”也没有对应失败证据。是否需要独立规则，仍应与 goal／保留边界区分 |
| u3 菜单内动作 | P4:5 的动作确实不在当步 Actor 可见菜单中，环境反馈无效果；P4:6 改到可用位置发现目标 | 基础初始／历史模板已经明确要求选择 admissible action。u3 主要重复既有协议，没有充分解释重复写入 Skill 的新增价值；本次“避免重复已有协议”的语义目标未完全达到 |
| c1 | 观察 A-B-A 循环与扩展位置，具有后续行为检查价值 | 仍包含全局“未检查”判断与 `until the target is found`，未表达候选不足或搜索边界；Checks 不是 Actor 指令，但观察范围仍有待限定 |
| c2／c3 | c2 观察清洁前提与关闭目的地处理的保持；c3 观察不可用动作下的选择行为，关联均有效 | c2 接近成功流程复核，c3 仍是已有协议遵循问题；尚未执行 Candidate 检验这些响应 |

新输出使用“target absent”而非把有其他物品的 sink/counter 一概描述为空，并明确加入了有限历史的局部规则。但能力边界仍不完整，不能把局部表述视为全局问题已解决。

模型可以提出尚未执行过的新策略；这里的问题不是“新策略必然不合法”，而是其具体实现条件和效果仍是待检验假设，不能当作已观察到的历史事实或已验证改进。没有因此修改 Prompt、结果或额外采样。

### 新旧比较的解释边界

旧 Diagnosis 为 4 项 Update／3 项 Check，新结果为 3 项／3 项；分组成员组合相同。此处仅描述结果差异。两阶段使用新 Prompt、Grouping 预算变化，且模型随机调用各一次，没有控制随机性或运行 Candidate，不能把数量、措辞或 Token 差异解释为 Prompt 的因果改善，也不能声称持续 Skill 自进化收益。

## 7. 后续 Preconditioner 交接

上游技术接口已可使用：

```python
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.diagnosis import load_diagnosis

grouped = load_grouping("artifacts/methods/v23/v23_prompt_alignment_001/grouping")
saved = load_diagnosis("artifacts/methods/v23/v23_prompt_alignment_001/diagnosis",
                       expected_grouping=grouped)
plan = saved["diagnosis"]["plan"]
# Check 使用 update_ids；同时提供 facts、background、grouping、sources、round_id。
```

这份 Plan 可以作为 Preconditioner 原始输入，保留原始问题和依据。不得预先把普通能力约束修正包装成历史 Memory 收益。Preconditioner 的机制接口已有设计，但正式 Prompt、MemoryEntry 的可读内容／历史引用解析仍需在其实施阶段确定；本次没有开发这些模块。

当前结果表明工程交接、字段迁移和两次调用已验证，语义优化目标部分未达到。到此停止，没有 Preconditioner、Memory、Editor、Replay 或完整演化实验。
