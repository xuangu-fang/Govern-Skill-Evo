# V26 七模块调用、恢复与 Campaign

实现日期：2026-10-29。基于[冻结继承范围](INHERITANCE_SCOPE.md)、[事实与证据层](FACTS_EVIDENCE.md)、[OfficeQA Prompt](PROMPT_MIGRATION.md)接通训练主循环。验收仅使用合成数据、固定响应和故障注入，没有调用真实模型、运行真实题目 rollout 或启动实验。

## 方法版本和控制语义

继续使用 Diagnosis v5、Preconditioner v7、Replay Prompt v4 的已适配正文，没有改用 Preconditioner v8，也没有修改七份 Prompt。Replay 的 OfficeQA 输入视图仍是 `v26_officeqa_pairs_formal_v1`：参考 V25 输入视图 v4 的配对和权限边界，保留完整正式消息与工具观察；不迁入 SpreadsheetBench 程序代码去重；当前使用 OfficeQA 专用无损输入视图 v2，处理重复历史、共享初始内容和局部引用，保持配对与证据权限。

这里要区分两个近似名称：Diagnosis 的 `need_evidence` 已从当前输出契约取消；Editor 仍输出 `patch/reason`，其中 `patch: null` 由程序解释为 `needs_revision`。后者不是配置开关，也不是额外模型输出字段。本次没有新增这一行为。

```text
冻结 Campaign 配置、源码/Prompt、Actor、任务和数据指纹
  → 冻结本轮 Parent / Memory / 任务
  → 公共 Actor 整批 Parent 执行
  → Grouping → Diagnosis → Preconditioner → Editor
  → 公共 Actor 整批 Candidate 执行
  → 按题目 ID 核验配对与实际 Diff → 严格成功数 Gate
  → Replay → 有目标时 Verifier → 有冲突时一次 Repair
  → 不可变 Memory commit → 本轮结果 → 原子切换正式 state
  → 下一轮
```

| 情况 | 执行结果 |
|---|---|
| Diagnosis no_change | 保留 Skill/Memory，结束本轮，不生成 Candidate |
| Preconditioner 全部合法撤回 | 同上 |
| Preconditioner 全部 KEEP | 继续 Editor，不把 KEEP 当作本轮无变化 |
| Editor 空字符串补丁 | 保留 Skill/Memory，不执行 Candidate/Gate/Replay |
| Editor null 补丁 | 合法语义停止；不重采样，不自动回跳 Diagnosis；原 Campaign 不通过 resume 绕过 |
| Gate ACCEPT | 完成 Replay/审查后发布 Candidate 和新 Memory |
| Gate RETAIN | 仍执行 Replay/审查，保留 Parent，但可发布新 Memory |
| Replay 无新增/变化 Knowledge | 不调用 Verifier；仍按原 Memory 提交协议记录本轮 |
| Verifier 无 CONFLICT | 不调用 Repair |
| Repair 输出格式错误 | 在同一模块预算内纠错；不是增加第二次语义修复轮次 |
| 技术或结构错误耗尽额度 | 保存现场并停止，不假造得分、成功记录或正式发布 |

`continue_no_change` 是显式配置：false 在完成并发布一个 no-change 轮后返回；true 继续剩余冻结批次。它不改变单轮模块语义。多 epoch 必须显式声明，且每个 epoch 恰好覆盖同一个优化任务池一次。

## 调用与存储实现

入口代码：

- [modules.py](../../../src/skill_evolution/v26/modules.py)：七模块输入构造与输出契约；复用现有事实投影、计划编译、补丁、Memory、Verifier/Repair。
- [stages.py](../../../src/skill_evolution/v26/stages.py)：统一的单模块持久化、受限重试、响应恢复和选中结果重验。
- [evolution.py](../../../src/skill_evolution/v26/evolution.py)：Campaign 冻结、整批 Actor 接入、分支、审查、提交、发布和已完成轮次审计。
- [config.py](../../../src/skill_evolution/v26/config.py)：显式配置与 Test 隔离；不提供正式实验模型或训练预算默认值。
- [transport.py](../../../src/skill_evolution/v26/transport.py)：显式 HTTP 方法调用，一次函数调用对应一次 HTTP 请求，无 SDK/HTTP 内层重试。
- [monitoring.py](../../../src/skill_evolution/v26/monitoring.py)：完成与未完成请求的计数、已知 token 合计及未知用量数量。

