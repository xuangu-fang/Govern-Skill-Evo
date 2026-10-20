# V22 08：共同决策结构下的真实持续更新

日期：2026-10-15。**第一轮完成并 ACCEPT（7/10→8/10），第二轮真实继承后 Parent 为7/10，但全局分类输出截断，按协议停止。没有完成两轮更新，也尚未检验历史响应对第二轮 D/S/C 的作用。**

[实验索引](../README.md) · [结构化结果与轨迹来源](../results/summary.json) · [档案核验](../results/verification.json) · [并行调度说明](../../../../../docs/methods/v22/PARALLEL_SCHEDULING.md)

## 研究问题和边界

本实验检验两件事：一份统一 Skill 更新能否改善当前批次的真实失败；由实际编辑及反馈形成的有条件行为响应，能否参与下一轮更新决定并得到执行检验。分类组织共同决策结构，Diagnosis 独立提出初稿，Fusion 调整 D/S/C，Editor 在当前 Parent 上修订，Replay → Gate → Memory 后共同发布 Skill 与 Memory。

从 No Skill／空 Memory 开始，不导入旧 01—07 的 Skill 或 Effect。每轮十个 Train，轮间二十个任务互不重复；旧任务反馈只作为预先选题来源，不能称这二十项从未见过。每轮一份统一 Candidate，没有 Direct 分支，没有新增 Selection／Test，没有额外回归批次或按结果换题／返工。

Gate 使用完整同批原生成功数：Candidate 严格高于 Parent 即 ACCEPT，否则 RETAIN；局部退化不单独否决晋级。只有 Gate 后 Memory 有效完成，才共同发布下一轮状态。技术失败不冒充 RETAIN。

## 冻结与调度修订

原计划为 `v22.grouped_continual.v2`，执行代码初始串行。用户在本次执行中明确要求当前剩余及今后任务并行，最终上限为八。第一轮十条 Parent 和前四条 Candidate 保留此前真实串行执行；其余六条 Candidate 同批并行，第二轮 Parent／Candidate 最多八并行。没有重新运行已完成任务或已完成的语义调用。

独立 amendment 冻结了调度授权、原 runtime 哈希、剩余 Replay 调度源码和 continuation 源码；原配置、任务、提示、模型、Skill、Gate、Memory 和单任务／总预算不改写。第四条 Candidate 的环境轨迹已完整达到步数上限，协调器在安全交接时被中断；进程记录保留 interrupted，完整原生轨迹经核对后采用，未伪造为失败后重跑。最终档案应作为“v2 方法协议＋明确调度修订”解释，不能称未经修改的原调度。

后续默认 `v3` 只固化八并行调度；该代码在本次真实运行结束后才合入，不是当前冻结实验源码，也不意味着自动重复这批任务。

## 第一轮：7/10 → 8/10，ACCEPT

| Train | Parent 步数／结果 | Candidate 步数／结果 |
|---|---|---|
| 0001 | 5／成功 | 5／成功 |
| 0006 | 10／成功 | 6／成功 |
| 0007 | 7／成功 | 4／成功 |
| 0013 | 50／失败 | 50／失败 |
| 0021 | 50／失败 | 50／失败 |
| 0022 | 6／成功 | 8／成功 |
| 0027 | 14／成功 | 7／成功 |
| 0028 | 20／成功 | 9／成功 |
| 0034 | 50／失败 | 27／成功 |
| 0035 | 28／成功 | 9／成功 |

五个共同决策组区分：状态操作后放置；目标未见的搜索；单物体转移；持第一件时无法拿第二件；持物使用照明工具。分类将成功的双蜡烛与失败的双 CD 放在同一问题组，将同属冷却任务但卡在搜索与已经可操作状态的任务分开。它符合按当前决策问题组织的方向，但本实验不证明分类本身造成收益。

Diagnosis 提出五项要求，涉及单件转移、冷却／加热、两件串行交付、短窗口防搜索循环和持物使用工具。第一轮 Fusion 为预声明的程序恒等，不是一次模型 Keep。Editor 形成统一五段 Skill，实际 SHA256 为 `6ead6e278eddfb70cb00d71ecb6987dc5d59396cfb0bd8e39cfab7797a1862fa`。

### 改善、未解决问题与保留能力

