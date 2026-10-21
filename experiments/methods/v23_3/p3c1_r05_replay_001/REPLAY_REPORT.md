# R05 Replay：因服务端限流中断的部分结果

**没有完成三方行为比较。** 已启动9/12条Episode：5条原生成功，4条HTTP 429技术中断；剩余B/P6、B/P7、B/P10按冻结停止规则未启动。无重试、无任务重启、无策略修补。预注册12条全部列出，没有筛除不利任务。

## 原生结果与配对

“步数”为已执行环境动作数；技术中断不记任务失败，成功未知。括号注明发出但被拒绝的下一次决策。

| Task | Parent成功 | A成功 | B成功 | Parent步数 | A步数 | B步数 |
|---|---|---|---|---:|---:|---:|
| P3 / val:0003 | 是 | 是 | 未知：429 | 4 | 4 | 0（首请求拒绝） |
| P6 / val:0006 | 是 | 是 | 未启动 | 10 | 8 | — |
| P7 / val:0007 | 未知：429 | 未知：429 | 未启动 | 19（第20请求拒绝） | 8（第9请求拒绝） | — |
| P10 / val:0010 | 是 | 未知：429 | 未启动 | 14 | 5（第6请求拒绝） | — |

Parent：完成3/4条，完成的3条均成功；A：完成2/4条，完成的2条均成功；B：启动1/4、完成0条，成功率不可估。不得把4条技术中断和3条未启动算作行为失败，或仅凭完成子集声称方法成功率100%。所有已执行步骤无50步触顶，72个执行动作均合法，未出现Nothing happens或fallback。

原 `verify_record` 对9份轨迹均通过，包括保留pending请求的中断轨迹；这些轨迹的 `episode_complete=false`、`native_success=null` 被保留。所有已启动Episode初始观察/完整候选与预检一致。原 verify_pair 及额外request_policy/实现摘要核查确认已启动的Parent–A四对与Parent–B/P3配置一致，但只有 **Parent–A/P3、P6是双方完成的有效结果配对**。其余是条件相同的截断记录，不能比较完整结果；没有一个完整三方配对。

两组都使用同一游戏/manifest、seed42、ALFWorld0.4.2、TextWorld1.7.0、同模型/route/Prompt/两步历史/50步协议与固定Skill。旧外网Parent不混入统计。逐项结果和配对核查见 [analysis.json](analysis.json)，实际请求/轨迹/native反馈在 episodes/{Parent,A,B}/{P3,P6,P7,P10}/。

## 逐组观察（先独立记录）

### Parent

- P3：:1到diningtable，:2取mug，:3到sidetable，:4交付成功，没有循环。
- P6：:1先到sinkbasin，:2 countertop1，:3 countertop2发现butterknife，:4取物；:5到drawer1但未打开，:6回sinkbasin，:7清洗，:8返回drawer1，:9打开，:10交付成功。成功保留精确类别和必要处理，存在提前去目的地的额外访问。
- P7：:1–14依次访问/打开drawer1–7，:15–17检查countertop1–3，:18–19又回drawer1/2；看到knife但已执行前缀中没有取走替代物。第20请求429，不能推断最后会失败、成功或替代。
- P10：:1–2检查fridge，:3 countertop1，:4–5到/查看cabinet1，:6–7回访fridge/countertop1，:8到diningtable发现apple；:9取物、:11cool、:14放入microwave原生成功。部分重复没有带来目标，但取得目标后的fridge回返是必要处理。

### Candidate A

- P3：四步动作及环境反馈与新Parent相同，准确取mug并交付。
- P6：:1 countertop1→:2 countertop2发现准确butterknife→:3取物→:4 sinkbasin→:5clean→:6 drawer1→:7open→:8move。检查两个同类表面的不同实例，没有近似物品操作、无效导航或提前去目的地。
- P7：:1–3先查countertop1–3，:4–5查cabinet1，再:6–7查drawer1，:8到drawer2。相比Parent前缀，观察到更早的同类表面扩展和跨类切换；看到knife后下一步离开，没有操作替代物。第9请求429，尚未找到butterknife，不证明其不存在或已实现可靠防替代。
- P10：前四步与Parent相同；:5直接到diningtable看见apple，Parent到:8才看到。第6请求429，**发现目标但未取得/处理/交付是技术中断，不能归因于步数耗尽或过强策略**。

