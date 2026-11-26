# SearchQA v28.3 设计稿：沿用 v29.4 的直接批次 Diagnosis

状态：2026-11-04，独立实现、离线验收及正式训练/Test 均已完成。训练完成 600 题、20 轮；独立 Test 完成 1,400 题，答对 1,187 题，EM 为 0.8478571428571429，F1 为 0.9148350340136054。归档见 [训练汇总](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/training_summary.json)和 [Test 汇总](../../../experiments/evaluations/v28_3_searchqa600_batch30_20261104_022828_test1400/summary.json)，实现与验收说明见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。用户在授权实现时将 Editor 预算从设计稿的 16,384 明确调整为 32,768；四份已审阅 Prompt 原文不变。

## 1. 目标与方法来源

v28.3 将当前 v29.4 方法适配到 SearchQA。v29.4 以当前 v29.2 为基线删除独立 Grouping，让 Diagnosis 直接比较完整 Parent 批次；其余提案、历史调整、实施、事件归因和选择方法继续沿用 v29.2。

这不是把当前 v28.2 的 Grouping 调用删除后直接改名。Diagnosis 和 Preconditioner 从 v29.4 原文开始适配，不继承 v29.3 的额外指导，也不整体移入 v28.2 Prompt v2 的五组修订。保留方法基线已有的整条 KEEP、具体行为增量、必要依赖、条件与保护边界要求。SearchQA 的实体/关系、答案边界、参考形式差异仍准确描述，但不新增独立分析流程。

四份提示词、Actor 原文和基线配置在本目录有可审阅副本；[来源映射](source_map.json)、[提示词审阅](PROMPT_REVIEW.md) 和 [差异](diffs/) 明确方法继承与 benchmark 适配。来源快照的时间点以本目录副本为准，未来上游文件变化不自动升级本设计。

## 2. 模块流程与职责

```text
Parent batch → Diagnosis → Preconditioner → Editor
  → Candidate batch → verified pairs → Replay → Gate
  → append Memory + publish Selected Skill → next round
```

| 模块 | 职责与证据边界 |
|---|---|
| Diagnosis | 直接读取完整 Parent 批次，包括成功和失败；比较共同判断问题及重要差异，生成 Original Plan；不读历史 Memory |
| Preconditioner | 读取 Parent、冻结的 Original Plan、Plan 直接引用的完整当前执行和历史 Memory；按 Direction/Scope/Coordination 决定 KEEP、全文 REPLACE 或 WITHDRAW |
| Editor | 只接收 Parent、goal 和 Update id/text；每条 Update 一个 patch，全部定位同一原 Parent，联合构造 Candidate |
| Candidate | 使用同一批任务、Actor 设置和评分器独立执行；不接收 Parent 答案、评分或参考答案 |
| Replay | 只分析 EM 翻转任务；每题一条事件，明确关联一个有实际修改的 Update 或 null；不读历史 Memory |
| Gate | 依据明确关联的 EM 改善/退化计算 G/L；只采用 Retain patches，不调用模型 |
| Memory | 按轮追加 Effective Updates、Gate 决定和事件；历史不改写，与 Selected Skill 原子发布 |

没有 Grouping Prompt、结果、目录或预算，也没有替代性的分组报告。Diagnosis 不必为每题生成 Update，不要求每条提案同时存在成功、失败和反例；单案例可以支持合理试验。原来 Diagnosis 也能看到完整批次，本次减少的是前置模型解释层，不是首次开放完整证据。

完整字段、引用、patch、分支和恢复规则见 [CONTRACTS.md](CONTRACTS.md)。没有逐 Update 独立 Actor 执行、重组后额外训练验证、新 Verifier、Knowledge 审查或 F1 投票。

## 3. 必须保留的 SearchQA 适配