V25 各模块重复的存储骨架在 V26 合并为一个 stage runner；不是把 V25 Campaign 文件机械复制后仅替换版本号。七个输出契约和关键状态分支保持原语义。统一 runner 只包装确定的输出检查；不能将任意输入、归档、磁盘或程序错误当作模型格式错误反馈。

`output_feedback.py` 从步骤 1 冻结的 V25 文件复制，改为 V26 命名空间，登记新模块校验入口，并移除 Spreadsheet 时间线二次投影：OfficeQA 的消息构造器已经生成正式证据视图。来源与变更见 [继承记录](../../../artifacts/methods/v26/campaign_20261029_001/inherited_sources.json)。其已识别输出错误边界、最近一次纠错上下文和禁止借错误扩大证据权限的原则不变。

每个 Campaign 使用独立目录，目录名由英文字母、数字、下划线或连字符构成，用于安全的 Memory context ID。主要结构：

```text
config.json / initial_config.json   实际配置与不可变原配置
contract.json                      本地 V26、Prompt、公共 Actor 源码字节快照
runtime.json                       Python/requests、上游源码哈希、数据/来源指纹、Actor 配置
initial_skill.md                    可选；没有 Stage0
initial_memory/active.json          空 Memory
state.json                         next_round / parent / active_memory
sessions/                          调用与显式 resume 记录
rounds/R01/
  round_input.json / parent.md      本轮冻结输入
  parent_runs/                      原公共 Actor 的 actor/ 与 evidence/，另存完整 records.json
  grouping/                         其余六个模块同样布局
    identity.json                   Prompt/源码哈希、调用配置、额度、视图与重试策略
    input.json / base_messages.json 内部输入与模型基础消息，分开保存
    attempts/001/
      request_context.json / messages.json / prompt.md
      request_started.json          发请求前持久化
      response.json / raw_output.txt
      parsed.json / result.json / validation.json / completed.json
      error.json                    失败时记录；恢复不删除或重置额度
      recovery.json                 已保存响应恢复时：additional_requests=0
    result.json                     选中 attempt 的相对路径
  candidate_runs/
  pairs/input.json / gate/result.json
  knowledge_review/                 精确审查输入、授权修复输入、最终候选及审查摘要
  memory/archive/ / memory/active.json / memory/view.json
  result.json                       before / after / outcome
  progress.json / stop.json
```

Editor 成功时，同一 attempt 下保存 `patch.diff`、`candidate.md` 和严格重算的 `actual.diff`。HTTP 传输还保存不含认证头的 `request.json` 与原始 HTTP 响应/状态；API Key 不进入配置或日志。模型输入仍使用原有各模块权限投影，归档内部输入不会直接整体发送给模型。

## 恢复规则

1. **配置与身份不漂移。** 初始 Skill、任务顺序、批次/epoch、数据内容、源页、参考答案指纹、模型/输出额度、Prompt 和代码变化均拒绝原地恢复。参考答案只保存哈希，不作为方法输入。原生 SkillAdam Python 源码也记录哈希。运行中不支持 budget/source amendments。
2. **先消费额度再请求。** 方法模块的 `max_attempts` 显式配置为 1–6 次总尝试，包含首次，沿用 V25 有界预算；所有 seven modules 使用该冻结预算，输出额度和模型可分别声明。已创建的 slot 永不回收。请求结果未知仍占额度。
3. **完整响应优先恢复。** 已保存 normalized response 或原始成功 HTTP 响应可在原 slot 重新解析，不产生新请求；即使是第六次也能完成。恢复使用同一输入、Prompt、配置和上下文。
4. **只反馈确定的输出错误。** 完整 stop 响应存在已识别 JSON/schema/引用/补丁错误时，下一次请求附最近失败输出及诊断；不累积整个失败历史。传输错误、截断和畸形 API envelope 保留当前请求。磁盘、程序、输入或归档错误停止，不伪装为格式纠错。
5. **正常结果不再采样。** 已选中结果必须重验原响应、解析、派生结果、Prompt 与输出文件；损坏不是新的模型错误。合法 no_change/null 补丁不转换成自动重试。
6. **Actor 恢复保持原状。** 每侧只调用一次公共 `actor_batch`，沿用原目录、workers=4、完成顺序 journal、六次请求预算和工具提交状态。失败题停止、整批收尾；恢复按题目 ID 跳过完成题。没有第二层题目线程池。
7. **提交与发布分开。** 本轮 Memory 使用独立目录，先写不可变 commit，再切换局部 Active；正式 `state.json` 最后原子更新。commit/index、Memory/state 之间中断可用相同输入幂等恢复。发布前再次核验配置和数据指纹。
8. **已发布内容也审计。** resume 和 `final_parent()` 从初始状态重验已发布轮次，包括七模块选中结果、配对、Gate、审查候选和 Memory 链；仅重读，不发模型或 Actor 请求。所有修改入口持有同一非阻塞单写入者锁。

