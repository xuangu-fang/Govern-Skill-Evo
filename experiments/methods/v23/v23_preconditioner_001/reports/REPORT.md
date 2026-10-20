# V23 Preconditioner 实现与无历史验证报告

日期：2026-10-18。Preconditioner 已实现，284 项测试与 19 个子测试通过。仅一次真实 `deepseek-flash` 调用返回合法 **Keep**：`decision=ready / adjustments=[] / checks=null`。程序生成的 Effective Plan 与原始 Diagnosis Plan 完全一致，保留 3 项 Update 和 3 项 Check；同输入复用零新增请求。

本次验证了无历史输入下的调用、合法 Keep、来源追溯和确定性编译通路。合并、拆分、撤下等非空调整通过离线测试，**本次真实模型没有产生调整，因此不能声称这些操作的真实模型效果已验证**。没有历史 Memory，没有 Candidate 或新的环境执行，也没有历史响应预条件化收益证据。

## 1. 实际文件变更

| 文件 | 作用 |
|---|---|
| [preconditioner.py](../../../../../src/skill_evolution/v23/preconditioner.py)（新增） | 上游读取、完整引用执行选择、消息装配、单次调用、四字段契约验证、同时编译、持久化／复用及 CLI |
| [preconditioner_prompt.md](../../../../../src/skill_evolution/v23/preconditioner_prompt.md)（新增） | 用户确认的完整通用英文 Prompt，含唯一 `{{execution_context}}` 插入点，无额外案例补丁 |
| [test_preconditioner.py](../../../../../tests/skill_evolution/v23/test_preconditioner.py)（新增） | 74 项离线测试，含实际新旧档案只读交接 |
| [V23 README](../../../../../src/skill_evolution/v23/README.md)、[包说明](../../../../../src/skill_evolution/v23/__init__.py)、[实现索引](../../../../../src/skill_evolution/README.md) | 接口、命令、编译与停点语义、历史读取边界 |
| [设计文档](../../../../../docs/methods/v23/PRECONDITIONER_DESIGN.md)、[方法索引](../../../../../docs/methods/v23/README.md) | 更新实现状态，明确位置顺序与来源依据继承顺序，链接验证结果 |
| [实验索引](../../README.md)、[实验日志](../../../../../docs/04_EXPERIMENT_LOG.md) | 登记本次独立实验与限制 |
| 本实验 [README](../README.md)、`config/`、`results/`、本报告 | 冻结配置、执行脚本、完整源码／Prompt 快照、结果与核查 |
| [原始实验目录](../../../../../artifacts/methods/v23/v23_preconditioner_001/) | 测试日志、输入／消息冻结、上游字节快照、HTTP 请求／响应、验证与复用记录 |

未修改 Grouping、Diagnosis、facts、共享背景、模型路由或 ALFWorld Adapter 的实现；未新增并行版本、审核 Agent、自动修复调用或自然语言评分器。

## 2. Prompt、真实背景与输入

正式英文全文见 [冻结 Prompt](../config/source/preconditioner_prompt.md)，实际发给模型的完整系统消息见 [live/prompt.md](../../../../../artifacts/methods/v23/v23_preconditioner_001/live/prompt.md)。Prompt 按用户提供的设计基线直接落地，不叠加设计文档，不追加对当前四条任务的特殊规则。

装配仍调用 `prompts.render_prompt()`，唯一背景来源为 `execution_context.md`；实际基础系统指令、初始／历史模板和 50 步上限来自本轮保存的 `background`。背景在 Prompt 中出现一次，插入的 Actor 模板原文保留。Actor 只能看到当前观察／动作候选及最近两组行动前观察—动作，不具备完整轨迹记忆或持久笔记。完整 [messages.json](../../../../../artifacts/methods/v23/v23_preconditioner_001/live/messages.json) 与真正发送的请求一致。

```text
load_grouping(saved Grouping)
  → load_diagnosis(saved Diagnosis, expected_grouping=grouped)
  → preconditioner_input(saved)
  → messages_for(saved)
```

模型数据严格只有六字段：

```json
{
  "parent": null,
  "plan": {"goal": "原始 Goal", "updates": [], "checks": []},
  "command_sets": {},
  "runs": [],
  "grouping": {"groups": []},
  "memory": []
}
```

