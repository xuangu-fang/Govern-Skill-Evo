# V22 unified D/S/C v2：真实流式执行停点与核验报告

日期：2026-10-16（北京时间）。状态：**已获启动授权并真实执行，但在 R1 Parent 阶段因运行进程消失而中断；两轮实验未完成，未自动恢复。**

本报告遵循冻结的 [准备方案][preparation]、[协议][protocol]及报告模板。不能把这次不完整运行写成两轮实验结果。独立核验档案见 [interruption_audit.json][audit]，原运行目录保持原样，包括尚未结算的 `running` 状态和旧成本摘要。

## 1. 执行身份与停止事实

用户明确批准执行冻结的 16 项新 Train、8+8、No Skill＋空 Memory、原模型参数、八并行及失败协议。北京时间 **01:06:14** 以冻结的 `continual_runner run --prepared` 入口启动，启动前只读 preflight 通过，runtime 内容身份为：

`b5ca8ef981c2bcc7326610c2ce2dd1b59988cf7603f32cb2eae6027946211b37`

执行期间没有修改算法、Prompt、任务、Schema、Gate 或 Candidate，也没有重新启动。R1 的 8 个 Parent 在约 0.36 秒内全部分发；记录显示任务内动作串行、并行不超过 8。

对话期间出现两次执行轮中断通知。随后原工具会话已失效，操作系统进程列表中也不存在 `continual_runner`／`run_task_skill` 执行进程；报告仍为 `running / parent_execution`，没有正常终止记录或退出码。因此可确认的是**进程已终止且未完成结算**；中断通知与进程消失时间相符，但不能据此确定具体终止信号、责任方或底层原因。没有证据将此次停止归因于远端 HTTP 错误、超时、无效 Pro JSON 或 D/S/C 算法失败。

最后三个在途请求分别开始于北京时间 01:08:48.921（0017）、01:08:41.750（0025）、01:08:32.996（0033）；这些是请求开始时间，**不是已确定的进程终止时间**。

停止后没有再次执行启动入口，没有新增模型或环境请求。原档案 177 个文件已逐个记录 SHA-256，核验前后文件哈希一致，见 [原档案清单][manifest]。

## 2. A：实际任务执行与可复用产物

| R1 Parent 任务 | 完整性／原生结果 | 已执行动作 | 已登记请求 | 可复用范围 |
|---|---|---:|---:|---|
| train:0019 | 完整，成功 | 7 | 7 | 完整 Parent 证据 |
| train:0004 | 完整，成功 | 4 | 4 | 完整 Parent 证据 |
| train:0020 | 完整，成功 | 9 | 9 | 完整 Parent 证据 |
| train:0017 | 不完整，原始状态仍为 running | 20 | 21 | 仅部分轨迹／消耗审计 |
| train:0025 | 不完整，原始状态仍为 running | 16 | 17 | 仅部分轨迹／消耗审计 |
| train:0033 | 不完整，原始状态仍为 running | 9 | 10 | 仅部分轨迹／消耗审计 |
| train:0016 | 完整，成功 | 7 | 7 | 完整 Parent 证据 |
| train:0010 | 完整，成功 | 9 | 9 | 完整 Parent 证据 |

5 条完整轨迹均通过保存身份、实际 No Skill 输入、消息重建、动作投影、原生结果、环境文件、依赖与源码身份核验。3 条部分轨迹也通过其已保存前缀的一致性检查，但不构成完整 episode。

**不能报告 Parent 为 5/8 成功率，也不能将未完成的 3 项记为失败。** 目前没有 Candidate，因此没有修复、退化、保留率、同任务差值或有效 Gate；R2 未开始。

可直接观察的局部事实：

- 0019、0016、0020 的成功轨迹包含取得目标、执行 `clean`、随后放入目标容器／位置；0010 完成取物和放置；0004 完成开灯及取得目标后的原生成功。
- 0017 已多次重访已观察位置，尚未取得目标；记录只支持“截至中断仍在搜索”，不能推断 50 步最终结果。
- 0025 已检查若干位置并取得一个非目标物；第 7 步动作不在当时 admissible list 中，环境返回 `Nothing happens.`。这是 No Skill Actor 的局部行为事实。
- 0033 已将目标放入设备并关闭，尚未观察到实际 `heat`；第 8 步被既有投影器提取为非有效命令的长文本，环境返回 `Nothing happens.`，随后重新打开设备。这是可观察的 Actor 输出／投影异常，不是更新模块行为，也不是已确认的停止原因。

上述未完成路径只用于停点与行为描述，不进入本轮正式 Effect，不据此调整冻结 Prompt 或补造任务结果。逐步证据路径及哈希均在 [核验档案][audit]。

## 3. B：统一 D/S/C 作用链尚未执行到哪里

| 环节 | 实际状态 | 当前可作的判断 |
|---|---|---|
| Parent Replay | 5 项完成、3 项中断 | 仅有初始 No Skill 行为证据 |
| 全局分类／Diagnosis | 0 次调用 | 无原始 Update，不能评价构造质量 |
| R1 Fusion 恒等 | 尚未进入 | 只存在冻结协议预期，尚无执行产物 |
| Editor／Candidate Replay | 未进入 | 无有效 Update、实际 Skill diff 或配对响应 |
| Gate／Replay-Memory Learning | 未进入 | 无 Gate、Findings、Effect 或认识修订 |
| R2 历史消费与 D/S/C 决定 | 未开始 | 无法分析历史与当前证据的贡献 |

