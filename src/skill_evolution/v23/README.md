# V23 Grouping、Diagnosis、Preconditioner、Editor、Replay／Memory 与 Gate

[设计规格](../../../docs/methods/v23/AUTOMATIC_GROUPING_DESIGN.md) · [实现验证报告](../../../experiments/methods/v23/v23_grouping_001/reports/REPORT.md)

实现 Grouping、Diagnosis、Preconditioner、Editor、Replay 与 Memory 维护；各模型模块不自行执行 Actor 环境任务。配对任务执行通过既有 ALFWorld Adapter 单独开展。依赖 Python、requests、python-dotenv；离线测试使用 pytest。Grouping 当前适配 V22 ALFWorld 原始 `trajectory.json`，根据记录中的协议重建并精确比较实际 Actor 请求，不读取当前默认模板替代历史配置。

| 文件 | 职责 |
|---|---|
| `facts.py` | 共享事实装配、Parent 与背景一致性、实际 Prompt 核验、before／after 转换、环境合法性保留及来源审计 |
| `grouping_prompt.md` | 设计文档中的正式英文提示词，测试保证全文一致 |
| `grouping.py` | 一次调用、解析与校验、保存、精确输入复用、Diagnosis 读取和 Candidate 归组映射、CLI |
| `diagnosis_prompt.md` | 简洁英文 Diagnosis 任务说明及既定 Plan 输出协议 |
| `execution_context.md`、`prompts.py` | 唯一共享执行背景模板与装配；旧档案显式只读兼容 |
| `preconditioner_prompt.md` | 通用英文增量调整提示词，共用 Execution Context；无无历史专用分支 |
| `editor_prompt.md` | 用户确认的正式英文 Editor Prompt，共用实际执行背景 |
| `editor.py` | 两字段交接、单次调用、严格 Unified Diff 应用、Candidate 构造与持久化复用 |
| `preconditioner.py` | 整条引用执行装配、一次调用、Adjustment 校验、Effective Plan 确定性编译、保存和下游读取 |
| `replay.py`、`replay_prompt.md` | 配对事实构造、一次响应学习、三字段提案校验与持久化复用 |
| `memory.py` | 不可变 Archive、原子 Active、跨轮引用与完整来源视图 |
| `diagnosis.py` | 读取已完成 Grouping、复用事实和执行背景、一次调用、结构引用校验、原始 Plan 保存及下游读取 |

## 使用

从仓库根目录执行，记录路径显式给出，不自动选择轨迹或运行环境：

```bash
python -m src.skill_evolution.v23.grouping \
  --records /path/to/parent1/trajectory.json /path/to/parent2/trajectory.json \
  --output artifacts/methods/v23/example_grouping \
  --round-id example_grouping \
  --model deepseek-flash --max-tokens 8192 --timeout 180
```

模型名按下表选择；凭据来自环境变量或 `--env-file` 指定文件中的 `OPENAI_API_KEY`、`OPENAI_BASE_URL`。不归档凭据。一次 HTTP 请求，无传输或语义自动重试；HTTP 原始响应、输出截断和无效 JSON 均保留。默认序列化输入上限为 400000 个字符，可用 `--max-input-chars` 下调，字符预算不是 Token 数。

### V23 / V23.2 端点路由

| `OPENAI_BASE_URL` | Actor（Parent / Candidate）及所有进化模块 |
|---|---|
| `http://llm-proxy.intra.xiaojukeji.com` | `deepseek-v4.1-flash` |
| `https://api.deepseek.com` | `deepseek-flash` |

两种端点支持尾部 `/` 和 `/v1`，优先采用端点对应的模型，即使模板或 `--model` 仍写着旧模型。已知端点下 CLI 可省略 `--model`；其他端点仍须提供模型。此规则只用于 V23 / V23.2，V22 保持原行为。Thinking、temperature、reasoning_effort、输出预算、超时和重试预算保持原值。

