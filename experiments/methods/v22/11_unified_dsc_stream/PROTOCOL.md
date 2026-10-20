# V22 unified D/S/C v2：新 Train 两轮流式实验协议

日期：2026-10-16（北京时间）。**本协议只授权准备与冻结；模型请求和 ALFWorld 执行须另获启动授权。** 算法 profile 为 `v22.unified_dsc.v2`，运行协议为 `v22.grouped_continual.v4`。后者仅标识新任务绑定、阶段预算、响应归档及预冻结启动，不改变五模块算法。

## 1. 研究目标与已批准边界

观察持续 Skill 自进化、历史条件化编辑响应对 D/S/C 的作用，以及同一 Update 从构造、变换、落实到响应学习的闭环。允许失败、局部退化、合理 Keep 和有界探索；不要求历史必须导致非恒等变换。

初始状态为 No Skill、空 Memory，不导入旧 Skill 或 Effect。固定 SkillOpt Train 清单共 39 项，历史已接触／选用 23 项，只剩 16 项新任务。因此用户明确批准由原建议的 10+10 调整为 **8+8**；没有扩大到原始 ALFWorld 全量 Train，也不使用 Selection/Test。

任务规则、历史来源和批准记录见 `TASK_SELECTION.md`、`config/task_inventory.json`。先固定 seed/hash 排名，再顺序分配前 8／后 8，不使用成败、修复可能性或家族配额。相对 01—09 及其披露的前置 Train，16 项交集为 0。

| 轮次 | 冻结任务（统一前缀 train:） |
|---|---|
| R1 | 0019、0004、0020、0017、0025、0033、0016、0010 |
| R2 | 0032、0003、0026、0018、0011、0015、0031、0030 |

每轮一个完整批次、一份统一 Candidate，不按决策组产生不同 Skill；无 Direct 分支、额外消融或额外回归批次。R2 继承 R1 完整发布的 Skill 和 Memory。各轮任务不同，跨轮成功率不能作为遗忘或进步的直接比较。

## 2. 固定流程与发布

```text
Parent Replay → 全批决策问题分类 → Diagnosis → Fusion／Compiler
→ Editor → Candidate Replay → Gate → Replay／Memory Learning → 共同发布
```

- R1 空历史使用程序恒等 Fusion，0 次 Fusion 模型请求。正常 R1 4 次语义阶段，R2 至多 5 次。R2 若没有可学历史，诚实记录当前证据作用，不制造历史贡献。
- 一轮有实际 Candidate 时，Parent 和 Candidate 各执行同一批 8 个任务，每项各一次。相同任务／种子／Actor 协议和模型条件须可核验。
- Gate 沿用 `v22.native_success_improvement.v1`：8 对完整、可比时，Candidate 原生成功数严格大于 Parent 才 ACCEPT，否则 RETAIN。无零退化否决。
- RETAIN 不否定局部编辑响应；有效 Memory 可以学习接受或拒绝 Candidate 的联合响应、反例与边界。
- Gate 完成但 Memory 无效或发布失败时，不推进任何正式 Skill／Memory 引用；停止后续轮次。
- Keep 保留原始 Update，仍可交给 Editor。合法 no_change、全部撤回、needs_revision、技术失败和完整比较后的 RETAIN 分别记录；无 Candidate 时没有 Candidate 分数，不能当作平局。已有无编辑学习／空历史 no-op 路径保持。
- 不依据本轮成败修改任务、Prompt、Schema、算法、预算或更新策略，也不重复采样已有有效输出。

## 3. 请求、并发与预算

Actor 为 `deepseek-v4-flash`，语义阶段为 `deepseek-v4-pro`。均发送 `temperature=1.0`、`thinking={"type":"enabled"}`、`reasoning_effort="medium"`、`stream=false`。保持当前 Actor 最近两步历史、seed 42、每 episode 50 步；任务内动作严格串行，任务间最多 8 并发。语义阶段在完整批次后串行执行，不与下一阶段重叠。

| 阶段 | 最多逻辑调用 | 每次 max_tokens | 连接／读取超时 | HTTP 尝试 |
|---|---:|---:|---|---|
| 分类 | 2 | 32,768 | 10／600 秒 | 每调用 1 次 |
| Diagnosis | 2 | 32,768 | 10／600 秒 | 每调用 1 次 |
| Fusion | 1 | 32,768 | 10／600 秒 | 每调用 1 次 |
| Editor | 2 | 32,768 | 10／600 秒 | 每调用 1 次 |
| Replay／Memory | 2 | 65,536 | 10／600 秒 | 每调用 1 次 |
| Actor | 1,600 | 16,384 | 10／300 秒 | 每逻辑请求至多 6 次 |

语义输出仍按既有 JSON Schema 由 Prompt 要求，使用现有严格解析器；不额外启用 provider JSON mode。Actor 继续既有 `<action>` 投影及缺失标签时的 look fallback；本次不修改动作算法。

`max_tokens` 是推理与可见输出共享的请求预算，不能把全部额度当作 JSON 空间，也不能虚构独立保留配额。根据归档证据，08 的分类和学习在 16,384 下曾截断，09 学习实际输出 20,980（其中推理 18,559）并用时约 320 秒，因此预先改为以上 32k／64k、600 秒。完整源路径和字段见 `config/budget_evidence.json`。

语义输入工程上限为**序列化 messages 的 400,000 Unicode 字符／次**，不是 Token 或上下文容量保证。所有阶段都受同一上限；每轮实际输入要等真实轨迹和此前发布的 Memory 产生后才可确定。08 学习曾达到 398,816 个 compact JSON 字符／119,314 输入 Token；本次批次减为 8 项，但仍不保证任意 Skill／Memory 增长都能装入。超限保存证据并停止，不自动裁剪轨迹、删 Memory 或追加总结调用。

