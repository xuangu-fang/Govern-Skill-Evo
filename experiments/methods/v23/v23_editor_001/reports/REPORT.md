# V23 Editor 实现与验证报告

日期：2026-10-18。Editor 已完成正式实现和离线回归：**384 项测试与 19 个子测试通过，其中 Editor 新增 100 项**。唯一一次真实模型请求返回了两字段 JSON 和非空 Patch，但补丁格式不合法，严格应用失败，**未生成 Candidate**。原始响应及费用记录完整保留，没有修复 Patch、重采样或运行环境。

工程层面已经具备创建、修改、删除、多 Hunk、严格坐标与换行处理、语义停点和零调用复用能力；这些由离线测试验证。本次真实调用不能作为“模型已生成可应用 Candidate”的成功证据。失败停点已按本次边界保留。

## 1. 实际文件变更

| 文件 | 作用 |
|---|---|
| [editor.py](../../../../../src/skill_evolution/v23/editor.py)（新增） | 上游读取、两字段输入、共享背景渲染、单次调用、严格 Patch 应用、Candidate／Diff 构造、持久化／复用和 CLI |
| [editor_prompt.md](../../../../../src/skill_evolution/v23/editor_prompt.md)（新增） | 用户提供的完整正式英文 Prompt，未追加针对三项 Update 的特殊规则 |
| [test_editor.py](../../../../../tests/skill_evolution/v23/test_editor.py)（新增） | 100 项 Editor 离线测试，包括真实上游档案只读交接 |
| [V23 README](../../../../../src/skill_evolution/v23/README.md)、[包说明](../../../../../src/skill_evolution/v23/__init__.py)、[实现索引](../../../../../src/skill_evolution/README.md) | 命令、接口、严格应用语法、保存／复用和下游交接 |
| [设计方案](../../../../../docs/methods/v23/EDITOR_DESIGN.md)、[方法索引](../../../../../docs/methods/v23/README.md) | 更新实现状态及验证入口，保留已确认的机制 |
| [实验索引](../../README.md)、[实验日志](../../../../../docs/04_EXPERIMENT_LOG.md) | 登记单次真实失败及停止边界 |
| 本实验 `README.md / config / results / reports` | 冻结源码、Prompt、配置、核查标准、原始输出副本、错误和报告 |
| [原始运行目录](../../../../../artifacts/methods/v23/v23_editor_001/) | 测试日志、输入／消息冻结、上游快照、完整 HTTP 请求与响应、停点 |

没有修改 Grouping、Diagnosis、Preconditioner、facts 或 ALFWorld Adapter 的核心实现。未实现 Replay、Memory、Gate 或完整演化循环。

## 2. 输入、Prompt 与输出契约

直接调用 `load_preconditioner()` 读取 `v23_preconditioner_001/live`，从 `saved['facts']['parent']` 取实际 Parent，从 `saved['effective_plan']` 取完整有效 Plan。只接受 `ready` 且非空 Plan，并重新核对它与 Preconditioner 确定性编译的结果一致。

模型数据严格为：

```json
{
  "parent": null,
  "plan": {
    "goal": "...",
    "updates": [],
    "checks": []
  }
}
```

这是结构示意；本次实际 Plan 有 3 项 Update 和 3 项 Check，完整输入见 [frozen_input.json](../../../../../artifacts/methods/v23/v23_editor_001/frozen_input.json)。模型消息不包含 runs、Grouping、原始 Diagnosis、Adjustments 或 Memory。basis 与 Checks 原样交接，程序不据此生成策略或自动插入 Skill 指令。

系统消息使用现有 `prompts.render_prompt()` 与唯一 `execution_context.md`，从保存的 background 装配真实能力、系统指令、初始／历史模板及步数上限。不存在新增能力声明或重新转换轨迹。

完整正式英文 Prompt 见 [冻结全文](../config/source/editor_prompt.md)，实际渲染全文见 [live/prompt.md](../../../../../artifacts/methods/v23/v23_editor_001/live/prompt.md)。Prompt 与调用时源码均已冻结，调用后未针对结果调整。

