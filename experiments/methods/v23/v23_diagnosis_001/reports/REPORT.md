# V23 Diagnosis 实现与验证报告

日期：2026-10-18。实验：`v23_diagnosis_001`。

Diagnosis 已完成共享输入装配、一次调用、解析校验、持久化及同输入复用。离线与回归共 **175 项测试、19 个子测试通过，0 失败、0 跳过**。唯一一次真实调用得到 **`revise`、4 项 Update、3 项 Check**，可以作为原始初稿交给后续 Preconditioner；其中仍有能力约束和事实措辞问题，未人工改写模型结果。

## 1. 文件与实现

相对仓库根目录：

| 文件 | 作用 |
|---|---|
| `src/skill_evolution/v23/diagnosis_prompt.md`（新增） | 英文任务说明、证据边界、既定输出协议；共享执行背景在运行时填入 |
| `src/skill_evolution/v23/diagnosis.py`（新增） | 输入、单次调用、严格结构和引用校验、存储、复用、下游读取与 CLI |
| `tests/skill_evolution/v23/test_diagnosis.py`（新增） | 73 项离线测试，包括实际历史 Grouping 交接 |
| `src/skill_evolution/v23/__init__.py` | 更新包说明 |
| `src/skill_evolution/v23/README.md`、`src/skill_evolution/README.md` | 用法、接口和模块状态 |
| `docs/methods/v23/DIAGNOSIS_DESIGN.md`、`docs/methods/v23/README.md` | 更新实现状态及报告链接，不改变设计契约 |
| `experiments/methods/v23/README.md`、`docs/04_EXPERIMENT_LOG.md` | 实验索引与记录 |
| 本实验 `config/`、`results/`、`reports/`、`README.md` | 冻结配置、实际输出、用量和人工语义核查 |

复用 Grouping 的 `live_generator()`、V22 的 JSON 解析器和现有原子 JSON 写入。没有修改 `facts.py`、Grouping 核心、ALFWorld Adapter 或其他演化算法；没有新增审核 Agent、自动修复调用或自然语言评分器。

## 2. 输入、输出与交接

`run_diagnosis()` → `load_grouping()` → `diagnosis_input()` → 单次请求。模型用户消息严格为：

```json
{"parent": null, "command_sets": {}, "runs": [], "grouping": {"groups": []}}
```

上面仅示意键；真实请求包含完整 93 步及所有菜单。此次 `parent` 确实为 `null`，没有用当前 Skill 文件替代历史事实。`sources`、轮次和路径仅保留在程序档案中。系统消息复用 Grouping 渲染后的 `[Execution context]`：真实基础系统指令、初始／历史输入模板、最近两组观察动作的能力说明和 50 步限制。执行背景按段提取，标记缺失会报错，不另写能力模板。

完整 `before → action → after`、菜单、反馈及 `P1:3 / P1:outcome / G1` 等引用保持原样。没有重新过滤命令或转换轨迹；精确过滤 `help`、环境合法性以及缺失菜单 `null` 的语义均继承已验证的共享事实。Grouping 的错误表述也原样传入，同时保留完整执行事实供模型核对。

输出固定为：

```text
decision: revise | no_change | need_evidence
reason: 非空字符串
plan: null，或 {goal, updates: [{id, text, basis}], checks: [{id, about, question}]}
```

只有 `revise` 使用非空 Plan，至少一个 Update；`checks` 可为空。程序检查精确字段、类型、ID 唯一性、引用存在性、组与成员证据关系、Check 的 Update 关联。`basis` 必须有直接执行来源，支持跨组引用，也允许不带组的直接执行依据。仅执行结构与引用检查，不用启发式判定策略好坏。

保存完整 `prompt.md / messages.json / request.json`、HTTP 原文、标准化响应、原始输出、解析结果、验证结果与运行信息。非法 JSON、截断、契约失败或技术错误均保留停点，不变成语义决定。复用比较完整输入、背景、Grouping、来源、轮次、提示词及响应与结果的一致性；无效或不一致目录拒绝复用，也不自动重试。

## 3. 离线验证