`evolution.run_campaign(..., config=...)` 对新的真实 Campaign 读取仓库 `.env`，统一解析 Actor、默认模块及 `stage_configs`，然后冻结实际生效配置；`local_validation.run_stage()` 对新的 V23.2 真实调用执行同样的解析，并将实际配置写入每次尝试的 `run.json`。外部已导出的环境变量仍优先于 `.env`；切换时应同时切换地址与对应凭据。纯离线注入的 generator / Actor 不读取端点路由。底层 `initialize()` 只冻结传入配置，单独使用时可先调用 `evolution.configuration_from_environment(config)`。

切换端点后使用新的 Campaign / 输出目录。已有 Campaign、历史报告和响应不重写；续跑前检查环境与冻结配置一致，防止混用模型。旧实验脚本的源码冻结检查仍生效，不能直接把旧实验当成新模型实验续跑。

只转换而不调用模型时，增加 `--convert-only`，输出到独立的新目录。转换目录不是已完成的分组，不能当作有效结果复用。

正常调用保存 `input.json`、`prompt.md`、`messages.json`、`request.json`、`http_response.txt`、`http_status.json`、`response.json`、`raw_output.txt`、`validation.json`、`run.json`；成功解析后保存 `parsed.json`，只有有效输出才保存 `grouping.json`。网络未返回时不会伪造 HTTP 响应文件。

再次使用已有分组目录时，比较轮次、完整事实／背景／来源、实际提示词及调用配置，并重新校验原始响应与结果。只有全部一致且原结果有效时直接复用，不再调用模型。使用 JSON 内容比较，不使用哈希。失败或未完成目录不能静默重试。

## 下游读取

```python
from src.skill_evolution.v23.grouping import load_grouping, candidate_groups

saved = load_grouping("artifacts/methods/v23/example_grouping", round_id="example_grouping")
# Diagnosis 可读取 saved['facts']、saved['background'] 和 saved['grouping']。
# sources 为程序侧执行／任务对应关系，不整体发送给模型。
by_task = candidate_groups(saved, ["train:0012", "train:0013"])
```

正常续行可通过 `run_grouping` 比较当前记录装配出的完整输入，或向 `load_grouping` 传入 `expected_bundle`。`candidate_groups` 只按任务身份继承 Parent 分组，不读取 Candidate 结果。

技术中断记录若保留初始状态和实际请求，可转换已经完成的动作；最后一个未执行请求只在程序侧记录，并保留未知结果，不制造执行事件。初始记录缺失、历史能力不同、Prompt 不可重建或事实冲突时拒绝转换。是否把不完整记录送入一轮学习由调用方运行协议决定。

## 验证

```bash
python -m pytest -q tests/skill_evolution/v23 tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
python -m scripts.analysis.v23.validate_grouping_history \
  --records /path/to/parent1/trajectory.json /path/to/parent2/trajectory.json \
  --output artifacts/methods/v23/example_history_audit
```

引用校验支持 `P1:3`、`P1:3-P1:5`、`P1:3–5` 等显式步骤引用，检查每个成员的步骤定位及所有可识别的执行、菜单、组引用。它不证明引用文字的事实解释正确。真实测试的原始结果包含已明确记录的语义问题，见报告。

## Diagnosis

[设计规格](../../../docs/methods/v23/DIAGNOSIS_DESIGN.md) · [实现验证报告](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md)

```bash
python -m src.skill_evolution.v23.diagnosis \
  --grouping artifacts/methods/v23/example_grouping \
  --output artifacts/methods/v23/example_diagnosis \
  --model deepseek-flash --max-tokens 16384 --timeout 300 \
  --max-input-chars 100000
```

直接调用 `load_grouping()`，模型数据只含完整的 `parent / command_sets / runs / grouping`。Grouping 和 Diagnosis 均调用 `prompts.render_prompt()`，将唯一的 `execution_context.md` 模板装配为 `{{execution_context}}`。实际 Actor 协议与上限来自本批保存的 background，单次替换保留原模板原文及占位符；当前 Diagnosis 不再截取 Grouping 标题段落。没有第二套能力说明、转换器或编号。Grouping 的分析文字原样保留，由模型对照完整事实判断。

