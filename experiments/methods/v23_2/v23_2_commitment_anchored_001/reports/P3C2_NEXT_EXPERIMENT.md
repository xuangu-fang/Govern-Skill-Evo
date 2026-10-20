# P3-C2 后续受控模型实验准备（未执行）

## 1. 要检验的干预

旧自由替换Preconditioner vs 本实验锚定构造。两个条件均使用真实R05 Memory，不用旧无Memory A与新有Memory候选混比。旧B_format只能历史参照；需新同条件重复才能初步考察稳定性。

唯一主动干预为构造方式及其必要输出契约/指令。它包括锚定生成要求和确定性应用，不是只改某一字符串。若观察改善，也不能单独归因于字节复制而忽略模型指令变化。下一步仍需另行授权，当前没有发送请求。

## 2. 固定材料与配置

- Original：P1-B R05授权retry合法plan，canonical SHA-256 `d960969ccebd23ad013fea0130e6f1bfa85b2759deaad4dcc8ae78675d68ce62`；来源与文件哈希见[来源清单](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/config/source_manifest.json)。
- Parent、Grouping、六条当前runs P1/P3/P6/P7/P8/P10与候选不变；B真实Active M1/M2/M3/M6/M7/M8/M9及完整sources，无M10，不补P2/P4。
- 用户payload与保存B完全相同。未来仅system中替换构造/内部契约并填写确定性plan hash；执行背景保持。不给模型22项人工标签、矩阵、夹具或研究者理想策略。
- 固定当前已保存参数：{"model": "deepseek-v4.1-flash", "max_tokens": 16384, "temperature": 1.0, "reasoning_effort": "medium", "thinking": {"type": "enabled"}, "stream": false}，timeout沿用300秒；模型/端点及返回实际模型必须在调用前核验，不能假定服务端永久不变。
- 保持原compiler及Editor接口。选定新草案和代码hash后冻结，再调用；不得根据输出补锚、改Prompt、修JSON或调整语义重采样。

草案：[完整Prompt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/config/anchored_prompt_draft.md)；[与原B差异](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/config/prompt_vs_B_format.diff)。它保留原Parent适当性、历史比较和Actor条件，仅改变构造操作与实验内部输出要求。所有inputs/prompt必须在未来发送前装配并复核容量，不把旧B的成功调用当作新草案容量保证。

## 3. 建议预算与失败规则

建议预注册3次旧/3次新，共6次逻辑调用、每次最多1次HTTP、0自动重试；交错旧新顺序并保留全部结果。此预算只是待授权方案，不是本次调用许可。若只授权一次配对，只能作为可用性/现象探索，不能称稳定优越。

API失败/截断/非法JSON/锚点不唯一/冲突/编译失败均保留原响应和成本，停止该次，不自动回退整段生成。公共路由或容量阻碍则暂停实验，不压缩Memory或改单侧证据。若未来要技术重试，需预先统一或另行授权，不因语义不理想重采样。

模型必须直接生成锚定方案；禁止先生成完整Update再第二次解释。实现尚无live runner，因此调用前需要最小一次调用归档适配、内部格式解析及原响应保留；不能直接用正式run_preconditioner期待内部edits兼容正式JSON。

## 4. 预注册评价

先分别评价各输出，再比较同Original的最终行为要求。区分结构有效率、未选片段保持与语义更新质量。

1. 历史响应是否真正作用于对应原承诺？同时识别当前证据本就支持的修正。
2. 目标修改有无问题依据/合理可检验预期？合理Keep也合法。
3. 配套修改是否说明不改就不可执行/矛盾/损害必要行为？标签本身不算依据。
4. 是否顺带改变完成单位、回访资格、任务阶段/强度？新增要求是否有独立动机，而非借用整体理由？
5. 精确目标/处理交付/可知有效回访是否保留；旧不合理要求是否仍遗留？原文保持不是旧策略正确证明。
6. 是否仍允许明确、大幅、非保守的探索？不能以更少字符、更短输出或更少Adjustment判优。
7. 记录全文锚点等可能绕过细粒度保护的选择；结构合法但语义无据仍判为语义问题。人工风险夹具不作为训练答案。

“新构造减少无据附带承诺且有据目标变换未被抑制”才是目标信号；仅未编辑文本被保留是工程保证，不足以证明历史预条件化有效。需要观察结构失败率/输出Token成本，不把锚点失败全部记为语义失败。

## 5. 范围与运行阻碍

- 只支持同ID替换/撤回和多Update编辑；拆合/新ID未实现。未来案例如需这些操作须在调用前明确实验范围，不能输出后拿限制当方法成功。
- 当前无API调用适配、无本轮真实上下文容量验证、无冻结发送请求；需要完成这些并获得授权才能运行。
- 原代码无法检查语义、依赖必要性或组合冲突。未来人工承诺评价和真实行为验证仍必要；不得增加第二审核Agent替代本次设计。
- R05已用于机制设计。模型验证之后需预先选择未参与设计的Train案例评估泛化；不能把旧R04/R06自动称为未接触样本，更不能用最终Test调参。
- Memory增量要在新机制下另做同Prompt有无Memory对照；构造方式对照不能直接回答Memory独立收益。
- 文本通过之后，Editor/Replay须另行授权。单次行为仍不隔离具体规则因果收益。

本阶段只完成准备，不启动上述实验。
