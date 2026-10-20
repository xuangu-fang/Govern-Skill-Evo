# V22 v3 Editor 检查点恢复结果

2026-10-16。依据用户“从 Editor 检查点恢复，如果 Editor 通过，则继续进行”的授权，执行一次额外 Editor 请求。**Editor 再次返回不符合 JSON 内容契约的响应，运行器按协议停止；未进入 Candidate Replay、Gate、Memory 或第二轮。** 本报告不将技术失败解释为合法 no_change / RETAIN，也不评价 Skill 效果。

## 执行边界与来源

本次独立档案前缀为 `artifacts/methods/v22/14_unified_dsc_v3_editor_recovery_{control,live,analysis}_20261016`。复用 13 档案中的八条完整 Parent、有效分类、已接受 Diagnosis 和空 Memory 的程序恒等 Fusion。没有重跑这些阶段；复制记录不计入新增费用。

算法仍为冻结的 `v22.unified_dsc.v3`。任务、模型、Prompt、Schema、Gate、有效 Plan 以及 Editor 完整消息未改变。Editor 消息与上次逐字节相同，两次实际请求 SHA256 均为 `bfc9ad0a1dbe4e591e20a0b00172f7d34f07ac40020bc0b18c24c0055e50bc68`。新运行冻结摘要为 `4a21d202d7effff3257516afd13db3c81732794a905b486e8718ae72c9547ed2`。

独立恢复控制器仅适配检查点复用和单次请求记账，启动前 5 项离线测试通过。请求仍为 Pro、temperature=1、thinking enabled / medium、max_tokens=32768、非流式、600 秒超时、single_attempt。具体协议、授权范围和预算见 control/RECOVERY_PROTOCOL.md、authority.json；没有修改五模块实现。

## 实际结果及证据

北京时间 13:29:41 发出请求，13:30:51 收到响应，13:30:52 完成失败归档。HTTP 200，finish_reason=stop；失败为 `response: expected one valid JSON object`。

原始 HTTP 的 message.content、调用记录 content 和 raw_outputs/main_editor.txt 完全一致。该内容共 14,881 字符，以普通推理文字开头，随后出现 `</think>`，最后才是 JSON 对象；冻结解析器在起始位置即拒绝。没有输出截断证据，也没有本地归档篡改证据。

仅为离线定位，检查了字符偏移 11,171 之后的 JSON：可解析且通过现有 Editor 结构与映射验证。这不证明自然语言落实忠实，也不使完整响应合法。**未将尾部提取为有效 Editor 输出，未写入或发布 Candidate。**

两次失败都存在类似通道边界：reasoning_content 在讨论 Actor 基础响应格式时结束，content 接着继续该句，并在后面包含 `</think>`。这提示需要排查字面 think 标签与推理/正文分离的相互作用；现有证据无法确定责任属于模型、供应端还是代理层。不能直接宣布代理缺陷，更不应通过反复采样掩盖问题。

主要证据：

- live/rounds/r1/calls/main_editor.json 及 main_editor_responses 中的原始 HTTP body；原始 body SHA256 为 `4f38b5aebc3e72f4e8581561c2da754cd317de7b88672d0c1f1cc455bcf53ae8`。
- analysis/failure_audit.json：解析失败、尾部离线检查、未产生后续阶段及 campaign 核验。
- analysis/channel_boundary_comparison.json：两次相同请求与通道边界的只读对比。
- control/completion.json：exit_code=1、artifact_valid=true、campaign_complete=false、published_rounds=0。

## 成本与完整性

| 范围 | 本次新增 |
| --- | ---: |
| Pro / HTTP 请求 | 1 / 1 |
| Actor / ALFWorld episode | 0 / 0 |
| 输入 Token | 37,704 |
| 输出 Token | 4,415 |
| 总 Token | 42,119 |
| 其中推理 Token | 1,351 |
| 其中缓存输入 Token | 36,864 |

推理和缓存分别为输出和输入的子集，不重复加总。代理实际费率不可得，因此货币费用保持未知，不以公开价格估算冒充实付。

自 11 原始实验及历次授权恢复以来，累计已记录 Actor 152 次、Pro 6 次、HTTP 158 次；其中 155 次已知 HTTP 200、3 次早期中断的尝试仍未知。累计已报告输入 305,440、输出 132,646、总计 438,086 Token；未知用量未当作零。累计 episode 启动 11 次，包括原始中断的 3 次，完整有效 Parent 仍为 8 条。详见 analysis/accounting.json，已排除复制记录的重复计费。

只读核验通过：原始档案、v3 修订源码和前次 13 冻结档案哈希不变；新运行 runtime 检查通过；八条 Parent 及其旁路响应文件与来源相同，分类和 Diagnosis 输入/消息/输出/调用记录相同。运行进程已退出。终态文件清单记录于 analysis/final_freeze.json。

## 当前停点与后续边界

有效检查点仍是八条 Parent、分类、Diagnosis、有效 Plan 及冻结 Editor 输入。未产生有效 Editor 输出或新正式 Skill/Memory；没有新的行为证据可以用于分析 D/S/C 收益。

本次授权的单次恢复已执行并失败，未追加重试。下一步宜先定位响应通道边界问题，再决定是否需要独立版本修订或再次恢复；本次未修改解析器、Prompt 或算法，也未自动采用尾部 JSON。任何新的付费调用或修订后续行需另行授权。