输出固定为 `decision / reason / plan`；`revise` 的 Plan 仅有 `goal / updates / checks`，另两种决定为 `plan=null`。Update 仅有 `id / text / basis`，Check 仅有 `id / update_ids / question`。`basis` 接受实际组、执行、初始状态、步骤和 outcome 引用，数组中使用独立引用而不是范围；至少含一个直接执行来源，每个显式引用的组须有其成员的执行依据。允许跨组更新、仅执行依据和空 checks。程序检查字段、类型、ID 和引用，不判定自然语言策略的正确性。

一次 HTTP 请求复用 Grouping 的调用函数，默认最多 16,384 个输出 Token，不重试。保存 Grouping 交接快照 `input.json`（含程序侧来源）、完整 `prompt.md / messages.json / request.json`、HTTP 原文、`response.json / raw_output.txt`、`validation.json / run.json`；成功解析后保存 `parsed.json`，只有契约通过才保存 `diagnosis.json`。截断或非法输出保留原文，不转成 `need_evidence`。API Token 和推理 Token 位于响应 usage，未返回的费用不推测。

已有输出目录只能复用，不能隐式重跑。比较事实、背景、Grouping、来源、轮次、当前提示词、调用配置和保存的原始响应；差异或无效结果会报错。新调用在 `run.json.call_config` 保存模型、端点、输出预算、timeout、temperature、reasoning_effort、thinking 和 stream；任一声明配置变化均拒绝复用，不自动重新采样。CLI 复用时仍提供同一 `--model`、端点及预算，不需要 API key。程序注入的 generator 可携带 `call_config` 属性，或向 `run_grouping/run_diagnosis` 显式传入 `call_config`；只读 `load_*` 可用 `expected_call_config` 核对期望配置。旧结果与新 Prompt 不会自动混用。

```python
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.diagnosis import load_diagnosis

grouped = load_grouping("artifacts/methods/v23/example_grouping")
saved = load_diagnosis("artifacts/methods/v23/example_diagnosis",
                       expected_grouping=grouped)
initial_plan = saved["diagnosis"]["plan"]  # 语义停点时为 None
# 同时提供 facts、background、grouping、sources、round_id。
```

该接口供后续 Preconditioner 读取原始初稿及其证据，不读取历史 Memory、不编辑 Skill、不运行 Candidate。

## 历史档案的只读交接

默认 `load_grouping()`、`load_diagnosis()` 按当前 Prompt 严格校验，旧 Prompt 的目录会被拒绝。需要读取旧结果时，显式传入可信的历史冻结模板，不从结果文件自动猜测协议或放宽校验：

```python
from pathlib import Path
from src.skill_evolution.v23.grouping import load_grouping
from src.skill_evolution.v23.diagnosis import load_diagnosis

before = Path("experiments/methods/v23/v23_prompt_alignment_001/config/before")
legacy = {name: (before / f"{name}_prompt.md").read_text()
          for name in ("grouping", "diagnosis")}
grouped = load_grouping("artifacts/methods/v23/v23_grouping_001/live",
                        legacy_template=legacy["grouping"])
saved = load_diagnosis("artifacts/methods/v23/v23_diagnosis_001/live",
                       expected_grouping=grouped, legacy_templates=legacy)
# saved['diagnosis'] 的 Check 只含 update_ids；磁盘上的旧 about 原文未改动。
```

兼容入口先核对历史模板渲染出的完整 messages、事实、原始响应和旧 `about` 契约，再对返回副本转换字段，并按新契约复核。只有显式历史读取使用冻结旧模板的原段落结构；当前两个模块均使用共用背景函数。新模型若输出 `about` 或混用两个字段会失败，失败原文照常保留。`run_grouping/run_diagnosis` 不接受历史模板参数，不能把旧生成结果伪装成新 Prompt 的结果。Preconditioner 的 `legacy_templates` 只控制上游档案读取。新 Preconditioner 调用始终使用当前正式 Prompt；旧无历史 Preconditioner 产物由 `load_preconditioner()` 使用既有冻结 Prompt 只读验证。