模型输出只有 `patch / reason`，reason 始终为非空字符串：

| patch | 程序处理 |
|---|---|
| 非空合法 Unified Diff | 全部 Hunk 精确应用后保存 Candidate |
| 精确 `""` | 合法无需编辑，保留 Parent，不创建 Candidate |
| null | 合法需要上游修订的停点，不创建 Candidate |
| 空白字符串、错误 Diff、不可应用 Diff、其他类型 | 技术失败，原始输出及错误保留 |

程序不从 reason 推断状态，不将应用失败转换成 null。`run.json.outcome` 和下游 `editor_status` 是程序派生状态，不是额外模型输出字段。

## 3. Patch 解析与严格应用

复用检查发现：V22 的相关代码生成文本 Diff，不负责应用；旧 V17 Editor 使用结构化编辑单元，且会自动补换行，不能满足本次准确文本与 Unified Diff 契约。因此新增一个限定单文件的应用函数，没有引入通用补丁框架或外部执行命令。

支持的格式是固定文件头后接一个或多个 Hunk：已有 Parent 使用 `a/SKILL.md → b/SKILL.md`，null Parent 使用 `/dev/null → b/SKILL.md`。允许标准省略计数的一行形式、零长度插入／删除范围及 Hunk 尾部说明。不接受 Git 元数据前缀、额外文件、其他路径、二进制格式或补丁外文本。

应用规则：

1. 旧坐标、行数、删除行和上下文逐字匹配准确 Parent；不搜索其他相似位置，不使用偏移或模糊匹配。
2. 多 Hunk 使用原文件坐标读取，新的声明坐标必须等于当前已构造结果的位置；拒绝重叠、倒序及计数不一致。
3. 仅按 LF 分行，保留空白、CR、CRLF 及 Unicode 字符。Patch 元数据采用 LF，正文的 CRLF 不转换。
4. 缺少文件末尾 LF 时使用标准无换行标记；标记必须与 Parent 原文相符，且生成结果不能在非末行出现无换行片段。不静默补换行、去空格或修正计数。
5. 全部应用在内存中完成；任何 Hunk 失败都不会发布部分 Candidate。
6. 结果必须非空白，且与准确 Parent 有实际文本变化。局部性和语义忠实不通过修改比例或自然语言评分器判定。

文本通过 UTF-8 字节保存／读取，避免通用换行转换。`patch.diff` 保留模型原文；`actual.diff` 由实际 Parent／Candidate 确定性计算，并补足 Diff 表达所需的无换行标记，不能用它修复模型 Patch。

复用现有 V23 模型调用、JSON 解析和原子 JSON 保存函数；文本文件也使用临时文件替换。JSON 解析沿用现有对单个 JSON 对象或完整 JSON 代码围栏的兼容，拒绝重复键；Prompt 仍明确要求只返回 JSON。

## 4. 离线测试及回归

在仓库根目录执行：

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

**384 passed, 19 subtests passed in 2.71s**；零失败、零跳过。Editor 新增 100 项，已有相关回归 284 项。完整日志见 [offline_tests.txt](../../../../../artifacts/methods/v23/v23_editor_001/offline_tests.txt)。

覆盖：null Parent 新增、已有 Parent 新增／替换／删除、多 Hunk 行数变化、重复文本准确位置、错误旧／新坐标、上下文和空白精确匹配、CRLF、Unicode 行分隔字符、缺少末尾换行及标记、不合法路径、重叠／逆序／截断／额外文件、部分应用失败、无变化／空白结果、三种合法分支、空白 Patch、多余字段、重复 JSON 键、真实上游读取、不自动写入 Checks、实际 Parent 字节保留、预算与配置约束、HTTP／网络／中断／JSON／Patch 失败保留、档案损坏拒绝和合法结果零调用复用。

离线测试明确不把自然语言可执行性当作程序判断：一段语义上不合理但格式合法的文本可通过文本应用测试，这不代表该指导可执行。

