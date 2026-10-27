# V3 实验设计与来源边界

## 第一阶段

候选是用户提供的 `/Users/didi/Downloads/v23_4_replay.md` 的逐字副本。没有修改主 Prompt，也没有新增模型角色、输出字段或生产学习阶段。

R05/R06 的 User 来自 P6 实际成功请求，并与 P4 冻结 messages 完全一致。System 只替换主学习 Prompt 前缀，后续 Actor 背景、Memory v3、Pair 和多 Knowledge 格式说明逐字保留。User 分别为 884,531 / 857,205 字符。冻结证据见 `config/INPUT_COMPARISON.json`、`config/freeze.json`。

使用已有 deepseek-v4.1-flash、temperature=1、thinking enabled / reasoning_effort=medium、初始 max_tokens=32768、非流式配置及原传输程序。每个案例取得第一份结构合法结果后停止。保留原最多三次技术/格式重启，length 后可将输出上限增至65536；不因语义评价重新采样。上限变化须在结果报告单独披露。

P4 基线为 P6 保存的首份合法结果，V2 为 `conditional_learning_001` 保存的首份合法结果。两者均不重新调用。比较的是有限样本的适用性，不是统计显著性或严格控制采样的因果效应。

## 第二阶段选择：离线受控再次修订

R05 实验 Candidate 的哈希为 `111613e3…`，R06 Parent 为 `eab4a195…`，两者不同。R06 Parent 实际来自正式 v23 R05 接受的 Candidate。R06 实验执行于10月21日，R05实验执行于10月22日，时间顺序也不能支持 R05→R06。已有7份保存的 Parent 文件中未找到接续实验 R05 或 R06 Candidate 的边。完整哈希和身份见 `LINEAGE.json`、`ALTERNATIVE_LINEAGE_INVENTORY.json`。

固定选择正式 v23 R05 的另一批真实配对反馈作为离线受控第二轮材料。它与实验 R05 的 Parent 完全相同（`06eccab6…`），前置 Memory 均为正式 R04 的同一快照；但实际 Candidate 不同。正式 R05 的20条原始轨迹已经通过现有 facts/pair 逻辑重建，与冻结 bundle 一致；实际 Diff、Candidate 和 Plan 也与当时 Editor 文件一致。

正式 R05 的这些执行 ID 与首轮实验 R05 输入中的当前及历史各轮执行 ID 无交集。它们是同样10个任务实例上的另一次真实执行，不能说是新的独立任务样本；它们也曾作为独立 R06 对照臂的旧历史，但没有被本条 R05 首轮 Memory 学习。这里的“不重复学习”以受测的隔离 Memory 链为边界。

第二次真实模型调用读取首轮 R05 原样提交的多 Knowledge 隔离 Memory，以正式 R05 的 Actual Diff、Plan 和配对事实作为当前证据。使用现有 Memory v3 及真实 Pair 解析，不补充模型未见的旧历史状态，不人工修复 Knowledge。

**该反馈实际发生在10月19日，因此离线学习的纳入顺序与执行时间相反；它不是新 Candidate 接续旧 Candidate 的自然演化。** 本测试只能回答：对于同一个实际 Parent 上另一种有独立执行证据的编辑，Replay 能否再次修订真实多 Knowledge、保留和校准历史。不能证明在线闭环、真实时间上的持续提升或两次编辑可叠加。

选择在读取 V3 首份合法结果前固定。第二轮仍最多一份合法结果，失败按相同技术规则处理；不按输出质量改选材料。

## 评价和保护

结构合法与语义采用分开评价。每个 Knowledge 的 Evidence 可解析不代表其文字被支持。结果中区分观察遗漏、错误范围、过强解释，以及因引用变化导致的下一轮详细状态可见性损失。

所有 Memory 提案只提交到本目录的隔离副本；检查重载、幂等性、历史归档不变、引用与窗口、未来 Replay Pair 和固定 Preconditioner 输入投影。投影是兼容性与规模探针，不是新的 Diagnosis/Preconditioner 调用，更不是 Skill 效果证明。

生产、默认 Prompt、正式 Active Memory、旧实验和原始执行归档通过哈希保护。本轮不启动 Actor/Editor，不优化 V4，不自动发布任何 Memory。