- 0034 修复：Parent 已在第10步看到多张 CD，却在持第一张时尝试非法第二次拿取，后来把 CD 放回来源；Candidate 第21步拿第一张，23步放 drawer，25步拿第二张，27步交付成功。这是整份五条 Skill 的联合观察，不能孤立归因 u3。
- 0035 保持成功并减少往返：Parent 曾撤回已经交付的蜡烛，Candidate 依次在第5／9步交付两件。成功从28步变9步；本阶段未以效率优化为独立目标。
- 0013 仍未发现 DishSponge；Candidate 反复访问 sink／countertop，全部动作合法但搜索覆盖不足，不能概括为清洁操作失败。
- 0021 仍失败但出现局部进度：Parent 从未发现 Bread；Candidate 第46步发现、47步拿取、49步冷却、50步返回目的地，缺最后交付。不能只按二元失败说完全没有改善，也不能把未完成说成修复。
- 0027／0028 直接执行可用 heat 后交付，成功分别14→7步、20→9步；0022 冷却仍成功但6→8步，不能只报告步数减少。
- 七项原成功均保持；Parent 有六次非法动作，Candidate 为零。Parent 0034 的三次非法动作中两次与输出中的示例 action 标签被解析有关，不应全部归为交付策略问题。

### Gate 后的三条正式 Memory

1. 直接 heat/cool 当前可用且目标已持有时，观察到执行状态变化后交付；保留冷却步数增加、晚发现仍未完成、Parent 本来也成功及联合归因限制。
2. 两件位于同一可见来源，第一件交付后回来源取第二件，观察到串行完成；历史证据限于 drawer 目的地，不把别处第二件／非 drawer 条件说成已经验证。
3. 只依赖最近两步的防循环规则仍未解决两项搜索失败；记录晚发现后预算不足，不将失败强称为修改造成的退化，也不把该策略当成已验证解决方案。

正式 Memory 保留条件、证据和限制，整体 ACCEPT 不把所有条款标为正确。第二轮真实继承上述 Skill 和三条 Effect。学习输出中“absence of search improvement”措辞偏强，因为 Bread 有部分进度；报告保留这一偏差，未人工改写模型产物或后续输入。更一般的“stop”要求也尚无合法环境 stop 动作支持，不能仅凭文本义务声称已经可执行。


## 第二轮：继承成立，分类截断导致中止

| Train | 已继承 Parent 的结果 | 主要观察 |
|---|---|---|
| 0002 | 50步失败 | 已持 CD，但未观察到灯，未执行 use；反复查看／放下再拿起；一次非法 stop |
| 0008 | 4步成功 | 当前单物体放置完成 |
| 0009 | 5步成功 | 当前单物体放置完成 |
| 0014 | 15步成功 | 找到 DishSponge，清洁后交付 |
| 0023 | 8步成功 | 当前冷却后放置完成 |
| 0024 | 50步失败 | 请求 Pan，实际多次冷却／交付 Pot；未发现 Pan，一次非法 stop |
| 0029 | 36步成功 | 第30步发现 Mug，33步直接 heat，36步交付 |
| 0036 | 50步失败 | 第23步正确交付第一件 Keychain，第二件始终未观察到 |
| 0037 | 8步成功 | 同来源两件串行交付 sofa |
| 0038 | 9步成功 | 同来源两件串行交付 sidetable |

十项实际注入的 Skill 哈希均等于 R1 已发布 Candidate；R2 context 读取 R1 的三条 Memory，未从 No Skill 重建。0037／0038 的非 drawer 成功是当前执行的新观察，不能改写成 R1 历史已覆盖；0036 的第二件未见与 R1 同来源两件已可见不同。

0002 暴露了可研究的条件空缺：旧搜索要求只覆盖目标未见且未持有，工具规则则要求前往工具可见位置；持 CD 但灯未见时缺少明确下一步。这是轨迹与文本之间的解释假设，未进入本轮模型输入。0024 的主要问题是错对象与完成判断，不能将成功的 cool 动作本身标为无效。两项非法 stop 说明自然语言停止要求没有自动成为环境可执行动作；它们的单条因果归属尚未验证。

第二轮分类实际 messages 为131,044 Unicode字符，低于400,000输入上限。请求持续260.743秒，HTTP200、一次传输、没有重试。服务返回 `finish_reason=length`，completion_tokens=16,384，其中 reasoning_tokens=16,161；剩余可见输出仅约223 tokens，JSON 截在首组的字符串内部。这是**总输出预算被推理消耗后发生的截断**，不是输入超限、网络超时或已验证的分类算法错误。

固定协议不允许语义／格式重试，因此保留原始响应并停止。没有有效第二轮分组，未调用 Diagnosis、Fusion、Editor 或 Memory，未生成 Candidate、Replay 或 Gate，不能记为 RETAIN。最后已发布状态仍为 R1。原始截断片段不应被当作合法分组来解释后续机制。

