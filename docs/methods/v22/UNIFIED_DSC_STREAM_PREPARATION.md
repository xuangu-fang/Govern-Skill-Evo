# V22 unified D/S/C v2：真实流式实验准备与冻结

日期：2026-10-16（北京时间）。**准备完成，尚未启动；等待用户启动授权。** 本阶段实验模型请求 0 次，ALFWorld episode 0 个，正式发布 0 次。

完整研究协议见 [PROTOCOL.md][protocol]；可执行配置见 [plan.json][plan]；预先确定的结果分析结构见 [REPORT_TEMPLATE.md][template]。本次不继续优化五模块算法。

## 1. 研究设置与任务边界

研究目标是持续生成有价值 Candidate、观察历史条件化编辑响应对 D/S/C 的真实作用，以及验证同一 Update 从 Diagnosis 到 Memory 的闭环。允许合理 Keep、双向尺度调整、有界探索、失败和局部退化，不要求每轮非恒等变换。

原建议需要 20 项新 Train，但当前固定 SkillOpt Train 只有 39 项：01—08 实际执行覆盖 22 项，加上 05／07 披露的前置 `train:0005`，保守排除 23 项，仅剩 16 项。09 复用真实材料并包含合成探针，没有新增 episode。

因此先报告了限制，再取得用户明确选择：**改为两轮各 8 项，全部使用新 Train**。没有混入 Selection／Test、扩大到原始 Train 或复用旧任务。124 份历史来源及逐任务排除依据见 [任务盘点][inventory]，包括冻结／已执行／复用／合成材料的区分。

选择规则先固定 seed `v22.unified_dsc.v2.train-stream.20261016.seed42`，按 `SHA256(seed + 换行 + id + 换行 + gamefile + 换行)` 升序排名，再顺序分配；不依据成败、任务家族或易修复程度挑选。

| 轮次 | 冻结 Train ID |
|---|---|
| R1 | train:0019、0004、0020、0017、0025、0033、0016、0010 |
| R2 | train:0032、0003、0026、0018、0011、0015、0031、0030 |

两轮互不重复，与历史排除集合交集为 **0**；每个条目均与原生 Train manifest 完全匹配。完整清单和生成授权见 [task_manifest.json][manifest]、[TASK_SELECTION.md][selection]。游戏与任务 JSON 均可静态解析；没有通过环境执行筛选任务。

初始 [内容规范][initial] 为 No Skill＋空 Memory，profile `v22.unified_dsc.v2`，不导入 08 的 Skill／Effect。R2 继承 R1 Gate 和有效 Memory 共同发布的状态；不另行重置。每轮完整批次只生成一份 Candidate。

## 2. 连续更新协议保持不变

```text
Parent Replay → 全局决策分类 → Diagnosis → Fusion／Compiler → Editor
→ Candidate Replay → Gate → Replay／Memory Learning → 共同发布
```

R1 Fusion 程序恒等。完整有 Candidate 的轮次需要 8 对同任务、完整且可比的执行；Candidate 原生成功数严格增加才 ACCEPT，否则 RETAIN，无零退化门槛。RETAIN 仍可学习局部响应。

Keep、合法无有效更新、Editor no_change、技术失败与完整比较后的 RETAIN 分开记录。Gate 完成但 Memory 无效时不发布，不推进下一轮。无 Candidate 不伪造 Candidate 分数；空历史且没有实际编辑时沿用既有 no-op 路径，实际调用可少于上限。

预注册分析覆盖原始 Update、适用的历史实际编辑／响应、Fusion 决定、有效 Update、Editor diff、真实机会／行动和 Memory 修订。历史贡献、当前证据修正、合理 Keep 与无法判断分别解释；仅有联合证据时保留联合归因。不以成功率、Effect 引用量或变换数量直接证明预条件化优势。不同轮次任务不同，跨轮成功率差不直接解释为提升或遗忘。

## 3. 冻结预算与请求规则

Actor 保持 `deepseek-v4-flash`；更新模块为 `deepseek-v4-pro`。每个 episode 最多 50 步，任务内串行、任务间最多 8 并发，语义阶段串行。Actor seed 42、最近两步历史及动作投影保持原样。