上面是形状示意，真实 Plan 非空，完整输入见 [frozen_input.json](../../../../../artifacts/methods/v23/v23_preconditioner_001/frozen_input.json)。规则如下：

1. 扫描原 Plan 的执行引用，包括 basis 和 Goal／Update／Check 文本中的引用；选中对应执行的完整记录，不截取步骤或生成摘要。
2. 每条执行只出现一次，保持原顺序、ID、初始状态、`before → action → after`、反馈和结果。没有新轨迹转换器。
3. 提供 Plan 显式引用的 Group 和所选执行所属的 Group；Group 中的其余成员不会自动展开为轨迹。缺失的执行不表示该执行或事件没有发生。
4. 菜单只选所提供完整执行引用到的 `C`，值及顺序原样保留，不再次过滤、归一化或编号。沿用已经核验过的 Actor 可见菜单和独立环境合法性记录。
5. Parent 严格来自原 Diagnosis 的实际执行事实，本次为 null。本阶段拒绝非空 Memory，且 Adjustment 不允许引用不存在的 Memory ID。

本次三个 Update 覆盖了四条 Parent，实际输入因此仍是 `train:0012–0015`、93 步、两个 Group、三项原 Update／Check。模型六字段之外的完整上游事实、背景与来源只保存于程序侧 `input.json`，便于复用比较和追溯。

旧 `about` 档案经过现有 `load_grouping/load_diagnosis` 的显式历史模板兼容路径校验后，在只读副本中变为 `update_ids`；Preconditioner 不输出或接受旧 Check 名称。实际旧档案测试前后逐字节一致。

## 3. 输出验证与确定性编译

模型只输出 `decision / reason / adjustments / checks`。Adjustment 只含 `from / to / basis / reason`；Replacement Update 只含 `id / text`。不允许模型直接提供第二份 Plan。

`compile_effective_plan()` 对全部 Adjustments 同时作用于原 Plan：

- `from` 非空且仅引用原 Update，同一来源只调整一次，不允许调整链。
- 一对一可保留自己的 ID，其他原 ID 不可占用；合并和拆分使用新 ID，不与其他结果或证据 ID 冲突。
- 替换结果插到被替换来源的最早位置；拆分按 `to` 顺序，未调整项保持相对顺序。模型调整数组顺序不改变编译结果。
- Goal 原样保留，Keep 原文保留。修改／拆分继承来源 basis，合并按来源在原 Plan 中的顺序去重。Adjustment basis 独立保存，不混入 Effective Update。
- `checks=null` 继承，数组整体替换，`[]` 清空。最终 `update_ids` 必须指向有效 Update；旧引用失效时拒绝结果，不猜测迁移。

`ready` 必须有有效 Update；`no_change` 必须显式撤下全部原 Update 并清空 Checks；`need_evidence` 只接受空调整与 null Checks。后两者的 `effective_plan.json` 为 JSON null，均作为合法语义停点保存。技术错误、截断或契约失败保持 invalid，不伪装成三种语义决定。

basis 存在性和结构检查不证明修改后自然语言要求的正确性。程序没有以启发式策略判断调整是否“好”。

`run_preconditioner()` 复用现有单次 HTTP、JSON 解析和原子 JSON 保存函数。原始请求、HTTP 内容、响应 usage、原文、解析和错误分开保存。有效结果持久化为 `preconditioner.json / effective_plan.json`。再次读取会重新解析响应、核对输入／Prompt／配置并重新编译；结果被改写或条件不一致会拒绝复用，无自动重采样。

## 4. 离线与回归

在仓库根目录运行：

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

结果：**284 passed, 19 subtests passed in 1.91s**；0 失败，0 跳过。其中新增 Preconditioner 74 项，原有相关测试 210 项。完整日志见 [offline_tests.txt](../../../../../artifacts/methods/v23/v23_preconditioner_001/offline_tests.txt)。

覆盖三种决定与停点、Keep／修改／合并／拆分／撤下、同时应用与禁止链、ID 冲突／非法来源／重复 from、排序与 basis 继承、Goal 不变、Checks 三模式及失效引用、无 Skill／有 Skill、部分执行输入、Group 不扩展执行、虚构历史引用拒绝、原始／当前 Diagnosis 只读交接、共享背景、非法 JSON／截断／HTTP 503／网络错误／中断保留、输入／Prompt／配置／保存结果变化拒绝复用，以及相同条件零重复调用。