## 并行、费用与可复核来源

轨迹起止时间核对：R1 Parent 峰值1，R1 Candidate 峰值6（后六项同时执行），R2 Parent 峰值8。R2 Parent 批次约990.05秒；R1 Parent 约2560.60秒，但两批任务不同，不据此声称固定加速倍数。后续默认运行器对 Parent 与 Candidate Replay 均使用最多8并行；任务内部仍按观察→请求→动作顺序执行，所有语义阶段等待整批收齐。

| 实际消耗 | 数值 |
|---|---:|
| 新环境 episode | 30（R1 20，R2 Parent 10） |
| Actor 逻辑请求 | 650（R1 Parent240、Candidate175，R2 Parent235） |
| Pro 语义调用 | 5（R1四次，R2分类一次失败） |
| 总逻辑请求 | 655 |
| HTTP 尝试 | 659 |
| 有返回用量的 prompt / completion tokens | 851,898 / 458,715 |
| 已报告总 tokens | 1,310,613 |
| 用量未知的 HTTP 尝试 | 4 |

四次传输层额外尝试遵循原冻结的同内容重试策略；未知用量不计作零成本。语义重试、格式重试、Candidate返工及episode重试均零。最终无缺失调用记录或不可读轨迹。没有因提前停止补跑未使用预算。

模型为 Actor `deepseek-v4-flash`、语义 `deepseek-v4-pro`；记录参数 temperature=1、max_tokens=16384、thinking=enabled、reasoning_effort=medium、stream=false、环境seed42、单请求timeout300秒、每episode最多50步。上述是冻结请求参数，不表示远端随机输出可逐字复现。

Git HEAD 为 `7d4749541dab04397ea146e56dc762a26ba81a3b`，工作区含既有未提交实现，因此实际身份以45份源码复制快照、4项配置绑定、20个game文件及5个系统提示为准。任务manifest SHA256为 `51a3393a94992536e3de1fd12e4910060d57c8434b189782814d08fb4d405b05`。原 runtime 记录文件SHA256为 `207de46b1b860dce1a650246331350e591acf717b62c9ed0d9951aaaf8c3728a`。

原始资料位于：

- [campaign 报告](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/report.json)与[runtime冻结](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/runtime_freeze.json)。
- [R1实际 Skill](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r1/candidate/SKILL.md)、[Gate](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r1/gate.json)、[正式状态与Memory](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r1/state.json)。
- [R2继承context](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r2/context.json)与[截断调用记录](../../../../../artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r2/calls/classification.json)。
- [独立调度修订](../../../../../artifacts/methods/v22/08_parallel_amendment_20261015/amendment.json)与[续行源码冻结](../../../../../artifacts/methods/v22/08_parallel_amendment_20261015/continuation_freeze.json)。

离线档案核验通过，明确返回 `artifact_valid=true`、`campaign_complete=false`、`published_rounds=1`、`incomplete_rounds=1` 和 `scheduling.amended=true`。核验确认来源与确定性衔接，不能认证模型的行为解释或因果结论。未来8并行补丁在隔离副本通过319项离线测试，实际合入七个文件后哈希一致，主工作区14项调度／修订／归档测试通过。合入前快照所覆盖90个既有源码／实验文件均未变化；合入只修改三份运行器相关源码，旧01—07产物及原08配置保持不变。

## 能回答与仍未回答的问题

本次出现了一份统一 Skill 修复双 CD 失败、保持本批七项成功的真实配对观察，并完成真实 Gate 采用、带限制的 Memory 学习和下一轮实际继承。它支持“Skill 更新能够改善原失败”的一个实例，不能从一次配对推出稳定收益。

历史 Memory 尚未进入第二轮 Fusion。因而本次**没有回答**“作用认识是否改变下一轮 D/S/C，以及行为是否支持调整”，更不能据此次中止断言预条件化有效或无效。没有完整第二轮、Direct、跨轮旧任务回归或 Selection／Test；不报告这些方面的优势、遗忘率或泛化结论。

下一步首先处理分类输出预算这一执行瓶颈，并明确单独的恢复／新协议；无需先增加 Diagnosis、Memory 或 Fusion 的结构。应保留已完成的30条轨迹、R1正式状态和本次失败成本，再决定是否复用 R2已冻结Parent材料恢复。分类保持一次全批调用，优先核对推理预算与可见输出预算如何匹配；不能在本档案中偷偷提高上限、补调或把失败替换掉。之后才能继续验证历史响应→实际更新→对应Replay这条尚未完成的机制。