最后状态仍为 `state0.json`：No Skill、空 Memory、round_index=0，状态身份 `b75a65fb6a1f13cd718ffb1491a77139f378f0648ab179b448146bd5248a22f3`。没有正式 Skill／Memory 发布。

因此，用户关心的“第一轮 Memory 如何影响第二轮 Fusion”“Editor 忠实落实”“Replay 的条件化学习”等研究问题均**尚未获得本次执行证据**。既不能判定机制成功，也不能将过程停止当作算法语义失败。

## 4. C：实际成本与稳定性

根据所有保存轨迹和 HTTP attempt 重新计数，避免使用中断前的旧总计：

| 指标 | 实际保存值 |
|---|---:|
| episode 分发／完整／不完整 | 8／5／3 |
| Actor 逻辑请求／HTTP attempt | 84／84 |
| Pro 语义调用／传输重试 | 0／0 |
| 已返回 HTTP 200／已归档原始 body | 81／81 |
| 已登记但未返回的请求 | 3 |
| 已知 prompt Token | 50,589 |
| 已知 completion Token | 33,177 |
| 已知 total Token | 83,766 |
| provider 报告的 reasoning Token | 18,632（completion 子集） |
| 货币费用 | 未知：没有冻结代理费率或实际账单 |

81 份原始响应均有匹配的轨迹引用、哈希、长度和 usage；未发现无引用的响应 body。3 个在途请求的远端处理与费用未知，**不能当作零费用，也不能当作确定未发送**。输入／输出总量只包含已返回用量，不是最终账单保证。缓存细项仅保留 provider 提供值，字段缺失不补零。

没有观察到 HTTP 非 200、自动重试或已归档异常响应；这不证明三个未确认请求的远端状态。已归档动作的有效性与 HTTP 成功也应区分，例如上述非命令投影仍来自 HTTP 200。

`verify_campaign` 原样核验未通过，具体为 `Recorded cost summary changed.`：主进程没有在终止前把后续子进程保存的轨迹用量写回总报告，原摘要仍为 68 次请求，而实际已保存 84 次。没有为了让核验通过而改写原报告。独立核验已确认冻结材料、round_start、8 条完整／部分轨迹和81份原始响应的一致性；**这不等于完整 campaign verifier 通过**。

## 5. 恢复所需授权与预算：仅提案，未执行

按冻结协议 §5，本次不完整 episode 不能从中间状态继续，也不能默认重新执行；旧 runner 没有通用 resume。要完成原定两轮，建议另立恢复目录与来源绑定，复用5条完整 Parent，仅重启3条不完整 Parent，然后继续原来尚未执行的阶段。原始3条部分轨迹独立保留计费／审计，不能与新执行拼成一条轨迹。

| 恢复工作 | 最多新 episode | Actor 逻辑请求上限 | Pro 调用上限 |
|---|---:|---:|---:|
| 重新执行 R1 未完成的 0017／0025／0033 | 3 | 150 | 0 |
| R1 其余流程，含 Candidate Replay | 8 | 400 | 4 |
| R2 冻结流程 | 16 | 800 | 5 |
| 恢复合计 | **27** | **1,350** | **9** |

这包括24个原方案尚未执行的 episode，以及**3个需要额外授权的重复启动**；累计分发最多35个，超出原32个 episode 上限。恢复新逻辑请求最多1,359，HTTP attempt最多8,109；加本次84个已登记请求，累计最多1,443个逻辑请求／8,193个HTTP attempt。即使请求数仍低于原总上限，也不构成自行恢复的授权。

恢复保持原模型参数、每episode50步、八并行、Pro零重试及所有算法／任务／Gate规则；合法无更新时实际调用可更少。不增加新任务、语义重采样或消融。3个未知在途请求的费用继续单列。

如获恢复授权，首先需要在独立目录完成来源绑定、可复用轨迹校验和最小恢复入口的离线验证；不能直接再次运行旧 `run --prepared` 命令。应采用不依赖当前工具会话持续存活的执行承载并保留进程／退出日志，作为工程可靠性措施，不能借此修改行为算法。当前没有实施恢复入口或发送恢复请求。

## 6. 当前结论

本次已验证冻结配置能够启动真实环境和Actor请求，并获得5条有效完整轨迹；同时暴露出执行承载中断后无法自动完成结算的运行问题。没有形成一轮完整更新，更没有形成两轮历史响应闭环。

需要用户决定是否授权上述独立恢复及3项不完整episode重新执行。在此之前停在本报告，不修改五模块、不扩大实验，也不将已观察到的局部行为作为Prompt优化清单。

[preparation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_STREAM_PREPARATION.md
[protocol]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/11_unified_dsc_stream/PROTOCOL.md
[audit]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_analysis_20261016/interruption_audit.json
[manifest]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_analysis_20261016/original_archive_manifest.json