- **证据可见性**：完整 question/context 直接可见，可以核对 passage 内容；context 存在某内容不证明 Actor 使用了它。普通 assistant.content 完整提供，独立 reasoning_content 不进入任何方法模块。
- **任务解释**：区分实体/关系选择、答案范围与粒度、同一对象的参考名称形式；不能把 EM 不匹配直接认定为实体错误，也不能从单个参考形式推导通用名称偏好。这是任务语义说明，不增加输出字段。
- **Actor**：保持 SearchQA 已有 system/user 模板、Skill 插入方式、完整问题和 context、单回合无工具协议。不能复制 DocVQA 的视觉问答基础提示词、图片占位符或“原图不可见”限制。
- **评分**：沿用答案提取及 SearchQA 原生归一化：小写、移除英文冠词、移除 Unicode 非单词/非空白字符、合并空白。EM 对任一参考精确匹配，F1 为 counter-based token F1 的参考最大值；EM=1 推出 F1=1，反向不成立。不新增别名、参考答案或宽松评分。
- **选择与历史**：以 EM 翻转替换 DocVQA hard 翻转；F1 只作诊断，不改变事件资格或 G/L。未归因事件保留但不投票；无事件的有效提案轮仍记录 source_updates。
- **运行与持久化**：保留 SearchQA 顺序 Memory ID、原文/结构比较，采用 v29.4 的轻量已发布检查点读取；不引入 DocVQA 摘要型 HEAD。具体保证与局限见合同第 9 节。

评分事实来源为 [SearchQA scorer](../../../src/skill_evolution/v28/benchmarks/searchqa/scoring.py) 及 [原生 evaluation](../../../external/SkillAdam/skilladam/benchmarks/searchqa/evaluation.py)。这些文件内旧整包 Gate 不属于 v28.3 的选择逻辑；实现仅复用评分，绑定本合同的逐 Update Gate。

## 4. 固定实验设计和预算

运行配置为 [v28_3_searchqa_train600_batch30.json](../../../experiments/configs/v28_3_searchqa_train600_batch30.json)。基准为 [冻结的 SearchQA v28.1 配置](baseline/searchqa_v28_1_config.json)，其旧 method/prompts 字段仅作来源记录，不能直接用于 v28.3。

| 项目 | v28.3 设计值 |
|---|---|
| 数据 | Train 400 + Validation 200 组成优化池 600，保持原 ID、内容和顺序 |
| 批次 | 原 20×30，单遍、不打乱；合并后 effective split 为 train，source_split 保留 |
| 初始化 | 原 [104 字符初始 Skill](baseline/initial_skill.md)，空 Memory `{"rounds":[]}`；不继承 v28.2 的学习结果或执行缓存 |
| Actor | deepseek-flash，thinking enabled，reasoning_effort=medium，temperature=1.0，direct HTTP |
| Train / Test workers | 15 / 15 |
| Test | 原 1,400 题及顺序；只评估完成训练后最终 Selected Skill，不用 Test 选择 checkpoint |
| 输入容量 | 4,000,000 字符、6,000,000 UTF-8 字节；无额外 context_window_tokens，不截断证据，不设 Skill 字符数上限 |
| 请求政策 | 每个 Actor/方法调用最多 6 次总尝试，无隐藏 SDK 重试，不做语义重采样，不在恢复时清零额度 |
| 重试间隔 | Actor 1.0×尝试序号秒；方法模块沿用 2.0×尝试序号秒 |
| 版本隔离 | 新 method/stage/runtime/Prompt/contract 身份，独立 campaign、Memory、响应日志与 Test 目录 |

| 调用 | max_tokens | timeout_seconds | connect_timeout_seconds |
|---|---:|---:|---:|
| Actor | 32,768 | 300 | 10 |
| Diagnosis | 65,536 | 600 | 沿用 SearchQA 方法传输配置 |
| Preconditioner | 65,536 | 600 | 同上 |
| Editor | **32,768** | 600 | 同上 |
| Replay | 65,536 | 600 | 同上 |

Editor 按用户最新要求设置为 32,768；其余模块保持 SearchQA 原有预算。删除 Grouping 的 32,768 额度，不转移给其他模块。Actor、方法 endpoint、temperature、thinking、reasoning_effort、请求错误分类和 HTTP 520 处理沿用 SearchQA，不能随方法迁移改成 DocVQA 的超时或错误策略。

