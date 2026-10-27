# V23.4 第五步：小规模真实生成与语义验证

发送前协议，2026-10-21。用户授权执行第五步，并允许 HTTP 429、reasoning/输出长度及程序性契约失败后的三次重启。解释为每个逻辑阶段首次尝试之外最多三次，合计最多四次 HTTP；不同尝试分别存档，取首次结构合法的结果。Keep、撤回、Editor 空/null Patch、语义不理想均不触发重采样。

## 冻结范围

- 路由沿用已有配置：内网 deepseek-v4.1-flash，temperature=1，thinking enabled，reasoning_effort=medium，stream=false，连接/上传 60 秒、读 300 秒。
- 初始 max_tokens=32768。只有 finish_reason=length 后才升到 65536；其余重启保持预算。65536 是预声明的尝试上限，不声称服务一定支持；400 等非恢复性 HTTP 错误停止该阶段。
- HTTP 408/429/5xx、连接或读取异常、返回 JSON/Schema/引用/严格 Patch 校验失败允许重启。退避 15/30/60 秒。软件配置/输入/源码冻结不一致不重试；不改写失败输出，也不向模型追加修复提示。
- 代码与输入在 freeze.json 记录 SHA256；冻结后如需修改实现必须另记修订，不能覆盖失败产物。凭据只在发送时读取，不归档 Authorization。

## 案例与顺序

第一组四个冻结案例：R05 是既有 V23.3 真实 Diagnosis 和执行/Memory；R06 使用既有 V23.2 原始真实 Diagnosis（不使用人工 multiline 改写）、执行/Memory。它们是已经参与设计的开发材料，不是 held-out 或最终 Test。A3 扩大许可、A5 有反例的 Keep 来自第四步合成材料，仅用于覆盖分支，不计作真实任务效果。

每例一次 Preconditioner 逻辑生成，结构合法且存在 Effective Plan 时一次 Editor 逻辑生成。全部 Keep 照常进入 Editor，合法全部撤回记录停点。不得要求模型输出指定 focus 或编辑数量。合成案例使用真实执行背景的结构模板，但说明这是合成决策材料，没有真实 Actor 观察或收益。

额外一个合成证据变化案例 A3_quality_shift：Original 和当前事实不变，历史替代来源只满足粗略而非精确要求。检查理由是否承认迁移限制，不强制 Patch 必须变化。只生成 Preconditioner，不跑 Editor，不宣称消除了采样噪声。

核心四例没有出现阻断性的系统性语义问题后，在 R05 同一真实当前批次上生成新版 Diagnosis，再执行 Preconditioner → Editor，共三个逻辑阶段。新 Diagnosis 不要求复制旧 Plan。

另对 R03 已有、可重载的真实 Replay 输入单独用新版 Replay Prompt 生成一次知识，检查实际 Diff、条件和配对响应。仅保存 Memory 提案，不提交 Active Memory；绝不为本轮未执行的新 Candidate 编造执行反馈。

总上限 13 个逻辑阶段、52 次客户端 HTTP 尝试。顺序发送，独立阶段可以在检查准备阶段并行处理本地材料；不并行发送请求以避免放大限流。所有失败算入尝试与用量，费用字段缺失记未知，不展示内部 reasoning。

## 实验适配边界

冻结案例不是新生成的 V23.4 Diagnosis，不伪造其生产归档。实验入口读取并核验旧响应与来源，调用正式 V23.4 Prompt/Memory 投影/输出校验/编译函数；Editor 使用正式 V23 Prompt 与严格 Patch 引擎。输出是独立实验归档，每次成功均重解析并验证。新版 Diagnosis 与 Replay 也使用正式 Prompt/Schema，但不把实验归档冒充生产加载器目录。

审查实际输入、Adjustment、Effective Update、Candidate 与 actual.diff，逐项记录历史适用性、D/S/C 作用、改善作用、探索未知、Keep 解释、Update Patch 与 Skill 的双向忠实性。评价者为当前同一分析者，非盲评或独立双评，不增加 Judge。语义失败不通过技术重启隐藏。

不执行 Actor、Gate、完整消融或默认方法注册。此步回答模型能否按设计生成，不回答持续提升成功率或历史的净因果收益。
