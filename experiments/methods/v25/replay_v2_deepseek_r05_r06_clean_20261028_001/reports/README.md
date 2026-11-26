# Replay v2：DeepSeek R05 / R06 干净输入单模块对照

2026-10-28。结论：**局部改善，但没有解决全部四类问题。没有整体过度保守；有一处新增的不必要不确定性。R05 数值案例仍遗漏关键程序差异，并出现新的过度概括。**

## 实验范围与完整性

- 新运行只包含 Replay v2；基线为原训练 R05 / R06 的 v1 原始 Replay 输出，不是发布后的 Memory。没有重跑 v1。
- 两轮均从原始 system/user 两条消息开始，没有旧回答或旧修正反馈。R05 技术重试也只有这两条消息。
- 逐项校验原始 bundle、模型 user 输入、Memory、执行上下文和调用参数相同；system 中只替换 Replay 模板。R06 仍使用当时的旧 M9，未串入本次 R05 输出。
- 模型 `deepseek-v4.1-flash`，原内网 endpoint；`max_tokens=49152`、`temperature=1.0`、`reasoning_effort=medium`、`thinking.type=enabled`、`stream=false`、超时 300 秒、每轮最多 6 次请求均不变。
- R05：第一次 `ReadTimeout`，原机制用相同请求重试，第二次输出有效。R06：第一次输出有效。共 3 次新 API 请求、2 份完整有效输出；没有格式错误，因此没有触发格式修正。
- 原生 `load_replay` 重读两份结果成功；逐请求重建一致。冻结的生产契约、原 campaign 和预先固定的运行文件哈希均未变。Preconditioner 默认仍为 v7。
- 没有调用 Actor、Verifier、Repair，没有发布 Memory，没有运行完整链路、训练或测试集评估。原始评分只是输入证据，未重新产生。

校验见 [validation.json](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/validation.json)，预先固定的标准见 [review_criteria.json](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/review_criteria.json)，输入与基线位置见 [manifest.json](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/manifest.json)。

## 四类问题的对照结论

| 检查项 | 改善 | 仍存或新增问题 | 判断 |
|---|---|---|---|
| 代码、执行事件、评分的含义 | R05 文本不再把错误坐标当作未改写事件，也不再把 16/16 当作 16 次转换；R06 标识符改为相同逐格通过/失败状态 | R05 数值仍把有条件的 min/max 查找写成确定读取到实际边界 | 部分改善 |
| 实际程序差异及共同行为 | R05 文本承认数值解析也变化；邮编不再声称 unmatched 填充值不同 | 数值仍漏掉正负号到加减动作的反转，还把 Parent 一个分支的行为扩成整个程序 | 关键目标未解决 |
| 经验范围与待验证假设 | 保留真实收益、未测得收益和可迁移的机制解释，没有因联合干预而拒绝全部归因 | R05 将完整键匹配、正则抽取和子串匹配混在一起，错误声称所有 Candidate 都增加空白折叠和 case-folding | 有效假设保留，但支持范围仍不稳定 |
| 主张的事实对应 | 原始邮编 unmatched 错误消失，文本评分口径修正 | 新增锚点条款前后矛盾、Q4 已知分支被写成未知，以及数值分支概括失真 | 不能认定事实核对已可靠落实 |

下面的 K 编号是各版本输出中第一个 Entry 的一基 Knowledge 编号，机器位置为 `/entries/0/knowledge/(K-1)/text`。
完整文本见 [outputs.md](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md)；证据摘录直接来自当次已见模型输入，附原始文件和 JSON pointer，不额外读取工作簿。

## R05：文本改善，数值问题仍是主要缺口

### 文本匹配：明显改善，但不是根因已确认

v1 K2 把 E10/E11 判错写成 Parent 没有改写，称 Candidate “converting all 16 graded cells”，并称其为清晰的单条规则收益。

v2 K2 记录的是 14/16 → 16/16，保留 case/whitespace/substring 改变，并明确数值判断也变了，包括 accounting-style negatives，因此两部分贡献尚不能分离。它没有再断言 E10/E11 的运行分支，也没有声称 16 格全部改写。这是本次最直接的改善。

Parent 已有 numeric-looking string 处理和 `1e-9` 整数容差；v2 没有逐一重述共同机制，但也不再把接受数值字符串当成 Candidate 独有的新增能力。无需把“没有列全所有共有行为”再判为失败。