| 请求类别 | 最多逻辑调用 | max_tokens／次 | 连接／读取超时 | HTTP 尝试／调用 |
|---|---:|---:|---|---:|
| 分类 | 2 | 32,768 | 10／600 秒 | 1 |
| Diagnosis | 2 | 32,768 | 10／600 秒 | 1 |
| Fusion | 1 | 32,768 | 10／600 秒 | 1 |
| Editor | 2 | 32,768 | 10／600 秒 | 1 |
| Replay／Memory | 2 | 65,536 | 10／600 秒 | 1 |
| Actor | 1,600 | 16,384 | 10／300 秒 | 最多 6 |

参数统一为 `temperature=1.0`、`thinking.enabled`、`reasoning_effort=medium`、`stream=false`。语义 JSON 使用现有 Prompt／Schema 和解析器，不新增 provider 返回格式模式。Thinking 与可见输出共享 max_tokens，没有假定独立 JSON 保留空间。

预算依据来自 [18 条归档调用证据][budget]：08 分类／学习曾在 16,384 下截断；09 学习实际输出 20,980 Token，其中推理 18,559，耗时约 320 秒。正常预算不再沿用该不足上限。

- 环境最多 **32 个 episode**；逻辑请求最多 **1,609**，其中 Actor 1,600、Pro 9。
- Pro 单 POST，零自动传输／语义重试；Actor 保留既有仅对 429／500／502／503／504 的最多六次相同请求尝试，网络异常不自动重发。两者禁 redirect。总 HTTP 尝试最多 **9,609**。
- Pro completion 声明额度合计 **360,448**。Actor 按每逻辑请求一次为 **26,214,400**，按全部六次可能计费尝试为 **157,286,400**；含 Pro 分别 **26,574,848／157,646,848**。这些不是预期消耗。
- 语义输入硬性工程上限为每次 **400,000 个 compact JSON messages 字符**，另有内容字符检查；不是 Token／上下文保证。08 R2 学习为 398,816 个该口径字符／119,314 输入 Token。后续真实轨迹产生前无法冻结动态消息全文，只能冻结装配代码、System、预算及每次实际输入。
- Actor 输入随观察和 Skill 变化，实际输入 Token 根据 provider 记录；不编造固定总输入 Token。没有内部代理费率，货币总价保持未知。
- 旧调用曾在请求 16,384 时报告 17,477 completion；请求额度不能保证服务账单绝对不超额。若发生，记录预算异常，不改写用量。

保存每次 HTTP 原始 body、请求身份、usage、耗时与结束状态，包括失败响应；最终成功 response 不与对应 attempt 重复计费。推理 Token 仅在 provider 给出时汇总，作为 completion 子集。未知 usage 不记作免费。额外恢复请求不在本次常规预算内。

## 4. 必要工程适配

新增运行协议 `v22.grouped_continual.v4`，算法 profile 仍为 v2；旧 v2／v3 运行配置保留原默认行为。

| 适配 | 实际作用 |
|---|---|
| [配置加载及阶段预算][runtime] | 新协议接受本次 8+8 原生 Train 清单，按批次派生 episode／请求预算，绑定准备材料；将 32k／64k、600 秒和单次请求规则传到调用与校验器 |
| [预冻结启动][runner] | 新增 `run --prepared`，同目录使用已批准的 freeze；源码／配置／依赖／游戏漂移在调用前拒绝；独占 start claim 防止重复启动；不将失败目录当作 resume |
| [语义传输][model-call]与 [Actor 响应归档][archive-code] | 新显式模式保留完整 HTTP body 和哈希，语义单次请求，Actor 既有六次规则；失败 JSON／HTTP／截断不自动重采样 |
| [用量汇总][cost-code]及运行核验 | 新归档模式按 attempt 汇总，包括失败用量，避免漏算／重复；原始响应身份在进入学习和事后验证时检查 |

已变更 8 个既有源码文件，新增 1 个响应归档辅助模块与 3 个测试文件。`unified_dsc.py`、Update／Effect 的算法语义、模型输出 Schema、Gate、正式 Memory 语义和分类 Prompt 均未改变。

正常上限仍是 9 次语义阶段，没有新审核 Agent、额外总结或自动修复调用。完整响应归档增加磁盘资料，不增加模型输入 Token。

## 5. 离线验证、兼容性与预检