回归仍覆盖精确 help 过滤、菜单共享、前后状态时间语义、真实 Actor 请求和 Grouping／Diagnosis 原有契约。本次没有放宽原校验，也没有修改测试以接受模型语义错误。

## 5. 唯一一次真实调用

[冻结配置](../config/plan.json) 在发送前保存。沿用原实验路由和全部调用参数：

| 项目 | 实际值 |
|---|---|
| 模型／端点 | deepseek-flash / api.deepseek.com/chat/completions |
| max_tokens / timeout | 16,384 / 300 秒 |
| temperature / reasoning_effort | 1.0 / medium |
| thinking / stream | enabled / false |
| 实际输入／字符上限 | 87,668 / 100,000 字符；字符数不是 Token 数 |
| 调用／重试／上游调用／新 episode | 1 / 0 / 0 / 0 |
| finish_reason / validation | stop / valid |
| 输入 Token | 24,771 |
| 输出 Token | 12,456，其中推理 12,239 |
| 总 Token | 37,227 |
| 耗时 | 60.126474 秒 |
| 金额 | API 未返回账单金额，未推测金额 |

原始请求、HTTP 响应及 usage 保存在 [live/](../../../../../artifacts/methods/v23/v23_preconditioner_001/live/)。摘要见 [summary.json](../results/summary.json)。本次真实模型完整输出如下，与原始响应解析结果一致：

```json
{
  "decision": "ready",
  "reason": "The supplied runs support all three Updates. P2 reached the step limit by cycling among sinkbasin 1, countertop 1, drawer 1, cabinet 1, and shelf 1 while leaving many exposed locations unchecked, which directly supports u1's no-cycling, forward-sweep, and expand-to-new-receptacle-types strategy; P3 succeeded after expanding to cart 1 and bathtubbasin 1, confirming the value of broadening the search. The deterministic ordered sweep is implementable with the Actor's current observation and last-two-step history. P1, P3, and P4 all follow the acquire/open-source/clean-at-sinkbasin/open-destination/place sequence of u2 (including opening fridge 1 and cabinet 1), and P4:5 shows an inadmissible action producing 'Nothing happens' before P4:6 recovers, supporting u3. No evidence contradicts the proposed behaviors, so the Updates are preserved unchanged.",
  "adjustments": [],
  "checks": null
}
```

程序编译结果见完整 [effective_plan.json](../results/effective_plan.json)：Goal、u1/u2/u3 的 text 与 basis、c1/c2/c3 的 question 与 update_ids 均与原 Plan 完全相同。没有把 reason 或其他调整依据注入 Plan。已有三项 Check 引用均有效，没有遗漏或新增 Update。

真实调用、解析、契约和保存均成功；随后的报告副本导出发生一次 `FileNotFoundError`：实验脚本遗漏创建 `results/` 目录。原始调用脚本和 traceback 保留，未重新运行。另一个只读 [导出恢复脚本](../config/export_saved_results.py) 创建报告目录，从 `live/` 复制原结果并重新核验，**零新增模型请求**。这次报告导出故障不掩盖为模型语义停点，也没有修改原始 Prompt、响应或结果。

同输入同配置复用已经以禁止调用的 generator 验证；live 文件前后字节一致，上游 Grouping／Diagnosis 与调用前快照字节一致，调用时源码和 Prompt 与冻结快照一致。

## 6. 逐项语义核查

以下是人工对保存事实的核查，不是新增模型或程序评分器。所有判断问题原样保留，未追加 Prompt 规则或重采样。