## 5. 唯一一次真实模型调用

复用已保存的 Preconditioner 合法 Keep；Parent=null，Effective Plan 为三项 Update／Check。上游四条执行仍为 train:0012–0015，但其轨迹不发送给 Editor。没有重新调用任何上游模块或运行 ALFWorld。

[请求前冻结的配置与标准](../config/plan.json)：

| 项目 | 实际值 |
|---|---|
| 模型／端点 | deepseek-flash / api.deepseek.com/chat/completions |
| temperature / thinking / reasoning_effort / stream | 1.0 / enabled / medium / false |
| 输出预算／超时 | 16,384 Token / 300 秒 |
| 实际输入／字符上限 | 11,005 / 100,000 字符 |
| 实际调用／自动重试 | 1 / 0 |
| finish_reason | stop，未截断 |
| 输入 Token | 2,147 |
| 输出 Token | 2,830，其中推理 2,403 |
| 总 Token | 4,977 |
| 耗时 | 11.030993 秒 |
| 金额 | API 未返回账单金额；未估算金额 |
| 应用结果 | invalid；未生成 Candidate |

完整请求、HTTP 原文、usage、模型输出、解析与错误位于 [live/](../../../../../artifacts/methods/v23/v23_editor_001/live/)，摘要见 [summary.json](../results/summary.json)。

模型实际输出如下，仅作失败提案记录，不是可执行 Candidate：

```json
{
  "patch": "--- /dev/null\n+++ b/SKILL.md\n@@ -0,0 +1,22 @@\n+# ALFRED Skill\n+\n+## Efficient target search\n+- When locating a target object, do not repeatedly cycle among the same few locations.\n+- After checking a location and observing that the target is absent—including after opening a container whose visible contents lack the target—prefer an unchecked admissible location over returning to a previously checked one.\n+- Use a deterministic forward sweep through location names or numbers and across genuinely different receptacle and surface types. Include outlying or non-kitchen receptacles when present, and check such sites before revisiting checked sites.\n+- At minimum, avoid choosing a location that appears in the immediately preceding observations or actions when another admissible unexamined location exists, unless a new observation indicates the target may now be there.\n+\n+## Clean-and-place order\n+For clean-and-place tasks, follow this dependency order:\n+1. Locate and acquire the requested target object.\n+2. If the target's source container is closed, open it before taking the object.\n+3. Go to an appropriate cleaning fixture, such as a sinkbasin when available, and clean the held target.\n+4. Go to the requested destination.\n+5. If the destination container is closed, open it before placing.\n+6. Move or place the cleaned target into or onto the destination.\n+\n+Verify that the acquired object matches the requested target. Do not substitute an unrelated object.\n+\n+## Admissible actions only\n+- Only select actions that appear in the current admissible action list.\n+- If an intended location or action is absent, do not issue it and expect progress. Instead, choose an available alternative, such as another listed location or a currently available examine/open action, and continue the plan from there.\n+",
  "reason": "Created the initial Skill with efficient target-search guidance, clean-and-place dependency ordering, and admissible-action constraints implementing all effective Updates."
}
```

技术失败定位：文件头正确，Hunk 声明 `@@ -0,0 +1,22 @@`。前 22 条新增行读完后，仍剩第 23 条正文记录，即文件最后的单个 `+`。这一行没有 LF，也没有标准无末尾换行标记。完整 Patch 因而包含 Hunk 之外的非法内容。应用器返回：

```text
Invalid hunk header or unexpected patch content
```

[行数核查记录](../results/patch_audit.json) 和 [原始 Patch](../results/patch.diff) 保留准确文本。程序没有将 22 改成 23，没有删除最后一个 `+`，也没有补换行。解析成功但应用失败，因此保存 `parsed.json / patch.diff / validation.json`，不保存有效 `editor.json`，不创建 `candidate.md / actual.diff`。

## 6. 对补丁提案的语义核查

没有成功生成 Candidate，以下只核查模型 Patch 中拟新增的文本，不视为应用通过或收益验证。