[Prompt 统一与验证报告](../../../experiments/methods/v23/v23_prompt_alignment_001/reports/REPORT.md)包含新旧 Prompt 全文快照、差异及单次配对验证。


## Preconditioner

[设计规格](../../../docs/methods/v23/PRECONDITIONER_DESIGN.md) · [无历史实现验证](../../../experiments/methods/v23/v23_preconditioner_001/reports/REPORT.md)

```bash
python -m src.skill_evolution.v23.preconditioner \
  --grouping artifacts/methods/v23/v23_prompt_alignment_001/grouping \
  --diagnosis artifacts/methods/v23/v23_prompt_alignment_001/diagnosis \
  --output artifacts/methods/v23/example_preconditioner \
  --model deepseek-flash --max-tokens 16384 --timeout 300 \
  --max-input-chars 100000
```

`read_upstream()` 依次调用 `load_grouping()`、`load_diagnosis(expected_grouping=...)`；只有 `revise` Plan 可以进入。`preconditioner_input()` 根据原 Plan 中的执行引用选择完整执行（包含 Goal／Update／Check 文本引用），保持原编号和轨迹不变；提供显式引用的 Group 及所选执行所属的 Group，不根据 Group 成员进一步展开执行。动作菜单只保留这些完整执行实际引用的菜单，值、顺序和重复项不变。`parent` 来自已核验的历史 Diagnosis，模型数据仅有 `parent / plan / command_sets / runs / grouping / memory` 六字段。新运行使用 `memory: {entries, sources}`，默认空对象视图；非空视图由 `load_memory()` 装配并验证。原始 `memory=[]` 档案只读兼容，不回写历史请求。

`compile_effective_plan(result, payload)` 验证四字段输出、Adjustment 与最终 Checks，并同时应用于原 Plan。新 Update 插入其来源最早位置，拆分按 `to` 顺序，其他 Update 保持原相对顺序；Goal 不变。basis 按来源 Update 在原 Plan 中的顺序去重继承；Adjustment 自己的依据只保存在 Adjustment。Keep 保留全部原文，合并／拆分／撤下造成旧 Check 引用失效时拒绝输出，不猜测迁移。程序只检查确定性结构和来源，不证明自然语言策略有效。

`ready` 返回至少一项 Update 的 Effective Plan；`no_change` 必须显式撤下全部原 Update 且 `checks=[]`；`need_evidence` 必须 `adjustments=[] / checks=null`。两个语义停点均保存 `effective_plan.json` 为 JSON null，交接时停止继续编辑，不将技术失败转换成语义决定。

保存完整上游快照 `input.json`（程序侧含来源）、模型实际六字段数据 `messages.json`、渲染 Prompt、原始请求／响应／Token、解析、验证和运行信息。仅合法输出保存 `preconditioner.json / effective_plan.json`；解析成功但契约失败仍保存 `parsed.json`。调用复用 Grouping 的单次 HTTP 路线；失败目录不能隐式重试。复用检查完整上游交接、Prompt、配置、原始响应和重新编译的 Effective Plan；同条件零新增调用。

```python
from src.skill_evolution.v23.preconditioner import load_preconditioner

saved = load_preconditioner("artifacts/methods/v23/example_preconditioner")
original_plan = saved["diagnosis"]["plan"]
adjustments = saved["preconditioner"]["adjustments"]
effective_plan = saved["effective_plan"]  # 两种语义停点均为 None
# 同时返回 facts / background / grouping / sources / round_id。
```

需要显式核对交接或配置时，使用 `expected_diagnosis`、`expected_call_config`。旧 Diagnosis 输入可通过 `read_upstream(..., legacy_templates=legacy)` 或 `run_preconditioner(..., legacy_templates=legacy)` 走上述既有只读兼容；新 Preconditioner 输出不接受 `about`。