### Candidate B

P3已完成reset，但第一次模型请求即HTTP429，0个环境动作；其余未启动。没有B的有效动作、成功或退化证据。不能把它当作No Skill/No Change轨迹，也不能称其稳健或无效。

## 配对行为与指标解释

| 完整配对 | Parent → A | 可以报告 | 不可归因 |
|---|---|---|---|
| P3 | 4步成功 → 4步成功；同动作序列 | 当前样本内保留该成功路径 | 未证明搜索新规则改进策略，也未检验其困难条件 |
| P6 | 10步成功 → 8步成功 | 减少2步；准确目标、清洁、交付均保留 | 差值不能单独归于Preconditioner、同类覆盖或Editor；单次随机样本 |

P6两步差值可具体对应：Parent有早期sinkbasin访问和清洁前的drawer目的地访问；A直接从两个countertops搜索后取物、清洁、交付。不是笼统“少回访就是更好”。Parent的清洁/交付所需返回同一位置是有效动作，不能计为有害循环。

自动统计仅为描述：不同到达位置数 Parent P3/P6/P7/P10 为2/4/10/5，A为2/4/6/4；不同长度的截断前缀不可比较覆盖优劣。`same_location_observation_revisits` 只计相同导航位置且返回文本相同，Parent P6/P10各2次，其余0；它既可能计入有效回返，又可能漏掉首次“closed”后再见“open”的旧位置，**不等于无信息动作数**。关键重复与有效回返以上述逐步核查为准。

没有观察到A因强约束造成完成任务退化，但可比较范围只有两个成功任务，P7/P10被截断，不能据此排除风险。没有B可观察行为；没有照明、多实例任务，不能验证那些能力。本轮没有足够证据判断Actor全局访问历史依赖如何影响长期搜索，也没有命中导航缺失但direct action可用的对照情景。

## 技术中断、预算与费用

按原调度顺序，B/P3在首次请求遇到模型级 `mix TPM rate limit`；在途A/P10、A/P7、Parent/P7随后收到租户级相同类限流，错误类型均 `throttling_error`。完整原始错误保存在对应trajectory_responses/*.body；报告不复制租户标识或内部限流键。返回未说明何时恢复；这不是余额耗尽、策略失败或本轮600步预算超限的证据，也不能将共享服务的限流阈值当成本实验的实际Token用量。

调度器在首个技术错误后停止提交新Episode；已在途者正常结束或记录错误。因此没有启动剩余三条B，也没有通过等待后重试改变冻结的零重试规则。不能用“B晚运行且无结果”推出B方法更差。

| 消耗 | 实测 |
|---|---:|
| Editor逻辑/HTTP | 2 / 2 |
| Actor逻辑决策/HTTP | 76 / 76 |
| Actor已执行环境动作 | 72 |
| Actor启动/完成/中断/未启动Episode | 9 / 5 / 4 / 3 |
| 429响应 | 4 |
| 自动重试 | 0 |
| Actor已知 input / completion / total tokens | 104,465 / 27,207 / 131,672 |
| Editor已知 input / completion / total tokens | 5,860 / 14,992 / 20,852 |
| 合计已知 input / completion / total tokens | 110,325 / 42,199 / **152,524** |
| 其中 reasoning（已含completion） | 34,718 |

4个429没有usage，未知部分不补零；货币费用未返回。完整成功HTTP均返回deepseek-v4.1-flash。共78个HTTP，低于602上限。没有执行额外模型评价、Gate或Memory更新。流程因共性服务限流停止，剩余行为问题保持未解。
