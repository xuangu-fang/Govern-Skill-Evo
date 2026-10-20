# V22 Editor 要求保持与 Replay 行为反馈：首版实现及真实验证

日期：2026-10-14。**代码与离线测试已完成，真实语义输出验收未通过。** 两次 Replay 和两次独立 Editor 构造检查均被校验拒绝，没有发布有效的 `package.json` 或 Editor v1 结果。以下事实核对与人工分析不能冒充通过验收的自动行为反馈包。

## 1. 问题、配置与范围

**Question：** 能否依据已保存的真实 Train 执行形成可追溯的行为观察，同时在一次 Editor 构造调用内检查实际文本是否保持要求及能力边界？

**Hypothesis：** 程序核对来源、执行事实及覆盖，模型解释条件与行为，并显式保留未知，可以支持后续响应学习；Editor 的结构化要求检查可以阻止已经声明的实质偏离或不可用能力依赖，不必新增固定 Review 调用。当前结果没有验证模型能稳定完成这些语义职责。

- 代码基线 Git HEAD：`7d4749541dab04397ea146e56dc762a26ba81a3b`；本阶段新增源码未提交，各操作 manifest 保存实际 Python 源文件 SHA-256。
- 初始配置：[plan.json](../config/plan.json)；在首次失败后、恢复调用前保存 [plan_recovery.json](../config/plan_recovery.json)，每个组件只追加一次独立调用。输入消息 hash 与各自首次调用相同，没有放宽校验或追加自动修复。
- 请求和返回模型：`deepseek-v4-flash`；temperature 请求值 1.0，thinking enabled，reasoning effort medium，max_tokens 请求值 16,384。每次允许最多六次既有传输尝试，实际均仅一次 HTTP，无传输重试。
- 来源：`artifacts/methods/v22/no_history_20261014/round`，原始报告 SHA-256 为 `6ac9e360a75906fe93d702d99b004a30b757e4f0721066497b2946818da36247`。使用原两项 learning-purpose Train 任务，不新增环境执行或访问 Selection／Test。
- Replay 使用实际旧 Candidate 和四条完整配对轨迹。独立 Editor 检查仅使用原 Parent、Diagnosis 与执行前证据，不读取旧 Candidate 或执行结果，不将新草稿执行或采用。
- Memory、Fusion 作用变换、正式 Gate、Skill 采用、额外比较与跨轮发布不属于本次实现。

## 2. 已实现的路径

具体约定见 [BEHAVIOR_FEEDBACK.md](../../../../../docs/methods/v22/BEHAVIOR_FEEDBACK.md)。

1. **Editor v1 同次检查。** 每项 proposal 对照触发条件、策略、范围、保留行为、关联和能力六方面检查实际文本，附准确摘录、状态和理由；程序检查要求 hash、完整覆盖、摘录真实性、状态与上游反馈一致性。已声明依赖完整历史、持久笔记或隐藏状态等不可用能力时，必须返回 `needs_revision`，不释放 Candidate。程序不能自动识别所有隐含依赖或证明自然语言等价。
2. **执行前观察说明。** 新轮次在 Candidate 执行前保存 `observation_plan.json` 并绑定 lineage，直接复用原目标、保留行为、预期、关联和边界；不新增模型调用。旧轮次只允许从冻结材料重建，标记为重建，不能回写成当时已有的检查。
3. **Replay 事实与解释分离。** 程序核对来源、真实版本、diff、执行条件、原生结果、动作与用量；一次模型调用负责落实、机会、行为、响应、联合关系、未决预期和未知。每个目标／全局保留行为与每项配对任务必须有去向，引用绑定正确的 run、task 和 step。proposal 内的局部保留要求作为完整输入保留，但尚无逐条执行覆盖保证，不能声称全部保留条件均已检查。
4. **反馈与审计。** 只有完整有效输出才能形成反馈包；错误保留原始响应与成本，不伪装成未知或无需修改。来源轮次只读，结果保存到独立目录。新 `run_round` 默认 v1，拒绝模型自行降级为 v0；旧 v0 产物仍按原协议复核。

逻辑检查没有变成逐项模型调用。常规每个 Editor 构造仍是一轮语义工作，Replay 后处理是一轮；本次共四次调用是因为两类验证均各发生一次明确记录的恢复，不是常规流程需要四次调用。

## 3. 真实调用结果与成本

所有操作的请求、原始响应、manifest、输入、状态和离线审计位于 `artifacts/methods/v22/behavior_feedback_20261014/`，汇总为 `validation_summary.json`。

| 操作目录 | 结果 | 已报告 tokens | 首个拒绝原因 |
|---|---|---:|---|
| `replay/` | error，无反馈包 | 28,014 | 要求摘录不属于对应 proposal；进一步查看还只有 6 项观察，未满足 6 个目标／保留项 × 2 个任务的 12 项覆盖 |
| `editor_check/` | error，无有效 Editor 输出 | 19,321 | 响应不是一个合法 JSON 对象 |
| `replay_recovery/` | error，无反馈包 | 30,267 | JSON 字符串转义／闭合错误；未进行文本修补或语义补齐 |
| `editor_check_recovery/` | error，无有效 Editor 输出 | 49,473 | `unresolved_expectations` 重复键；不选择其中一份覆盖另一份 |
| **合计** | **4 次语义调用、4 次 HTTP、0 次环境执行** | **127,075** | **0 次未知用量、0 次传输重试** |