| 项目 | 核查结论 |
|---|---|
| 理解原始 Plan | 识别 u1 搜索、u2 清洁交付依赖、u3 动作候选约束，整体选择 Keep；没有生成无关要求或第二份 Plan。 |
| u1 的当前事实依据 | P2:5/8/11/21 等与完整后续轨迹确实显示反复访问，最终 step_limit；P3:18 到 cart、19 到 bathtubbasin 发现目标、20 取得目标，支持考虑扩展搜索范围。P2 与 P3 的场景菜单不同，不能把 cart／bathtub 当成 P2 同样具备的选择。模型没有明确声称 P2 具备它们。 |
| u1 的可执行性限制 | reason 直接断言“deterministic ordered sweep”可由当前观察和最近两步实现，但原 Update 仍使用全局 unchecked／previously checked 条件，未给出仅凭有限历史判定这些状态的方法。固定扫描本身可能可行，但这份完整要求的可靠执行尚未由现有事实证明。模型没有解决这一潜在矛盾。 |
| 搜索效果解释 | “confirming the value”表述过强。P3 扩展搜索后找到目标是当前单条轨迹事实，不是顺序扫描／扩展策略的独立因果收益；本次没有真正编辑 Skill 或对照执行。原 Update 的确定性扫描仍是待验证策略假设。 |
| u2 的事实与保留 | P1:2 先开 fridge、3 再取物；P1:5/7、P3:22/24、P4:9/12 支持先清洁后交付，P4:11 支持必要时先开目的容器。Keep 保留这些成功行为，没有破坏原 Goal。 |
| u2 的概括偏差 | reason 将 P1、P3、P4 都概括为 acquire/open-source/clean/open-destination/place。实际上 P3 没有开容器动作，P1 开源容器且先于取得，P4 开目的容器；这些是跨执行的条件性步骤，并非每条执行都经历完整序列。原 u2 本身有 if 条件，此次理由的压缩表述仍不准确。 |
| u3 与已有基础协议 | P4:5 的 `go to stoveburner 3` 不在当时可见菜单中且环境非法，返回 Nothing happens；P4:6 转向 stoveburner 4，确实存在当前行为依据。但初始和历史模板已经要求选择 admissible action。u3 首句明显重复，后续“选择可用替代动作”是较具体的恢复要求。模型未区分这两部分，没有说明重复规则是否必要；不能直接据此认定必须撤下整项。 |
| Checks | 三项 Check 保留且都合法关联原 Update。c1 观察重复访问／扩展，c2 观察清洁与交付依赖，c3 观察可用动作及恢复，有观察价值。c1 的 unchecked 可以由后续完整轨迹观察者核对，但这不能反过来赋予 Actor 全局记忆；“until found”也不代表任意任务都保证成功。 |
| D/S/C 与 Keep | Keep 是合法结果，不能因为没有调整而判契约失败。本次没有无依据的范围收缩、扩大或撤下，也没有真实非空 D/S/C 调整可供验证。离线编译支持不等于真实模型已作出高质量调整。 |
| 历史来源边界 | memory=[]；输出未引用 Memory，也没有把当前事实称为历史编辑收益。它对当前证据的过度肯定与虚构历史是不同问题，分别记录。 |

这份 Effective Plan 的来源和结构可以直接交接，但不能把 `ready` 当作程序已经证明所有要求可执行、已消除冗余或能提高任务成功率。当前真实结果保留了原 Plan 的有限历史约束不足和基础协议重复问题。一次随机调用也不能证明 Prompt 或 Preconditioner 的总体质量。

## 7. 下游接口与下一步历史信息

```python
from src.skill_evolution.v23.preconditioner import load_preconditioner
saved = load_preconditioner("artifacts/methods/v23/v23_preconditioner_001/live")
original_plan = saved["diagnosis"]["plan"]
adjustment_result = saved["preconditioner"]
effective_plan = saved["effective_plan"]
```

同时可读取 `facts / background / grouping / sources / round_id`。本次 `effective_plan` 非空，后续模块能够直接读取；合法语义停点时它为 None。原 Plan、Adjustment、Effective Plan 三层分别保存，basis 的继承表示来源，不自动成为修改后全部要求的语义证明。

下一步 Memory 需要提供可解析的稳定引用、实际 Parent→Candidate Skill 编辑、相关 Update／Check、执行条件与 Actor 协议、可追溯的真实行为变化、改善／退化／反例／不确定性，以及解释与观察的区分。多项共同编辑不得被包装成每一项编辑独立有效。具体 MemoryEntry Schema、生成、存储、检索和适用性机制尚未实现或在本次重新设计。

后续接入真实 Memory 时需要扩展引用解析与输入验证；当前 Prompt 已保持通用历史响应任务描述，不需要无历史专用版本。本次到此停止，未实现 Memory、Editor、Replay、Gate 或完整演化循环。
