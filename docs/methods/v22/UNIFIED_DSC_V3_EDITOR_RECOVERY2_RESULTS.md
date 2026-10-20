# V22 v3 Editor 第二次授权恢复结果

2026-10-16。用户授权“再次从 Editor 检查点恢复，如果 Editor 通过，则继续进行”。本次新增一次 Editor 调用，仍因完整 content 不符合 JSON 契约而停止。连同 13 的首次调用和 14 的恢复，Editor 已连续三次出现同类失败。未自动重试，未进入 Candidate Replay、Gate、Memory 或第二轮，未发布新 Skill/Memory。

## 协议与复用

独立档案为 `artifacts/methods/v22/15_unified_dsc_v3_editor_recovery_{control,live,analysis}_20261016`。复用八条有效 Parent、分类、已接受 Diagnosis、空 Memory 的程序恒等 Fusion；没有重跑上游。沿用 v3、冻结任务和模型参数，不修改五模块、Prompt、解析器、Schema 或评价规则。恢复控制器的五项离线测试通过。

实际 Editor 完整消息与原检查点相同。新档案的 authority.json、runtime_freeze.json、dispatch_ledger.json 和 completion.json 记录授权、版本、调用和停点；原始档案及 v3 源码核验未改变。

## 返回与失败

北京时间约 13:39:43 开始恢复，13:41:40 完成失败归档。HTTP 200，finish_reason=stop。原始 HTTP content 与归档文本一致，共 36,490 字符，以 `and <action>...</action> format each step` 开头，包含长段推理文字，后面出现 `</think>` 和 JSON。冻结解析器从首字符拒绝：`response: expected one valid JSON object`。没有 max_tokens 截断证据。

离线诊断发现偏移 31,858 之后的尾部对象可解析且满足现有 Editor 结构和映射验证；未采用该尾部，未生成有效 Editor 输出。这种结构检查不证明自然语言落实忠实。三次相似通道混入值得排查，但当前材料不足以确定模型、代理或供应端的责任；本次未作任何自动清洗或补救。

证据见 live/rounds/r1/calls/main_editor.json、对应 main_editor_responses 原始响应、raw_outputs/main_editor.txt，以及 analysis/failure_audit.json。原始 HTTP body SHA256：`30b7f17d8f675affc0a6a628189fcf208eed8cd0ec0a8485b33d685e8921a57d`。

## 成本与核验

| 项目 | 本次新增 |
| --- | ---: |
| Pro / HTTP | 1 / 1 |
| Actor / 环境 episode | 0 / 0 |
| 输入 Token | 37,704 |
| 输出 Token | 8,329 |
| 总 Token | 46,033 |
| 推理 Token（输出子集） | 698 |
| 缓存输入 Token（输入子集） | 36,864 |

复用记录不重复计费。自 11 开始及历次授权恢复累计已报告总 Token 484,119（输入 343,144，输出 140,975），Actor 152 次、Pro 7 次、HTTP 159 次；3 次早期中断调用用量仍未知。代理费率不可得，货币费用保留未知。完整计算及来源哈希见 analysis/accounting.json。

终态检查 artifact_valid=true、campaign_complete=false、published_rounds=0。历史文件和版本核验通过，八条 Parent 及旁路响应逐字节复用，未生成 Candidate/Gate/学习产物。analysis/final_freeze.json 固定本次终态文件摘要。

## 当前结论

本次授权恢复已执行，Editor 未通过，因此未继续后续阶段。有效 Parent、分类、Diagnosis、有效 Plan 与冻结 Editor 输入仍可复用；本次没有新增行为证据，不能评价预条件化收益。建议先定位重复的推理/正文通道问题，再决定后续恢复。本次不追加调用，不改变算法或协议。