使用已有 Python 3.13 环境，未调用模型：

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q tests/skill_evolution/v23/test_diagnosis.py
# 73 passed

/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
# 175 passed, 19 subtests passed
```

覆盖三种决定、Plan 对应关系、空 checks、多组依据、非法／重复引用、重复 ID、多余字段、无 Skill／已有 Skill、错误 Grouping 与真实轨迹同时保留、失败结果归档、一次调用及复用、保存内容篡改拒绝、输入预算、HTTP 失败和真实交接。回归包括 58 项 Grouping、44 项 Adapter／V22 测试及 19 个子测试。

实际历史交接测试在本机运行通过，没有跳过：4 条执行、93 步、两个组、四个任务身份一致；P3:10 仍为 `go to shelf 4`，Grouping 中把它写到 P3:1–17 之后的错误文字未改写。没有重新运行环境或创建另一套轨迹转换器。[完整日志](../../../../../artifacts/methods/v23/v23_diagnosis_001/offline_tests.txt)。

## 4. 唯一一次真实调用

源分组：`artifacts/methods/v23/v23_grouping_001/live`，`train:0012–0015`。沿用该目录已有两个组，未调用 Grouping。

调用前保存[冻结配置](../config/plan.json)及[Prompt 快照](../config/diagnosis_prompt.md)。实际输入 82,874 字符，上限 100,000；`deepseek-flash`、`max_tokens=16384`、`reasoning_effort=medium`、thinking enabled、temperature 1、stream false、timeout 300 秒。正式端点为 `api.deepseek.com`，凭据不归档。

```bash
/tmp/gse-v23-py313/bin/python -m src.skill_evolution.v23.diagnosis \
  --grouping artifacts/methods/v23/v23_grouping_001/live \
  --output artifacts/methods/v23/v23_diagnosis_001/live \
  --model deepseek-flash --max-tokens 16384 --timeout 300 \
  --max-input-chars 100000
