# LMB SkillAdam 配置与离线检查

2026-10-31当前修订：[共用Actor截断自动重试](../v27/actor_length_retry_20261031/README.md)。原生优化器策略保持不变；下文初始接入和恢复验收结果保留历史语义。

2026-10-30：此前完成的是 v27 接入，尚无独立 LMB SkillAdam 配置及入口。
本次补齐原生 SkillAdam 优化器与共用 LMB Actor 的连接，未启动真实优化或 Test。

## 文件与环境

- 配置：`experiments/configs/lmb_skilladam53_epoch1_deepseek_flash.json`
- 入口：`scripts/runs/run_lmb_skilladam.py`，默认仅执行 `preflight`
- 桥接：`src/adapters/lmb/skilladam.py`
- 原生实现：`external/SkillAdam/skilladam/`，本次没有修改上游代码
- 环境：`/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python`
- 依赖：沿用 `benchmarks/livemathematicianbench/requirements.lock.txt`；`python-dotenv==1.2.4` 已存在，`pip check` 通过，本次未安装或更新包
- 凭据：真实运行时从项目 `.env` 加载 `OPENAI_API_KEY`、`OPENAI_BASE_URL`；preflight 不加载密钥、不创建模型客户端

## 参数来源

优化器参数依据本地开源代码中的 `skilladam/experiments/main_results.json` 的 LMB 节、
`methods/skilladam.py` 和 `core/feedback_loop.py`。模型及任务执行参数对齐当前 v27。

| 配置 | 本次值 | 来源 |
| --- | --- | --- |
| 优化池 / Test | 35 Train＋18 Selection＝53 / 124 | 与 v27 共用固定 ID 与内容 |
| 内容 revision | `6f53c5ff7227633ea954b2847cd590314d582047` | 已下载内容，校验原始及准备文件哈希 |
| 顺序与选项 | Train 排序后接 Selection 排序；选项 seed=42＋题目 ID | v27 与原生 SkillAdam 请求逐题比较一致 |
| 初始 Skill | SkillOpt 原生 `initial.md`，与 v27 相同 | 用户约定，跳过 Stage0 |
| batch / Gate 数据 | 10 / 与当前训练批相同，包含尾批 | SkillAdam LMB 原生配置 |
| 采样 | sequential，优化池不打乱 | SkillAdam LMB 原生配置 |
| 最大 / 最小迭代数 | 15 / 5 | SkillAdam LMB 原生配置 |
| 连续失败阈值 / patch attempts | 3 / 3 | LMB 配置 / 原生 FeedbackLoop 默认值 |
| 编辑预算 | base=4，minimum=1，beta=0.9，metric=exact_match，v_max=0.05 | 原生自适应预算 |
| Gate | EM 增益至少 0.08，原生 drop 边界 0.08 | 原生 LMBAcceptanceGate |
| Prompt / 压缩 | `lmb-main-result` / deterministic | 原生 LMB 配置 |
| Momentum / history | 原生 Momentum；history_turns=null | 保留原生实现 |
| optimizer_context_limit | 150000 | 原生对话历史重置阈值 |
| Actor / 优化器模型 | `deepseek-flash`，DeepSeek 官方接口 | v27 |
| 模型参数 | temperature=1.0、reasoning_effort=medium、thinking=enabled、max_tokens=16384、timeout=300s | 与 v27 Actor 和 Editor 相同；16384 也符合 SkillAdam 公共输出预算 |
| Actor 并发 / Test 并发 | 20 / 16 | v27 共用 Actor |

原生顺序 sampler 只遍历一次，实际生成 10／10／10／10／10／3 六批；
max_iterations=15 只是上限，不会重复优化池。保留原生早停，因此可能在第 5 批后停止。

上游配置说明将 Gate 标为 `lmb-main-result`，但 Runner 接收的运行时名称为
`main-result`；本配置使用后者，仍选择同一个原生 LMB Gate。

`optimizer_context_limit=150000` 是原生按字符数估算 token 的历史重置阈值，
超过后保留当前 Skill、Momentum 和状态并重建优化器对话。
它不是 v27 的 `context_window_tokens`，也不是对服务商真实上下文窗口的声明。
不把 v27 五模块的 32768 输出预算混入单一 SkillAdam 优化器。

Actor 直接复用 v27 的单轮 HTTP 执行与归档恢复：最多 6 次技术尝试、SDK 重试 0、
连接超时 10s；正常stop的错误答案和不可解析答案评分，不重采样。当前length先归档再按原消息重试，与技术错误共享六次总尝试；耗尽停止，不评分。
优化器传输使用 SkillAdam 原生 OpenAI-compatible 实现，保留 SDK 的 max_retries=2
默认值。这与 Actor 的重试层不同；patch_attempts=3 仍由原生优化器管理。

## 原生与共用边界