- **V22 376 项通过**，包含新增 18 项；[日志][v22-tests]。
- **ALFWorld 适配器 35 项通过**；[日志][adapter-tests]。
- 新 8+8 合成主线完成 9 次模拟 Pro 调用、32 条合成 Actor 记录，32k／64k 预算、原始 body、发布及完整 verifier 通过。它们不是模型请求或环境 episode。
- 新测试覆盖无重试、失败及未知用量、推理子集、旧默认隔离、预算／材料漂移拒绝、prepared 单次启动，以及阶段参数和 Actor 归档标志接线。
- 08 的 10 份旧消息、09 的 7 份 v1 消息可逐字重建。核对 1,345 个修改前文件，仅上述 8 个源码变化；旧实验配置、Prompt、Skill、Memory、运行结果及报告未变。见 [兼容性核对][compatibility]。

回归过程中修正了旧恢复输入省略 protocol 时的新分支兼容问题。首次预检包装脚本在 freeze 已保存后遇到兄弟模块导入路径错误；只修正独立检查脚本并核验同一 freeze，没有重建或覆盖冻结源码。初次测试日志与 [准备诊断][diagnostics] 保留。

[只读预检结果][preflight]确认：

- 冻结 48 个源码／协议文件、14 个配置及材料绑定、16 个实际游戏文件；依赖为 ALFWorld 0.4.2、TextWorld 1.7.0、requests 2.32.5、python-dotenv 1.2.1。
- 任务静态文件可读且身份一致；环境接口可导入。凭据配置存在，只记录存在性与 endpoint 哈希，不复制密钥。
- 检查脚本对 HTTP 请求与 `textworld.start` 设置禁止调用哨兵，两者计数均为 0；没有 reset／step、Candidate 或发布记录。
- 只读核验再次通过。它不证明远端认证／模型服务可用，也不证明真实 reset 必然成功；这些需授权启动后才可观察。

运行目录目前严格只有 `runtime_freeze.json / source_snapshot / config_snapshot`，没有 start claim、state0、rounds 或实验 report。

## 6. 冻结身份与实际命令

冻结记录：[runtime_freeze.json][freeze]。

| 对象 | SHA-256 |
|---|---|
| runtime 内容身份 | `b5ca8ef981c2bcc7326610c2ce2dd1b59988cf7603f32cb2eae6027946211b37` |
| runtime 文件 | `35dbe50a4aa207b83cac33953d92b318aa4827dfcbc4429050b41b0473e575eb` |
| plan 文件 | `cb9b0ffd24265204da6fc572b23aba0b30e631d3cef1506477cca78f473b4a91` |
| task manifest 文件 | `74e0cd98d0a62077ed3b7a02875fff68db01e9e9bf5a21c815bdbd0c320c764a` |

可安全重复的只读启动前核验：

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/envs/alfworld/bin/python \
  artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/preflight.py --check
```

**以下命令会调用模型并运行环境，仅在用户明确授权启动后执行：**

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/envs/alfworld/bin/python -m src.skill_evolution.v22.continual_runner run \
  --prepared \
  --plan /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/plan.json \
  --output-dir /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_live_20261016 \
  --env-file /Users/didi/Desktop/Govern-Skill-Evo/.env
```

首次启动后不能再次使用该命令作为恢复。若发生技术失败，保留原目录，停止新增分发并结算在途工作；另行提交独立恢复协议、原档案哈希、可复用检查点和新增预算。已完成且可核验的阶段不重跑；不完整 episode 不默认重跑／替换。主运行器没有通用 resume，本次也不预授权恢复。

准备阶段没有剩余已确认的程序阻碍；实际服务、语义质量和新任务效果仍需授权实验检验。本次交付停在冻结方案，不启动实验或下一轮 Prompt 优化。

[protocol]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/PROTOCOL.md
[plan]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/plan.json
[template]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/REPORT_TEMPLATE.md
[inventory]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/task_inventory.json
[manifest]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/task_manifest.json
[selection]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/TASK_SELECTION.md
[initial]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/initial_state.json
[budget]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/config/budget_evidence.json
[runtime]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_runtime.py
[runner]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_runner.py
[model-call]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/model_call.py
[archive-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/adapters/alfworld/response_archive.py
[cost-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/run_round.py:55
[v22-tests]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/v22_regression.log
[adapter-tests]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/adapter_regression.log
[compatibility]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/compatibility.json
[diagnostics]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/preparation_diagnostics.json
[preflight]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_preparation_20261016/preflight.json
[freeze]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_live_20261016/runtime_freeze.json