```

HTTP 调用 **1 次**，约 **44.33 秒**，`finish_reason=stop`，校验通过。输入 23,945 Token；输出 8,881 Token（含推理 7,707）；总计 **32,826 Token**，缓存命中 0。推理 Token 已包含于输出量，不重复相加。API 未返回货币账单金额，因此金额记为未知，不估造费用。请求、完整 HTTP 响应及 usage 已保存于[原始档案](../../../../../artifacts/methods/v23/v23_diagnosis_001/live/)。

### 实际输出与逐项核查

[完整原始 Diagnosis JSON](../results/diagnosis.json)与有效 `diagnosis.json` 逐字节一致，未修改。以下是人工核查，不是新增模型输出字段，也没有调用审核模型。

| 项目 | 事实依据及可落实部分 | 限制或偏差 |
|---|---|---|
| `reason / goal` | 正确识别无 Parent Skill，并以 P2 搜索重复、P3/P4 扩展位置及成功的取物→清洁→放置作为初稿依据 | 将 P2 问题直接称为 Skill-addressable 比证据更强；没有 Candidate 对照证明其成因。goal 已写入分解任务等具体手段，留给后续调整的空间稍窄 |
| `u1` 任务阶段与动作选择 | P1:1–3 支持开容器取物；P3:20、P4:7 支持取物；P4:5 确为菜单外／环境不合法动作且无效果。条件与动作方向基本可执行 | 菜单内选动作已是基础协议要求，这条兼有协议强化，不能视为已经证明的独立 Skill 缺陷。“当前 inventory”并非每步自动注入，需要现有观察、候选或显式查询支持 |
| `u2` 搜索 | P2 多次回到无目标的 sink/counter/cabinet，并重复 inventory，50 步耗尽；P3:19 转到 bathtubbasin 后发现目标、P3:20 取物；P4:6 转到另一炉位发现 kettle。真正使用了行为差异，而非只看成功标签 | `unchecked`、`remaining`、已检查完区域未限定为最近两步可识别的信息，隐含全局搜索历史。优先闭容器是合理候选策略，但本批没有比较证明它更优；尚未检查的容器不能统一断言为关闭 |
| `u3` 持物清洁 | P1:4–5、P3:21–22、P4:8–9 都支持持物前往 sink 并 clean，明确以清洁确认判断阶段完成，保留成功行为 | 本批均为 clean-and-place，没有验证无需清洁或已经清洁物体的边界；该规则不构成对所有任务的普遍证明 |
| `u4` 到达／打开／放置 | P4:10–12 直接支持关闭目的柜先开再放；P1:6–7、P3:23–24 支持开放表面直接放置，保留有效差异 | “move 后停止”仅在任务已完成时成立。样本中最终 move 后环境即 done，没有发生终止后的 Actor 请求，不能据此推断 Actor 主动停止能力或所有 move 都完成任务 |
| `c1` | 同时观察是否改变搜索位置、是否仍循环及预算，具有后续检查价值 | 继承 u2 的全局未检查条件；`just-emptied` 混淆“没有目标”与“被清空”。本批 sink/counter 常有其他物品 |
| `c2 / c3` | c2 观察成功阶段与关闭目的地处理的保持；c3 针对 P4:5 的不可用动作，分别关联实际 Update | c2 接近复述更新，但可作有效行为保持问题；c3 检验的是既有协议遵循，尚无执行验证 |

### 时间语义与能力边界

- **Grouping 时间错误**：实际 P3:10 已访问 shelf 4，P3:18 去 cart，P3:19 才去 bathtubbasin。输出引用 P3:19–20 支持发现／取物，没有复述错误先后顺序；但也没有明确纠正它，不能声称模型已显式识别并解释该错误。
- **初始状态**：P2 初始观察只列出 cabinet 名称；关闭状态在后续接近／操作中可见。输出笼统称许多未检查容器为 closed，仍超出了对未观察容器状态的直接支持。
- **“empty”的措辞**：P2:13/50 的 sink 有 tomato；counter 有多种物品。更准确的事实是“未发现目标且内容未变”，模型没有始终区分这两者。原始结果保留。
- **有限历史**：Actor 仅有当前观察、候选及最近两组行动前观察动作；没有全局 visited set。u2 未明确把未检查、剩余位置等条件限定到可见信息，因此不能判定该项完全可落实。提示词已经写明能力限制，本次不因这项缺陷改 Prompt 或重采样。
- **预算可见性**：历史模板包含已执行步数和当前步数，不能说 Actor 不知道当前步数；但 50 步上限在 Diagnosis 执行背景中，实际 Actor 基础模板没有该上限。u2 要求预留步骤，却没有说明总预算来源或具体保留规则。
- **跨任务泛化**：四条都是 clean-and-place；无需清洁的分支和优先闭容器的搜索收益尚未验证。不把合法结构或成功生成 Plan 当成自进化收益。

## 5. 复用与后续接口

真实结果完成后，使用一个“一旦被调用即抛错”的 generator 再次调用 `run_diagnosis()`：正常复用，**0 新增请求**。进一步逐字节比较 Diagnosis 全部文件、源 Grouping 全部文件，均未改变。实际请求与冻结参数、完整事实、分组和 Prompt 快照一致。见[复用核验](../../../../../artifacts/methods/v23/v23_diagnosis_001/reuse_validation.json)与[汇总](../results/summary.json)。

后续可直接读取：

```python
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.diagnosis import load_diagnosis

grouped = load_grouping("artifacts/methods/v23/v23_grouping_001/live")
saved = load_diagnosis("artifacts/methods/v23/v23_diagnosis_001/live",
                       expected_grouping=grouped)
raw_plan = saved["diagnosis"]["plan"]
# 同时提供 facts、background、grouping、sources、round_id；全部沿用原引用。
```

**可以正式交接原始 Plan 和证据，不能把它标记为语义问题已解决或效果已验证。** 当前真实验证仅覆盖 `parent=null`；已有 Skill 路径由离线测试覆盖。共享执行背景依赖 Grouping 的固定段落标记，未来调整该格式需要同步维护提取边界；未来修改 Prompt 后，旧结果需使用匹配版本读取。

本次到此停止：零新增 ALFWorld episode，未重跑 Grouping，未开发 Preconditioner、Memory、Editor、Replay 或 Gate，未启动完整演化实验。