Runner 在原生控制流程外增加初始 checkpoint、轮内 I/O 回执、整体恢复校验和用量去重；
rollout 目录绑定与 Actor 提示词沿用当前 v27 适配。采样、优化器 Prompt、确定性压缩、
补丁解析与应用、自适应预算、Gate、Momentum 工具与状态、checkpoint 格式和早停继承原生实现。
原生 SkillAdam 会分别执行训练 rollout、Gate Parent rollout、Gate Candidate rollout；
有效一批 10 题通常对应 30 次 Actor 作答，不采用 v27 的 Parent 复用策略。

Actor 使用 v27 数据加载器和执行器。原生 Adapter 收到未打乱选项，执行一次原生打乱，
并在调用 Actor 前验证请求文本及正确标签与 v27 一致，避免二次打乱。
向原生结果对象投影普通 assistant content、公开请求及评分所需元数据；
不投影 `reasoning_content`、原始响应中的隐藏字段、定理或证明草图。
原始响应仍保存在共用 Actor 审计归档中。

训练入口只接收 53 题优化池，不自动运行 Test。124 题保持独立，后续统一评测可使用
v27 的 `run_evaluation` 与输出的 `native/final_skill.md`。本次未新增自动 Test 行为。
配置、数据内容、初始 Skill 和相关源码哈希在真实运行目录冻结；恢复时必须一致。
Actor 批次恢复复用共用归档校验；整体恢复先校验所有已登记阶段，再进入原生 checkpoint 流程。

按用户确认，暂时保留上游证据压缩和优化器 Prompt：压缩轨迹不显式补入完整选项、
正确标签或 theorem／sketch，Prompt 中已有的 Hidden Reference 声明也保持不变。
这是已核实的上游行为及已知限制，本轮恢复修复不处理它。

## 离线验证

恢复修复后的最新结果见 [恢复修复与回归验收](LMB_RECOVERY_FIX_20261030.md)。
补充两个恢复边界后，独立 LMB 环境29项离线测试通过，网络连接尝试和真实模型请求均为0；
本次只补测试与文档，原生优化器实现、参数、证据压缩及 Prompt 不变。
以下为最初接入时的历史验证，不代表对中断恢复所有路径的验证。

[验证报告](../../../artifacts/verification/lmb_skilladam_config_20261030/validation.json)记录 8 项测试通过、
网络连接尝试 0、真实模型请求 0，原始与准备数据哈希未变。
[冻结的预检查快照](../../../artifacts/verification/lmb_skilladam_config_20261030/preflight.json)保存配置、
177 题映射、批次、数据与源码哈希。检查覆盖：

1. 开源优化参数、53/124 划分、六批顺序及全部 177 题请求/答案映射。
2. content-only 投影、评分与 token usage，完整 Actor 缓存重用。
3. Actor 完成归档损坏时零新增请求，未完成批次只补齐待执行任务。
4. 不可解析答案与 length 空内容均记 0 分，不语义重试。
5. Test 或请求漂移在 Actor 调用前被拒绝。
6. 原生 EM Gate 的保留与接受边界。
7. 使用 httpx MockTransport 检查实际 SDK 序列化出的 DeepSeek 参数和工具调用解析。
8. 用合成题、固定模拟响应贯通原生补丁、Gate、Momentum 工具调用、最终 Skill 发布和已完成 checkpoint 恢复。

另复跑 [v27 原有离线验收](../../../artifacts/verification/v27_after_lmb_skilladam_config_20261030/validation.json)：53 项测试全部通过，网络连接尝试 0。
这些结果证明配置及离线接入，不代表真实模型服务连通性、生成质量或 benchmark 成绩。

仅执行离线预检查：

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/runs/run_lmb_skilladam.py preflight
```

重跑新增离线验证：

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/verification/verify_lmb_skilladam_offline.py --output artifacts/verification/lmb_skilladam_recovery_boundaries_20261030
```

真实训练需要显式 `run` 子命令和 `--output experiments/baselines/lmb_skilladam/<run-name>`，
恢复还需 `--resume`。本次没有执行这些命令。

## 2026-10-31 Actor输出上限修订

当前共用Actor为49,152；SkillAdam原生优化器仍为16,384，SDK2／patch3不变。[配置修订与验收](../v27/actor_49152_20261031/README.md)。此前表格中的Actor16,384属于历史配置。

## 2026-11-01 优化器引用的 Actor 协议同步

本地 `Runner` 将优化上下文中的 `vendor_prompt` 绑定到共享 Actor 的基础协议，
去除动态 Skill 插入。原生修改建议和 Momentum 更新模板均引用该上下文，因而准确
展示当前 answer-only 要求。此前本地只替换了 Actor 请求，优化器仍看到上游允许
逐步解释的协议；本次仅修正这项描述不一致。

没有新增调用前一致性检查。上游文件、轨迹压缩（包括选项正文处理）、独立推理字段
处理、Actor 协议、评分及训练配置均未修改；历史实验档案保持原样，未重新训练。

已有合成完整迭代测试增加了对修改建议和记忆更新实际 system 消息的离线核对：
修正前复现协议不符，修正后全套 33 项离线检查通过，网络尝试和真实模型请求均为 0。
见[验证报告](../../../artifacts/verification/lmb_skilladam_optimizer_protocol_20261101/validation.json)。
