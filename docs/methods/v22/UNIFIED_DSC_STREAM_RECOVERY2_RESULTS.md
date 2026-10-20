# V22统一D/S/C流式实验：一次额外Diagnosis重试结果

2026-10-16（北京时间）。**已执行用户授权的一次额外Diagnosis重试，仍因组来源契约失败而停止。没有再次重试，也没有进入Fusion、Editor、Candidate Replay、Gate或Memory Learning。** 两轮实验未完成。

## 1. 授权与同输入核验

用户授权：“额外重试 Diagnosis 一次，如果成功就继续运行”。本次真实新增模型请求只有 **1次Pro**，新增环境episode **0个**；8条完整Parent和成功分类均复用。

恢复入口放在独立目录，沿用原runner字节码，仅在独立函数命名空间中继承原state0／campaign身份，使round ID及其引用不随新归档目录变化。未修改原模块全局、源码、Prompt、Schema、验证器、Gate或任务。分类原始call／body和Parent轨迹直接复制且字节一致，不伪造新执行。

5项离线检查通过，包括原编排的归档重建、逐字输入一致性、只能调用一次、改写消息拒绝、复用槽不能重跑及预算上限。首次测试桩缺少模拟call记录，补全测试桩后通过，失败日志保留；没有为离线测试调用实验模型或启动环境。

实际请求核验：

- 与前次Diagnosis **messages文件字节一致、请求参数一致、完整请求体哈希一致**。
- 请求体SHA-256：`b808e8c86644429f07c5a88dca276c78c104787d4dc0ed8c3e22ea18c206932d`。
- 未向消息追加错误信息、纠正建议或其他提示。
- 参数仍为deepseek-v4-pro、max_tokens=32,768、temperature=1、thinking enabled、reasoning_effort=medium、stream=false，读取超时600秒，单次POST。
- 新runtime冻结身份：`f683c222035bbab1b5d2b6b1ef528455f400dd690e8805a720e47c38fefea543`。

授权与独立恢复方法见 [恢复协议][protocol]、[authority.json][authority]。实际核验见 [audit.json][audit]。

## 2. 返回与拒绝原因

请求在北京时间 **11:05:55** 发出，**11:08:48** 返回，约173.00秒。HTTP200、finish_reason=stop；JSON可解析、compact结构和来源存在性校验通过，没有输出截断。随后原验证器报错：

`Requirement needs current decision group and matching Parent event evidence.`

[本次原始Diagnosis][diagnosis]仍返回revise，提出搜索取物、变换后投放、打开关闭目的容器、动作输出格式四项要求。但与前次只漏两组不同，**本次4项requirements的basis全部只有Parent事件，没有任何group来源引用**：

| 要求 | 显式组引用 | 所引事件的实际组 | 现有契约 |
|---|---|---|---|
| u1 搜索／取物 | 无 | G1 | 不通过 |
| u2 先变换再投放 | 无 | G1、G2、G3 | 不通过 |
| u3 打开关闭目的容器 | 无 | G2 | 不通过 |
| u4 动作输出格式 | 无 | G1 | 不通过 |

原程序在 [grouped_representation.py:210][validator] 要求非空显式组集合，并与引用Parent事件所属组集合一致；因此在u1即停止。独立只读核验发现其余3项也存在同类遗漏。没有补齐group ID、删除事件或放宽检查，原模型输出完整保留。

相同冻结输入的两次Diagnosis均未满足组来源契约。这是当前输入上的重复遵循失败；不是HTTP问题、网络超时、截断、历史Effect不适用或D/S/C方向被环境证伪。两次不足以估计总体失败率，也不能证明整个预条件化算法无效。

原始要求仍包含策略与条件，Watch也保留了操作顺序的未知；但由于没有形成有效Plan，不能把这些文本当作已成功运行的统一Update，更不能分析尚未发生的Editor落实或历史响应学习。

## 3. 成本、归档和剩余研究边界

| 本次新增消耗 | 数值 |
|---|---:|
| Pro逻辑请求／HTTP尝试 | 1／1 |
| 环境episode／Actor请求 | 0／0 |
| 输入Token | 35,968 |
| 输出Token | 9,687 |
| 总Token | 45,655 |
| reasoning Token | 9,085，属于输出子集 |
| provider报告cached input | 34,816，属于输入子集 |

缓存Token不再次加入总量，也不据未知代理费率换算价格。此前失败响应和中断消耗都保留；复用分类、8条Parent不重复计费。

累计去重账本：真实episode启动11次（含原3次中断），Actor请求152次、Pro3次、HTTP尝试155次；已确认HTTP200为152次，首次中断的3次在途请求仍无usage确认。已知输入193,983、输出117,910、合计311,893 Token；reasoning84,181为输出子集。货币费用仍未知，未知请求不视为零费用。

旧档案、前两份报告和本次原始响应均保留。原campaign verifier结果为 `artifact_valid=true, status=error, campaign_complete=false, published_rounds=0`；这是错误终止记录一致性通过，不是Diagnosis通过。

第一轮Parent仍为8/8成功，已完成分类继续有效。没有Candidate，所以没有修复／退化配对、Gate结果或Memory更新；第二轮未启动，历史响应对D/S/C的作用仍未获得新实验验证。

## 4. 本次结束状态

本次授权的“一次额外重试”已经用完且未成功，因此按用户条件停止，没有继续后续流程，也没有启动第三次Diagnosis采样。8条Parent、分类和两次失败Diagnosis均可供后续只读分析。

如果之后继续推进，当前需要单独决策的是模型可见组来源要求与严格路由契约如何协调；不能在本次冻结实验里静默补字段或放宽验证。本报告不实施任何优化，也不以重复采样代替机制判断。

[protocol]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery2_control_20261016/RECOVERY_PROTOCOL.md
[authority]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery2_control_20261016/authority.json
[audit]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery2_analysis_20261016/audit.json
[diagnosis]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery2_live_20261016/rounds/r1/raw_outputs/diagnosis.json
[validator]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_representation.py:210