2026-10-29 补齐的三个执行边界（不修改七模块方法语义）：

- **可配置重试退避**：新增可选 `retry_delay_seconds`，默认为 0，必须为有限非负数，并随 Campaign 和 stage 身份冻结。沿用 V25：本次运行中第 n 次可重试失败后，若还有下一次尝试，等待 `retry_delay_seconds × n` 秒；最后一次失败、不可重试错误、成功或纯归档重读不等待。沿用 V25 的恢复行为，不另行补算进程退出期间的退避时间。
- **准备阶段中断**：只有在最后一个 slot 尚无 `request_started.json`、且没有响应/发送/执行结果等矛盾证据时，才根据冻结输入核验已有文件、补齐缺失文件，并继续使用同一个预留编号。已有内容不匹配则停止。临时文件不作为请求或响应证据。开始标记一旦持久化，即使实际发送前中断，也按结果未知的已消费请求处理；不会回收额度。原 slot 的零请求准备恢复同样适用于第六个预留 slot。
- **Actor 前置生成器检查**：发起新的 Parent 或 Candidate Actor 批次前，检查方法生成器可调用。缺失时先停止，不消费 Actor 请求额度。已保存的批次包装记录可直接读取；若包装尚未保存，但原生 journal 已完整提交所有题，则允许重建包装，不要求生成器。部分完成的 journal 不能借此绕过检查。已有方法响应的零请求解析和正式发布仍可在 `generate=None` 下完成。

这三处修复只适用于使用当前源码创建的冻结 Campaign；不绕过旧 Campaign 的源码或配置漂移校验。

技术停止需要显式 `resume=True`；这不代表批准修改配置、扩额或重新采样语义结果。完整响应恢复在原 attempt 完成，没有照搬 V25 的额外 `recovered_*` 子目录；零新增请求和不重置额度的语义相同。

## 显式配置和使用入口

配置必须包含：

| 字段 | 含义 |
|---|---|
| `method` | `method_config()` 的完整当前方法冻结 |
| `benchmark`、`actor` | Adapter 身份和公共 Actor 的完整非秘密 metadata |
| `gate_metric` | 必须显式与 Adapter 一致；当前可选实现为 `officeqa_em_exact_v1` |
| 可选 `optimization_pool` | `officeqa_train50_validation24_v1` 自动构建 50 Train + 24 Validation 的运行视图，保留原始划分来源；不改公共数据文件 |
| `optimization_splits` | 不允许 Test；选择合并池时固定为 `['train']`，不再保留独立 Validation 池；未选合并池时沿用原划分 |
| `batches`、可选 `epoch_schedule` | 明确任务顺序和总轮数；每批使用一个 split |
| `initial_skill` | null，或显式 source/text；不读取其他 benchmark 的 Skill/Memory |
| `max_attempts`、`continue_no_change` | 方法总尝试数及 no-change 后是否继续 |
| 可选 `retry_delay_seconds` | V25 线性退避基数，省略为 0；与公共 Actor 原有重试等待分别管理 |
| `max_input_chars`、`max_message_utf8_bytes` | 每次实际消息含临时反馈的容量硬限制，发请求前检查 |
| `module_calls` | 七模块各自完整配置：endpoint/model/max_tokens/timeout_seconds/temperature，可选 reasoning_effort/thinking/token_limit_field |