| 内容 | 核查结果 |
|---|---|
| 联合处理 Updates | 拟新增搜索、清洁交付和动作候选三个部分，对应 u1/u2/u3；没有另外修改 Checks 或引入轨迹编号。reason 声称落实全部要求，但这不是程序已证明的事实。 |
| u1 搜索条件与范围 | 保留避免循环、目标缺失后优先未检查位置、确定性扫描、扩大容器类型及最近历史中的回访例外，整体接近原要求。仍依赖全局 unchecked／previously checked 判断；没有说明仅凭最近两步如何可靠判定，也没有将这一潜在阻碍返回上游。直接抄入条件并不能证明 Actor 能执行它。 |
| u1 是否偷偷替换策略 | 未明显用“只避开最近两步”替代整个原要求，而是保留全局要求和最低限度条款。因此主要问题是可执行性矛盾未处理，不能简单声称已经完成忠实且可执行的实现。 |
| u2 依赖顺序 | 保留清洁先于交付、目的容器必要时先开、目标身份核对和禁止替代物。可是把“取得目标”编号为第 1 步，把“源容器关闭时先开再取”编号为第 2 步，并要求按该顺序执行，产生顺序表达冲突。原 Update 有明确的 before taking 条件，编辑后的编号使这个条件更难一致解释。 |
| u3 基础协议重复 | “Only select actions…”再次重复 Actor 模板已要求的 admissible action 约束。后半的选择可用替代动作是具体恢复指导，有区别于基础协议的内容；模型没有消除前半重复。不能据此把整个 u3 都认作无用。 |
| 保留无关能力 | 本次 Parent=null，没有已有文本可供保留，不能由这次调用验证模型对现有 Skill 的局部修改能力。该能力的文本应用部分由离线测试覆盖。 |
| 新增无关内容／Checks | 没有发现把 Check 问题另行写成指令、加入当前任务答案、执行引用或性能保证。标题与章节是正常组织文字。 |
| null／空 Patch 分支 | 本次未返回这两个分支；其结构与保存语义仅经离线验证。不得把无效 Patch 重新解释为其中任一结果。 |

本次未修改 Prompt、原始 Patch、Plan 或参数，也没有根据这些语义问题重新采样。结构正确不证明语义正确；此处结构应用本身已经失败，不能宣称 Editor 已成功落实本轮 Plan。

## 7. 持久化、复用与下游交接

保存 `upstream.json`（程序侧完整来源）、`input.json`（模型两字段）、`background.json`、渲染 Prompt、messages、请求配置、HTTP 原文、响应 usage、解析、Patch、验证和运行信息。旧 Grouping／Diagnosis／Preconditioner 档案与调用前快照逐字节相同，源码与 Prompt 冻结快照一致。

离线已验证三个合法结果在同输入、Prompt、配置下零新增调用复用。**本次真实失败目录不可作为有效结果复用**：再次以禁止请求的 generator 进入时被拒绝，文件未改变，新增调用为零。不会隐式修复或重试。

下游接口：

```python
from src.skill_evolution.v23.editor import load_editor
saved = load_editor("path/to/a/valid/editor/result")
model_output = saved["editor"]
candidate_text = saved["candidate_text"]
actual_diff = saved["actual_diff"]
```

有效 Candidate 分支提供完整正文、实际 Diff、Effective Plan、Parent、执行背景和来源；合法空 Patch／null 分支返回 `candidate_text=None`，不提供新 Candidate。调用方可通过 `expected_preconditioner` 与 `expected_call_config` 核对期望身份和配置，读取时重新应用并比对结果。

**本次 `v23_editor_001/live` 是 invalid 停点，`load_editor()` 会拒绝读取为有效结果，Candidate Replay 没有可直接执行的新 Skill。** 只有原始提案、错误和来源可用于分析。

本次按一次调用边界停止。未运行 Replay、Memory、Gate 或完整 Skill 自进化，也未产生 Candidate 执行轨迹。后续如需新的真实生成，应另行授权并保存为独立实验，不覆盖本次失败记录。