max_tokens 包括服务端计入的推理 token，不代表保证可输出同样多的普通文本，也不等于输入上下文容量。本次 20 轮正式实验已完成；更长历史下的容量仍需另行验证，不能通过截断证据绕过合同。

## 5. 交接和运行设计

Diagnosis 模型输入只有 parent/runs/shared_initial；输出保持 decision/reason/plan。Preconditioner 的执行筛选遵循 v29.4：扫描整个 Plan 中的合法直接执行引用，不扫描 Diagnosis reason。提示词仍要求关键支持与保护边界的证据进入 basis。

Editor 看不到 basis 或任何调整 reason，所以所有实施条件必须随有效 Update text 传递。Replay 看不到历史 Memory 或上游 reasons，只能依据本轮实际 patch、diff 和已投影的 EM 翻转对解释事件。

保留 no_change、全部 WITHDRAW、全部空 patch、合法 null 语义停止、无 EM 翻转和正常 Gate 等分支。恢复复用已完成请求与检查点，已发布历史不反复重开 Actor 来源；当前轮仍完整校验后发布。无哈希历史读取的保障边界在合同中明确，不宣称与 DocVQA 摘要链等价的检测能力。

train/test 使用独立显式入口；训练结束不自动启动 Test。本次正式训练和后续独立 Test 均已完成，测试使用的 Skill 与训练导出的 final_skill.md 逐字一致。训练汇总中的 test_started=false 记录的是训练入口没有自动启动 Test，不代表后续独立 Test 未执行。v28.2 的恢复仍需用户另行要求，不因 v28.3 的运行或文档更新而终止、唤醒或重标记旧进程。

## 6. 实现验收范围

| 范围 | 需要验证的行为 |
|---|---|
| 方法基线 | 四阶段接线，无 Grouping 调用/目录；v29.4 提案与调整方法未混入 v28.2 Prompt v2；预算符合本稿 |
| 直接证据 | 完整批次含成功/失败；单案例提案合法；Plan 引用筛选精确；Group/历史/隐藏字段非法来源拒绝 |
| 无损视图 | system 共享、重复字段省略可逆；question/context/普通响应逐字保留；过滤后 P/Q 不重编号 |
| 编辑与选择 | 每 Update patch、共享 context、字符改动组合、空/null、子集重组、来源相等判断及分数归属 |
| SearchQA | 原生浮点 EM、归一化、F1=1/EM=0、F1-only 不投票、未归因事件、Actor 模板与参数一致 |
| 记忆与恢复 | 无事件仍记提案、追加不可改写、原子 HEAD、游标落后恢复、调用额度不重置、轻量历史读取 |
| 隔离 | 旧版本拒绝、旧文件与暂停实验不变、Test 不进入优化、正式请求与离线合成验收隔离 |

SearchQA 离线验收 403 项全部通过，其中 v28.3 专项 129 项；DocVQA 不作为必需验收或运行依赖。实际结果见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。设计阶段的 31 项静态检查及后续预算变更记录见 [design_validation.json](design_validation.json)，不能用文档检查替代运行验收。

## 7. 效果解释边界

删除 Grouping 可能减少前置分类的影响，也可能使 Diagnosis 更容易遗漏跨案例差异；需要真实实验判断。v29.3 Test 分数下降不能单独定位到某条 Prompt 或某个模块，v29.4 离线验收通过也不证明它能提高 SearchQA 成功率。

相对 v28.2，本版本改变方法提示词来源并删除 Grouping；Editor 按最新要求保持同为 32,768。因此属于版本整体比较，不能把差异全部归因于 Grouping。保留 EM-only 事件意味着 EM 不变的答案变化和 F1-only 变化仍不进入 Replay Knowledge；本轮不扩大 Memory 类别。联合执行归因不是独立因果识别，单批 Retain 不证明泛化；重组出的新 Selected Skill 可能尚未在该轮执行。

评估重点是后续任务的实际表现和规则适用性，不用 Update 数量、长度或 KEEP/Retain 比例替代效果判断。已有 Test 结果参与过版本讨论，未来结果应如实说明开发背景，不将其描述为完全未被开发过程接触的盲测。