已根据用户选择确定：74 题合并优化池、SkillOpt OfficeQA 原始 `initial.md` 作为初始 Skill、不引入 Stage0，以及 EM=1 计成功且 Candidate 成功数严格增加才 ACCEPT 的 Gate。选择记录见 [训练配置已确定部分](../../../experiments/configs/v26_officeqa_training_selection.json)，初始 Skill 原样快照见 [initial Skill](../../../experiments/configs/v26_officeqa_initial_skill.md)。记录包含来源版本、文本和哈希，但不是完整可运行配置，不能直接作为 CLI 的 `--config`。

将选择记录的 `campaign_fields` 合入完整 Campaign 配置即可启用该视图；CLI 根据 `optimization_pool` 自动加载。Python API 使用 `training.load_dataset(prepared_root, optimization_pool)` 构建相同视图后绑定 Adapter。74 题按原 Train 清单随后接原 Validation 清单构成池；批次顺序与是否打乱仍由未来的显式 `batches` 决定。合并池配置必须覆盖全部 74 题；声明多 epoch 时每个 epoch 均需覆盖全部 74 题一次。原始来源保存在运行行／case 元数据的 `source_split` 中，并进入冻结任务指纹。真实 172 题 Test 及公共 prepared_v2 文件不变。

Actor 与方法模块的模型、路由、输出额度以及批次、epoch 等预算尚待选择，不复制 V25 某次实验的绑定模型、推理字段或固定输出额度。优化器重试没有与 SkillOpt/SkillAdam 统一。

Python API 在 `using_benchmark(adapter)` 下使用 `run_campaign(path, config=..., generate=...)`；需要新请求时，`generate(name, messages, directory, call_config)` 必须显式提供。可使用 `HTTPGenerator(api_key)` 或离线固定响应函数；纯归档恢复可以使用 `generate=None`。没有隐式加载 `.env`、创建客户端或自动请求的 fallback。`run_round` 执行并发布至多一轮；`final_parent` 返回完整 Campaign 已验证的最终 Skill 路径（No Skill 返回 None）。

命令行入口为 `python -m src.skill_evolution.v26.cli`，支持：

- `status <campaign>`：只读进度与成本，不需要凭据，不声称完成完整性核验。
- `run <campaign> --config <file> --prepared-root <dir> --parsed-root <dir> --actor-key-env <变量名> --method-key-env <变量名>`：显式运行；恢复另加 `--resume`。此模式构建真实调用器，必须同时提供两个凭据选项；没有凭据时不会自动降级。
- `run <campaign> --config <file> --prepared-root <dir> --parsed-root <dir> --resume --archive-only`：无凭据归档恢复，不创建 Actor 或方法请求客户端。仅绑定冻结 Actor 元数据，传入 `generate=None`，沿用原 Campaign 的恢复检查与额度。

归档恢复命令模板（本次未执行真实 Campaign）：

```sh
python -m src.skill_evolution.v26.cli run /absolute/path/to/campaign \
  --config /absolute/path/to/campaign/config.json \
  --prepared-root /absolute/path/to/data/officeqa/prepared_v2 \
  --parsed-root /absolute/path/to/data/officeqa/corrected_v2/treasury_bulletins_parsed \
  --resume --archive-only
```

`--archive-only` 必须与 `--resume` 同时使用，不能指定任一 key 环境变量选项，也不能初始化新的 Campaign。配置必须与原 Campaign 一致，原数据、来源文件、代码与 Prompt 身份仍会校验；不迁移旧版本冻结归档。

该模式可恢复已保存的模块响应、重建完整 Actor journal 的包装、完成 Memory 和正式状态发布，因此不是只读命令。遇到未完成 Actor 批次或需要新模块请求时停止；不会分配新的请求额度、重新采样或创建备用目录绕过预算。新 Parent／Candidate 请求前仍执行原有的方法生成器检查，已耗尽额度保持耗尽。仅查看状态时使用 `status`。