总预算：

- 2 轮、16 个独立 Train、最多 **32 个 episode**。
- 最多 **1,600 Actor＋9 Pro＝1,609 逻辑请求**。
- Actor 既有 HTTP 规则：仅 429／500／502／503／504 可在相同请求体下至多 6 次尝试，退避 1／2／4／8／16 秒；网络异常不自动重发。语义请求 1 次 POST，无 HTTP 或语义重试。两者禁 HTTP redirect。
- 最多 **9,600 Actor＋9 Pro＝9,609 HTTP 尝试**。已分发并行任务遇到技术失败时，停止新增分发，等待已分发任务结算并计费归档。
- Pro 声明 completion 总额 **360,448**；Actor 每逻辑请求只生成一次时为 **26,214,400**，保守计入全部六次可能计费尝试为 **157,286,400**。含 Pro 合计分别 **26,574,848／157,646,848**。这些是请求额度之和，不是预期消耗。
- provider 曾在请求 16,384 时报告 17,477 completion，故不能将请求额度宣称为账单绝对硬限；实际超额须作为预算异常保留。没有已知代理费率，**货币总价未知**。不把未知 usage 当作 0，也不根据未经确认的公开价格推算内部代理账单。
- 不预分配额外恢复请求、episode 重试或失败后重采样预算。合法无更新可减少实际调用，但余量不能转为额外实验。

保存完整 provider usage、原始响应、模型名、请求参数、消息哈希、finish reason、耗时和每次 HTTP 状态。推理 Token 若 provider 提供，则单列为 completion 子集，不与 completion 再相加。输入 Token、缓存命中及其他细项只按 provider 实际提供字段报告，缺失保持未知。

## 4. 预注册的作用链分析

运行中冻结原始 Plan、Fusion changes、有效 Plan、Editor mappings、实际 Skill/diff、逐步轨迹、Watch／Findings／Effect 与来源身份。分类提供共同决策条件，不把组标签当作适用性证明。

R2 分析覆盖有实质意义的更新决定及保留决定，按以下问题串联证据，不要求模块输出新的 D/S/C 表：

1. 原始 Update 的目标行为、选定策略、触发范围和保留／依赖关系是什么？
2. 被使用的历史 Effect 对应哪份实际编辑、哪组条件及什么实际行为响应？当前条件有哪些可比与不可比处？
3. Fusion 的变换或 Keep 有何具体依据？分别标明历史响应贡献、当前事实／能力修正、尚无法判断的解释。Effect ID、提及 Memory、变换数量本身不是成功证据。
4. Editor 是否保持有效 Update 的方向、尺度、强度和关联？以实际 diff 为准，映射不是语义等价证明。
5. Candidate 是否遇到行为机会、执行目标行为，或路径变化使机会消失？目标响应、局部进展和整体成功分别报告。
6. Memory 如何修订认识？未触发、未执行、未验证不能当作策略无效；联合证据不分摊为独立编辑收益。范围扩大、保留未知及旧限制退役都需与证据对应。

事实、受证据支持但未验证的解释、Prompt 中预期、证据不足结论分别表达。不因机制叙事偏好选择“漂亮”案例；没有明确历史驱动作用也照实报告。报告结构预先保存在 `REPORT_TEMPLATE.md`。

## 5. 失败与独立恢复

检查点是审计证据，不是自动 resume：round_start、classification/evidence、diagnosis、effective、replay、learning、final freeze，以及每次 dispatch／HTTP body／逐步轨迹／state 发布文件。

- 技术失败：保留完整响应及已知消耗；无效 JSON、截断、接口失败、缺少可比轨迹不能转换成合法 Keep、no_change 或 RETAIN。停留在最后已共同发布状态。
- 进程已分发但没有完整可核验轨迹的 episode 视为技术不完整，不能从中间环境状态继续、不能换任务或默认重跑；如因此不足完整配对，不发布该轮 Gate。
- 恢复如有必要，须另获授权，在独立新目录绑定原目录全量哈希、失败位置、完成检查点及新增预算。原目录不修改，已完整有效的阶段／episode 只复用不重跑；成功语义输出不重复采样。
- 未发请求的剩余工作、已发送但无确认响应的工作、已完整有效的结果必须分别列清。没有确认的请求仍可能有费用，不能当作未执行。
- 当前 runner 不提供通用恢复命令；旧 08 控制脚本不可直接套用。本协议不把某种未来恢复预先视为已授权，也不预制绕过验证的恢复入口。

## 6. 冻结、预检与启动

只读 preflight 检查原生 Train 身份、游戏／任务 JSON 可读、依赖及环境接口可导入、profile／预算和绑定一致，不调用 `textworld.start/reset/step`，不发送模型请求。它不能证明真实环境 reset 一定成功。

运行目录内预先生成 `runtime_freeze.json`、`source_snapshot/`、`config_snapshot/`；保存实际源码、配置、分类及五模块 System Prompt、模型请求预算、Train 来源、游戏文件、依赖和执行身份的哈希。No Skill＋空 Memory 已在 plan 中绑定；单独 `config/initial_state.json` 保存起始内容规范，不伪造正式轮次结果。

启动时使用同目录 `run --prepared`；先核验本次 freeze 和所有绑定，再通过独占 start claim 开始。若源码／配置／任务等变化，须重新准备和提交，而非静默重新冻结。已有 report、state 或 rounds 的目录不能作为新启动／resume。

实际绝对命令、最终 freeze SHA、预检和测试结果由准备报告给出。没有启动授权前，只能执行 preflight、只读核验与离线合成测试。后续实验也只支持本次 Train 研究主张；不宣称优于普通 Memory 辅助编辑，不将旧成功率或本次一次运行当作稳定因果收益。