后续可读取原始 Plan、Adjustment 和 Effective Plan 三者追溯来源。历史 Memory 读取现已接入；同批真实对照验证了消费与更新构造，但未验证新 Effective Plan 的行为收益。


## Editor

[设计规格](../../../docs/methods/v23/EDITOR_DESIGN.md) · [实现验证报告](../../../experiments/methods/v23/v23_editor_001/reports/REPORT.md)

```bash
python -m src.skill_evolution.v23.editor \
  --preconditioner artifacts/methods/v23/v23_preconditioner_001/live \
  --output artifacts/methods/v23/example_editor \
  --model deepseek-flash --max-tokens 16384 --timeout 300 \
  --max-input-chars 100000
```

`run_editor()` 直接读取并校验保存的 Preconditioner；仅 `ready` 且 `effective_plan` 非空时进入。模型数据只有 `parent / plan`，完整 Effective Plan（含 basis、Checks）原样交接，不发送轨迹、Grouping、Memory 或 Adjustments。系统消息仍使用唯一的共享背景模板和真实 `background`。程序侧 `upstream.json` 保存完整来源快照，`input.json` 是模型实际两字段输入，`background.json` 是本轮真实执行背景。

模型输出严格为 `patch / reason`，reason 始终为非空字符串。非空 Diff 严格应用后生成 Candidate；精确空字符串保存无需编辑结果；null 保存需要上游修订的停点。后两者不创建 Candidate。空白字符串、错误 JSON、截断或无法应用的补丁属于技术失败，不转换成语义停点，不解析 reason 来推断状态。

`apply_patch(parent, patch)` 仅接受一个文件的标准 Unified Diff：已有 Parent 使用 `--- a/SKILL.md / +++ b/SKILL.md`，null Parent 使用 `--- /dev/null / +++ b/SKILL.md`；随后为一个或多个 Hunk。支持省略计数时的一行、零长度插入／删除范围及 Hunk 尾部说明。不接受其他路径、额外文件、Git 元数据前缀、二进制补丁或补丁外说明。

每个 Hunk 的旧坐标、旧行数与上下文／删除原文必须精确匹配，新的声明坐标也必须与已构造结果一致；拒绝重叠或逆序 Hunk，不做偏移搜索或模糊匹配。多 Hunk 统一按原文件坐标读取，新增行数只影响结果坐标。文本仅按 LF 划分，不把 CR 或 Unicode 行分隔字符静默转换；Patch 元数据使用 LF，正文中的 CRLF 原样保留。无末尾 LF 使用标准 `\ No newline at end of file` 标记，必须与旧文件匹配且不能在结果中形成非末行的无换行片段。文本保存和读取使用 UTF-8 字节，避免通用换行转换。

全部 Hunk 在内存中成功应用且结果非空白、与 Parent 确有变化后才保存 `candidate.md`。`patch.diff` 保留模型原文；`actual.diff` 由准确 Parent／Candidate 计算，包含必要的无换行标记，不覆盖模型 Patch。局部性与语义忠实由 Prompt 和人工核查约束，程序不设置修改比例阈值或自然语言评分器。

保存完整 `messages.json / prompt.md / request.json`、HTTP 原文、`response.json / raw_output.txt`、`parsed.json`、原 Patch、`validation.json / run.json`。有效输出保存 `editor.json`；仅 Candidate 分支保存 `candidate.md / actual.diff`。`run.json.outcome` 是程序派生的 `candidate / no_change / needs_revision`，不是新增模型输出字段。技术失败保留错误，目录不会隐式重试。

```python
from src.skill_evolution.v23.editor import load_editor
saved = load_editor("artifacts/methods/v23/example_editor")
model_result = saved["editor"]  # 仅 patch / reason
candidate = saved["candidate_text"]  # 两种合法停点为 None
actual_diff = saved["actual_diff"]  # 未生成 Candidate 时为 None
# 保留 effective_plan、facts、background、sources 等原有程序侧来源。
```