独立测试的 `evaluate`、`report` 命令见 [测试说明](EVALUATION.md)，测试结果不进入 Campaign 更新。

## 离线验收与边界

验收命令：

```sh
/Users/didi/miniforge3/envs/OfficeQA/bin/python -m pytest \
  tests/skill_evolution/v26 tests/adapters/officeqa -q \
  --junitxml=artifacts/methods/v26/campaign_20261029_001/pytest.xml
```

测试覆盖 ACCEPT/RETAIN、三个 no-change 分支、Editor null 停止、全部 KEEP、无目标跳过、一次 Repair、跨 epoch 的 Skill/Memory 继承、历史引用精确取证、技术/输出重试隔离、六次额度、最后响应恢复、原始 HTTP 错误恢复、API 用量未知、发布/Memory 中断、来源/配置/结果漂移、单写入者锁、Test 隔离和 Actor 整批失败后的 journal 恢复。

所有 V26 测试阻断 socket、requests 和 OpenAI/Azure 客户端；传输单测只用本地假 Session。固定响应生成器运行 Campaign 状态机，不进行模型推理。成本统计扫描原 Actor 状态和方法 request_started，计入失败/未完成尝试，避免重复统计证据包装和恢复解析；未知 token 字段保持未知，不记成已知零。

精确测试数量、源码指纹与快照见 [验收报告](../../../artifacts/methods/v26/campaign_20261029_001/report.json) 和 [JUnit](../../../artifacts/methods/v26/campaign_20261029_001/pytest.xml)。原 V24/V25、公共 OfficeQA Actor、数据和七份 Prompt 保持不变。

三处恢复补齐后的验收为 **246 项通过，其中新增 32 项**。覆盖准备文件逐步落盘的中断、第一/第六 slot、开始标记前后区别、归档矛盾/篡改拒绝、格式反馈保留、退避边界、Actor 前置检查和不需要生成器的纯归档恢复。等待测试使用替身，不实际等待退避；模型响应和 HTTP Session 均为离线替身。该步骤记录见 [补齐验收报告](../../../artifacts/methods/v26/recovery_20261029_001/report.json) 和 [JUnit](../../../artifacts/methods/v26/recovery_20261029_001/pytest.xml)。

Campaign 命令行无凭据归档恢复补齐后的完整离线验收为 **283 项通过，其中新增 17 项 CLI 测试**。新增覆盖完成状态重读、发布中断、已保存 Verifier 响应恢复、完整 journal 包装重建、Parent／Candidate／方法新请求前阻止、部分 journal 拒绝、六次方法额度耗尽、模式／配置校验及原显式调用模式回归。客户端构造在归档测试中被禁止；显式调用模式测试仅注入离线固定响应。记录见 [CLI 归档验收报告](../../../artifacts/methods/v26/cli_archive_20261029_001/report.json) 和 [JUnit](../../../artifacts/methods/v26/cli_archive_20261029_001/pytest.xml)。

当前正式训练配置已确定，见 FORMAL_TRAINING.md：deepseek-flash、74 题、1 epoch、8 次迭代，采用 corrected_v2 语料及已确定的各模块输出预算。真实训练仍需检查输入容量、截断与输出质量；离线验收不代表自进化效果。

独立 Test 执行、恢复与报告入口现已接通，见 [独立测试说明](EVALUATION.md)。它固定使用当前 172 道 Test 题、公共 Actor 和原生 EM/F1 评分，输出写入独立目录，不进入七模块或 Campaign/Memory 更新。`final_parent()` 仍仅负责核验并读取已完成 Campaign 的最终 Skill；不会自动启动测试。

74 题优化池与初始 Skill 选择接入后的完整离线验收为 **296 项通过，新增 13 项**，覆盖原划分来源保留、混合原 Train／Validation 批次、归档 CLI 恢复、全池／每 epoch 覆盖、Test 排除、底层数据漂移、SkillOpt 初始文本与来源核对，以及 F1 单独提高不触发 ACCEPT。记录见 [训练选择验收报告](../../../artifacts/methods/v26/training_selection_20261029_001/report.json)。未调用真实模型或启动实验。