证据：[v1 K2 / v2 K2](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md)（行 19 / 73）；[P1](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 43 起、Q1 行 794 起。E10/E11 及对应 F 值在五行预览之外，运行输出没有这些值，故仍不能确认具体贡献；这是输入不足，v2 此次处理得更合适。

### 数值平衡：两个原问题保留，且新概括损失了分支条件

v2 K5 仍称 Candidate “read the min/max constraint rows from the full sheet”，并将实际读取边界和逐格传播称为最清晰的条款对应收益；但当次记录只确定程序实现了标签查找、数值行启发式和 `0/inf` 回退，没有给出实际选中的边界行或值。不能由 189/189 独立确认使用了哪个分支。

更关键的是，v2 仍没有记录已在输入代码中明确存在的变化：

| 分支 | Parent | Candidate |
|---|---|---|
| 残差为正 | 从 unit5 到 unit1 减少 | 从 unit1 到 unit5 增加 |
| 残差为负 | 从 unit1 到 unit5 增加 | 从 unit5 到 unit1 减少 |

这个竞争解释不需要新增证据。它应与边界处理一起保留，不能只按 Skill 新增条款组织归因。

v2 还把 Parent 写成 “pushed the entire residual into the first eligible cell”。真实代码仅在负残差加法分支这样做；正残差分支原本就会沿多列扣减、更新剩余量。v1 K4 至少分别描述了这两个分支，v2 K5 的压缩反而丢失了关键条件。

因此，**未选中边界行属于输入证据不足；漏掉正负号反转、概括错 Parent 分支属于已见事实利用不充分。** 不能统一归为没有日志。135/189 → 189/189 的收益应保留，但收益的解释仍不可靠。

证据：[v1 K4 / v2 K5](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md)（行 31 / 91）；[Parent 正负分支](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 202、213；Candidate 查找与回退行 941–1068、加减分支行 1079 起。

### 邮编：旧错误消失，但要区分原始 Replay 与发布后 Memory

v2 K3 不再说两边 unmatched 行写法不同；仍保留 1456/1460 → 1460/1460 和空白归一化差异，并记录列选择的实现差异，归因有所保留。保留“按语义保留一个分隔空格”的修复方向是合理探索，不需要已隔离因果才能提出。

但这只能算相对 **v1 原始 Replay** 的改善。v1 后来的 Verifier/Repair 已删除 unmatched 错误，最终 M9 本来就没有那句话。本轮没有发布 Memory，不能宣称最终 Memory 又新增修好了这一项。

此外，v2 的 “sheets and columns ... instead of fixed positions” 不够精确：Parent 的列是固定的，但选 sheet 已按名字识别；Candidate 改用 header。这种实现差异也不等于两边实际选中了不同列或 sheet。

证据：[v1 K8 / v2 K3](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md)（行 55 / 79）；[P12/Q12](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 380 / 1212；旧发布结果路径见 manifest 的 `v1_published_output`。

### 新增的过宽归类：将不同操作统一写成子串能力

v2 K4 把关键词扫描、材料面积汇总、hashtag 提取一起写成已有 case-insensitive substring 能力，并称 Candidate 的变体都添加了 whitespace collapsing / case-folding。

核对后：P13/Q13 是归一化后的完整材料键聚合、查找；P15/Q15 都用 `#(\w+)` 正则提取，Q15 并没有添加上述空白折叠和 case-folding。它们通过评分是事实，但不能作为同一种“容错子串操作”的共同实证。

这不是要求禁止泛化，而是泛化前要保留操作语义：关键词包含、完整键相等、正则抽取不能直接互换。这里不缺输入代码，属于事实归类错误，进而扩大了经验的支持范围。

证据：[v2 K4](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 85；[P13/Q13、P15/Q15](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 538 / 1351、692 / 1518。

## R06：同分含义修正，新增条目仍需事实核对

### 标识符：不再把评分相同写成值相同

v1 K4 由 15/17、相同 H12/H13 错误坐标推成 “changed no graded cell”。v2 K4 改成 “same pass/fail pattern on every graded cell” 和 “no measured change”。原评分的错误列表完整，故这一表述成立；它没有推断错误格的实际值相同，也没有推成后缀保留普遍无效。

它继续保留完整标识符与数字前缀的机制区别，说明当次记录未证明同一个数字基础号出现多个后缀。这是合适的输入边界。

仍有两点范围风险，不能算已确认的新事实错误：

- “the two shared mismatches are not explained by the keying difference” 最稳妥的读法应是尚未建立解释，不能被下游读成已经排除 keying 的影响。
- 两边还存在 item 键选择优先级不同：Parent 优先 item name，Candidate 优先 item code、找不到再回退 name。v2 未保留这一竞争差异。当前不能证明它影响了 H12/H13，但也不能将差异缩成只有后缀处理。

证据：[v1 K4 / v2 K4](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 129 / 159；[P15/Q15](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) 行 328、344 与 1363、1414 起。

### 锚点与合并：有效经验保留，锚点末句存在矛盾

v2 K2 保留表头 I2 → I3、数据整体下移及 4/12 → 12/12；K3 保留按已有来源名跳过 Jack → 追加所有要求来源、最终全对。它没有因单任务或联合修改而拒绝这些较强的机制解释，因此没有出现整体保守化。

不过 K2 末句把 “not writing above the stated start” 与 “not clearing pre-existing answer-region cells” 一并说成本例没有区分机会，因为原格子为空。这把两个条件混了起来：

- 原格为空，确实没有测到清空已有内容的危害。
- Parent 明确在 I2/J2 写表头，Candidate 没写；它们本来就位于 I3 之上，而且 I2/J2 在 Parent 错误坐标中。因此“不往起点上方写”的行为差异实际存在，不能因原格为空而排除。

这是在同一条中先正确描述差异、后又过度排除条款作用的事实对应问题。

证据：[v2 K2](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 147；[P7/Q7](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) 行 82、137、865 起。

### Q4：局部出现不必要的保守判断

新增 K7 正确利用 Q3 的已知 sheet 名与代码判断 `Desired outcome` 分支执行，说明 v2 并非一律要求分支日志。

但同条又把 Q4、Q11 合并称为 “without an established branch outcome”。Q11 所需完整示例块不在预览中，保留分支不确定性合理；Q4 则不同：当次预览已给出 C2=`=A25`、C3=`=A41`，代码读取这两格并解析为 25、41，从而确定走 `start_row=row2, step=row3-row2` 分支。无需追加日志就能判断使用了示例公式确定起点和间隔。

因此 Q4 是局部的过度保守／已知事实未利用，不能泛化为整个 v2 不敢提出经验。也不能把明确由任务提供的示例区域笼统当成非法来源；本轮只核对证据和行为。

证据：[v2 K7](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 177；[Q3/Q4/Q11](../../../../../artifacts/methods/v25/analysis/replay_v2_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) 行 435、720、983；Q4 预览行 737 起，分支行 779 起。

## 有无整体过度保守、输出膨胀

未出现空输出、拒绝归因、要求最低案例数或必须先有独立因果证明的现象。R05 仍保留三个提升案例、公式缓存成功和技术失败后恢复；R06 保留两个提升、标识符未测得收益以及多种能力保持。R05 文本经验承认贡献无法分开，同时保留修复方向，符合目标。

| 轮次 | v1 Knowledge 数 | v2 Knowledge 数 | v1 / v2 Knowledge 正文英文空白分词数 |
|---|---:|---:|---:|
| R05 | 8 | 6 | 835 / 767 |
| R06 | 4 | 7 | 568 / 1165 |

R05 不再单列全部直接值成功列表，但仍保留总体表现和公式／直接值对照，不能仅凭少两条认定保守。R06 新增条目覆盖保持能力、共同失败、示例依赖行为，但正文约翻倍，并带入 Q4 等新问题。**条目变多不等于质量提高，条目变少也不等于经验被压制。**

成功请求的 completion tokens（含 reasoning）为 R05：17,150 → 19,632；R06：28,307 → 41,571。R05 另有一次超时，其服务端 token 用量未知，不能给出完整总成本。这里只是单次运行记录，不据此断言 v2 必然增加延迟或超时率。

## 对本次结果的判断

1. v2 对若干明确的证据口径错误有效：R05 文本的评分数／改写数混用、R06 同分／同值混用都消失了，合理经验没有整体被压掉。
2. 最重要的剩余问题是实际程序比较未稳定执行：数值正负号反转仍遗漏，且压缩时丢失分支条件。输入已有相关代码，不能靠继续补输入解释这一点。
3. 不确定性校准在两端均有失衡：R05 未知边界分支写得过实，R06 Q4 已知分支又写得过虚。更严厉地统一要求“谨慎”不能直接解决这种问题。
4. 本轮只能证明这两份输出的改善与缺口。temperature=1、没有重复采样且使用归档 v1，不足以把每个差异都因果归给 Prompt，也不证明后续 Diagnosis/Preconditioner/训练分数会改善。

本次没有继续修改 Prompt 或生产代码。全部新产物位于当前独立实验目录；历史 v1、发布后 Memory 与默认 Preconditioner v7 保持原样。