`load_editor()` 重建两字段输入和 Prompt、核对响应与结果，并重新应用 Patch 验证 Candidate 与实际 Diff。`expected_preconditioner / expected_call_config` 可核对指定交接与配置。`run_editor()` 在同输入、同 Prompt、同配置下复用已完成有效结果，零新增请求；条件变化、保存结果损坏或失败目录会拒绝复用。下游只有在 `candidate_text` 非空时才有新 Candidate 可读取；本模块不运行 Replay，不证明更新收益。


## Replay 与 Memory

正式契约见 [设计方案](../../../docs/methods/v23/REPLAY_MEMORY_DESIGN.md)。`replay_prompt.md` 为用户确认的完整英文 Prompt，使用现有 `prompts.render_prompt()` 与共享 Actor 背景。`replay.py` 只做响应学习，`memory.py` 只做确定性维护，不包含 Gate 或新的环境执行器。

```python
import json
from pathlib import Path
from src.skill_evolution.v23.replay import build_replay, run_replay, load_replay
from src.skill_evolution.v23.memory import empty_memory, load_memory, commit_memory

# records 均为已经保存的真实 ALFWorld trajectory.json 内容。
# 复用完整 Parent 批次；Candidate 独立记录，函数按任务身份核验配对。
bundle = build_replay(editor_directory, parent_records, candidate_records,
                      memory=load_memory(memory_directory))
saved = run_replay(bundle, replay_directory, generate=generate,
                   call_config=call_config, max_input_chars=300000)
commit = commit_memory(memory_directory,
                       context_id="experiment_unique_R1",
                       context=bundle, result=saved["replay"])
view = load_memory(memory_directory)
```

模型输入只有 `parent / diff / plan / command_sets / runs / pairs / memory`；Plan 只读视图保留 goal、Update id/text、Checks。build_replay 的返回值另外保存背景、来源和 Candidate，用于程序核验，不全部发给模型。模型输出只有 `entries: [{revises, knowledge, evidence}]`；空数组合法，调用／JSON／契约错误不会改写成空数组。

两侧各调用现有 facts.build_facts()，不实现另一套轨迹转换器。Parent 引用保持 P；Candidate 改为 Q，按任务身份显式配对；双方菜单按完整有序值共享去重。菜单仍只排除精确 `help`，原始环境合法性保留。初始状态、协议、模型路由、环境内容、版本、Skill 和实际 Diff 都校验。不比较中间状态必须相同，也不把技术中断当作普通失败。

若 Actor 源码文件哈希不同，默认拒绝；只有提供匹配双方具体文件版本的 `implementation_review`（`parent_files / candidate_files / reason / diff`）才允许继续。该记录须来自实际源码核对，不能仅填写“可比较”跳过审计。实际每步 Prompt 仍须通过 facts.py 核验。本次已记录仅访问标签、入口路径、记录方式和等价 Prompt 提取差异。

`memory.py` 的长期条目为 `id / context_id / revises / knowledge / evidence`。Archive 按轮保存在 `archive/<context_id>.json`，内含不可变条目和完整来源；`active.json` 的 active_ids 与 commits 一次原子切换。采用文件锁串行提交，不增加数据库事务层。中断提交在切换索引前不可见，必须用相同输入恢复；已提交轮次再次提交严格核对输入和输出并返回原记录，不分配重复 M ID。

`load_memory()` 读取全部 Active 条目，每条只向模型提供 id、knowledge、evidence。步骤级历史引用展开对应完整执行及其菜单；编辑引用展开历史 Parent、Diff、Actor 背景与配置；来源按上下文／执行去重。不沿 revises 读取所有旧版本，不自动展开其他任务，不摘要或截断。缺失引用报错。

非空 Memory 交给 Preconditioner：

```python
from src.skill_evolution.v23.preconditioner import run_preconditioner
saved = run_preconditioner(grouping_directory, diagnosis_directory, output_directory,
                           generate=generate, call_config=call_config,
                           memory=view, max_input_chars=300000)
```