合计 prompt tokens 为 84,515，completion tokens 为 42,560；源轮次的 285,828 已报告 tokens 及一次未知用量不重复计入本阶段。原四次请求全部留存，失败不从成本中剔除。

Editor 恢复请求的返回 completion_tokens 为 31,761，其中 reasoning_tokens 为 24,986，高于请求 max_tokens 的数值；此前原始单轮也出现过类似计量现象。这里只能记录实际返回，不能断言当前网关已执行总 completion 的硬上限。四次返回均为 `finish_reason=stop`，因此仅靠结束标志不足以判定输出完整或合法。恢复前后输入 hash 相同，服务返回的 prompt token 计量仍有差异；原因未确定。

四份操作的来源／调用／成本离线审计均为 `artifact_valid=true`，但 Replay 的 `feedback_ready=false`，Editor 的 `check_complete=false`。前者只说明失败材料可核对，不意味着语义产物有效。按恢复计划本阶段不再追加调用。

## 4. 从原始执行可确认的事实

这些事实由程序从原轨迹提取，在 `replay/input.json` 的 `facts` 中保留来源。原始 Candidate SHA-256 仍为 `8779a3f166d8ad42c7db82292a64a420746c723d586e2e8a73c9c78d1659ecc5`。

| Train 任务 | Parent | Candidate | 可核对变化 |
|---|---|---|---|
| `train:0000` 照明 | 原生成功，28 步 | 原生成功，7 步 | Parent 第 4、7 步动作不在当前合法列表；Candidate 未出现该情况；Parent 有 4 次 `look`，Candidate 为 0 |
| `train:0012` 清洁放置 | 原生成功，7 步 | 原生成功，8 步 | 两侧动作均在合法列表；Candidate 第 4 步增加一次 `look` |

两项配对的已记录执行条件匹配；模型随机性和未观察变化仍在，不能把 28→7 步直接分摊为 p1、p2、p3 的独立收益。完整轨迹核对补出了 Diagnosis 未强调的第二次非合法动作，说明 Replay 必须读取实际执行，不能只复述初稿片段。

以下是**人工复核线索，未被接纳为自动 Replay 解释或 Memory 知识**：

- 原 Candidate 将 p2 的“灯尚未点亮”改为“当前没有点亮观察”，将 p3 的“未访问容器”改为一般合法探索，涉及状态条件和历史依赖变化；后来的任务成功不能证明这些改写等价。
- 照明两侧选择的闹钟实例不同；p2 与 p3 联合执行，没有独立对照。完成序列也不能证明“先放下目标”在所有此类任务中必要。
- 清洁任务保留成功结果，但多一次 `look`，不能据此报告所有行为完全保持。
- take 后未完成的恢复分支、不同灯具与目标组合、较大合法动作列表等边界未覆盖；Candidate 对零奖励与 `Nothing happens` 的概括仍需区分。

## 5. 验证与下一步

离线验证覆盖新旧协议兼容、执行前绑定、已声明实质偏离与不可用能力的阻断、伪造或错侧引用、目标覆盖、未触发误报保持、不完整／不可比执行、输出篡改、失败成本和旧轮次复核。方法侧 **111 项**、环境侧 **35 项**测试通过。127 份受保护文件及日志原有前缀保持不变，旧轮次仍可离线核验；文档本地链接有效，新增 V22 文件无尾空白。`git diff --check` 仍报告此前已有的日志第 6619 行尾空白，未清理历史内容。精确结果保存于 artifact 根目录的 `verification.json`。

```bash
python -m unittest discover -s tests/skill_evolution/v22 -q
python -m unittest discover -s tests/adapters/alfworld -q
python -m src.skill_evolution.v22.feedback verify \
  artifacts/methods/v22/behavior_feedback_20261014/replay
python -m src.skill_evolution.v22.editor_check verify \
  artifacts/methods/v22/behavior_feedback_20261014/editor_check
```

这两条真实操作的 verify 命令会返回非零退出码，并同时报告材料可核对、语义产物未就绪；这是本次失败的实际状态。单元测试中的有效输出是显式构造的协议测试夹具，不是模型成功证据。

下一步应先解决**真实语义输出的稳定性与成本**，再接入 Memory／Fusion：减少让模型重复复制的标识和结构，研究由程序装配确定性字段、模型只返回必要判断的紧凑协议；在保持完整证据、覆盖和引用约束的前提下压缩输入，检查服务的结构化输出支持与 token 计量。同时明确必要的局部保留条件如何合并和覆盖，避免不断展开重复观察。具体方案需单独设计及验证，不能用宽松解析、丢弃冲突字段或连续重跑掩盖本次失败。程序绑定字段也不能代替对判断依据的核查。

当前完成的是两个模块的首版工程路径、失败阻断和可审计材料；**有效的真实行为反馈包与 Editor v1 真实构造仍未交付，不能把这一阶段描述为闭环已经跑通。**
