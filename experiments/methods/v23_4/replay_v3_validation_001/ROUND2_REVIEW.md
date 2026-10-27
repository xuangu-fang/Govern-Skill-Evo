# 多 Knowledge 第二次真实修订：结果与边界

本轮是一次真实 Replay 模型调用，采用另一批真实执行反馈；但实验组织是**同一Parent上的不同编辑、离线重新排序学习**，不是自然时间顺序的Skill闭环。来源、执行时间、hash及Pair独立性见 `LINEAGE.json`、`METHOD.md`。第二轮没有使用R06的V3结果或Memory。

## 实际发生了修订

首轮原样隔离Memory包含M10（三条Knowledge，精确对象主题）、M11（两条，搜索主题）、M12（一条，合法动作主题）。第二轮首份合法输出是 `round2/runs/ROUND2_replay/attempt_002/parsed.json`：

| 首轮条目 | 第二轮决定 | 结果 |
|---|---|---|
| M11 / 2 Knowledge | revises=[M11] | M13 / 4 Knowledge：加入正式R05当前响应，保留首轮实验R05与更早历史搜索比较 |
| M10 / 3 Knowledge | revises=[M10] | M14 / 3 Knowledge：整合当前与历史精确对象响应 |
| M12 / 1 Knowledge | 没有修订 | 原样保留。当前正式R05的Diff没有新增Admissible Actions，因此不修订本身合理；其中旧解释问题也继续存在 |

不是只新增重复Memory，也不是再次把旧字符串转换成单条数组。输入确实包含首轮真实产生的多Knowledge，输出确实替换这些条目，原样提交、重载及未来投影均通过。

## 历史保持与校准分离

历史bread的改善与退化、plate38成功/50失败、首轮循环失败及正确目标获取能力仍然得到表达。两个被替换条目的旧Evidence均全部进入新数组，未丢失任何旧引用。没有观察到本轮完整数组替换导致明显的重要历史对照遗忘；这不证明机制普遍不会遗忘。

但是历史校准失败：首轮的absent解释、把sinkbasin2新实例当成新type、历史cup“被加热”等问题均被保留。模型仍可看到完整历史动作序列，因此不能把所有继承错误归因于窗口缺失。更严重的是，新反馈被套入已有解释，而不是据它纠正已有解释。

## 关键来源错配及其实际影响

M14/K1正确引用了首轮实验R05的完整前缀，描述其Candidate取、清洗、放置近似knife；随后却说**本次**Candidate又在Q7:9/17/19重复同样动作。

| 来源 | Q7:9 | Q7:17 | Q7:19 |
|---|---|---|---|
| 首轮历史 `v23_4_R05_replay_v3_validation_001/Q7` | take knife 1 from drawer 1 | clean knife 1 with sinkbasin 1 | move knife 1 to drawer 1 |
| 第二轮当前 `Q7` | go to drawer 2 | go to drawer 2 | go to drawer 4 |

第二轮当前Candidate完整50步没有take/clean/move knife动作；Parent却确实在P7:5/7/9取刀、清洗、放回。因此当前事实支持“Candidate避免了Parent的近似对象操作，但仍未找到目标而失败”，而输出虚构为两侧都操作knife，从而错误强化“两次措辞都没能抑制替代”的判断。

这是会改变D/S/C更新方向的实质性错误，不是措辞瑕疵。当前与历史两个事件均在实际发送的model_input中；所有引用ID又都合法，所以结构校验通过不意味着动作绑定正确。原始对照保存于 `ROUND2_EVIDENCE.json`，没有改写模型输出。

搜索条目也继续发生范围升级：M13/K1把三组比较归纳成Parent没有到达目标所在family，但当前butterknife Parent曾访问countertop1，只是没到countertop2；mug Parent实际到达diningtable并16步成功，Candidate是4步成功。新比较确有价值，但“新的位置/更快的路径”不能直接写成“首次进入整个类别”。

受控的离线学习顺序、相同任务与相同P/Q编号、相邻旧新编辑会带来关联负担。本次未设置控制组，不能据此确定混淆原因，或推断自然连续更新必然产生相同问题。可以确认的是：原样多Knowledge在这一次再次修订中没有可靠地用当前证据校准旧解释。

## 下游可用性与规模

| 指标 | 第二轮前 | 第二轮后 |
|---|---:|---:|
| Active Memory / Knowledge | 8 / 11 | 8 / 13 |
| Knowledge文本字符 | 18,505 | 22,230 |
| Memory v3字符 | 825,726 | 1,018,759 |
| 完整trace动作数 | 1,959 | 2,338 |
| 展开详细步骤 | 541 | 697 |
| 历史可验证Pair | 41 | 49 |
| 固定Preconditioner User字符 | 1,008,598 | 1,201,631 |

Memory v3约增加23.4%，固定Preconditioner User约增加19.1%。增加包含真实新反馈与保留旧认识，不能全称为冗余；但本例的部分增长同时保存并强化了错误解释。旧引用均保留说明检索可追溯，并不能保证语义可靠。

第二轮初次输入364,613 tokens，触及32,768输出上限；按既有规则重试后输入364,569、输出50,587，合法完成。请求事实与Prompt未变化，usage按服务返回记录，不自行用字符数换算。没有语义失败重采样。

**结论：验证了真实多Knowledge再次修订的技术路径和历史保留能力，未验证可靠纠错；本轮原样Memory不可直接采用。** 不发布Active，不人工修补，不启动下一轮Prompt优化。