CLI 同样支持 `python -m src.skill_evolution.v23.preconditioner ... --memory /path/to/memory`。新请求统一使用对象，`load_preconditioner()` 对既有无历史档案使用已归档的原 Prompt 校验；不将旧结果误用于新 Prompt／Memory 请求。历史 M ID 可进入 Adjustment basis，原 Update basis 的继承和 Effective Plan 编译规则不变。

真实结果见 [Replay／Memory 报告](../../../experiments/methods/v23/v23_replay_memory_001/reports/REPORT.md) 和 [Memory 对照报告](../../../experiments/methods/v23/v23_preconditioner_with_memory_001/reports/REPORT.md)。固定预算启动脚本随实验归档，只允许各阶段一次实际执行，不能用来自动重试失败。当前已完成 4 个 Candidate、1 次 Replay、2 次 Preconditioner，后续不继续调用。

## Gate：确定性晋级决定

[设计](../../../docs/methods/v23/GATE_DESIGN.md) · [真实档案验证](../../../experiments/methods/v23/v23_gate_001/reports/REPORT.md)

`gate.py` 只比较完整核验批次的环境成功数量，Candidate 严格更多才 ACCEPT，否则 RETAIN。`replay.verify_pair()` 共用既有配置/任务/初始状态核验，`facts.build_facts()` 验证原始执行和终止反馈。未知结果或技术中断保留停点，不计为失败。

```python
from src.skill_evolution.v23.gate import run_gate, load_gate
saved = run_gate(
    'artifacts/methods/v23/v23_replay_memory_001/replay',
    'experiments/methods/v23/v23_gate_001/config/tasks.json',
    'artifacts/methods/v23/v23_gate_001/live',
)
result = load_gate('artifacts/methods/v23/v23_gate_001/live')['result']
# decision, parent_success, candidate_success, compared
```

同来源、输入和规则复用时不再次调用判定入口，仍核验来源与保存结果。`build_gate()` 为独立配对批次提供原始轨迹装配，`decide_gate()` 为已核验结果提供纯函数。Gate 不改 Skill 或 Memory，不向 Replay 输入或 MemoryEntry 增加字段。当前四组 Train 工程验证为 Parent 3 / Candidate 2，RETAIN；不代表独立 Validation。

## 统一轮次调度

`evolution.py` 串联现有模块，提供 `run_round`、`resume_round`、`run_campaign` 和只读 `status`。契约见[实现说明](../../../docs/methods/v23/EVOLUTION_DESIGN.md)。

```bash
python -m src.skill_evolution.v23.evolution run --campaign <path> --config <json>
python -m src.skill_evolution.v23.evolution resume --campaign <path>
python -m src.skill_evolution.v23.evolution status --campaign <path>
```

首次从 null Parent、空 Memory 开始。每轮冻结真实输入，模型阶段最多三次技术尝试，Actor 单步三次请求；耗尽停止，只有用户显式 resume 才开启恢复预算。合法语义结果不重采样。Memory 在轮次独立目录准备，唯一 state.json 原子发布下一轮 Skill 与 Memory。Gate 和 Replay 使用同批 Train 配对，独立 Test 不进入演化。配置和源码/Prompt 内容直接核对，不新增哈希体系。当前验证见 [v23_evolution_001](../../../experiments/methods/v23/v23_evolution_001/README.md)。

### 正式六轮数据准备

[ALFWorld 正式准备](../../../experiments/methods/v23/v23_alfworld_formal_001/README.md)提供 57 条优化任务和 134 条 Test。`optimization_splits=["train","val"]` 显式启用 Selection 优化身份，仍禁止 Test；`task_items` 保留公开 ID。新增只读 `evolution.final_parent(campaign)` 返回完成全部轮次后正式保留的 Skill 路径或 None。最终 Test 命令生成器复用现有 `run_task_skill`，不使用最后一个 Candidate 代替正式 Parent。本次未启动实验。
