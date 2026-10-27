# P6：多 Knowledge 真实 Replay 验证

日期：2026-10-22。**R05/R06 均取得结构合法提案，共 3 次 HTTP、1 次技术重试。R06 保留了此前遗漏的两个关键比较；R05 仍有事实与范围错误，R06 搜索条目仍有过强解释。未自动发布任何 Memory。**

## 实验条件与调用

直接发送 [P4 冻结输入](../multi_knowledge_p4_001/freeze.json) 中的 R05/R06 消息：实际 Skill Diff、Effective Plan、完整当前 Pair、原历史 Memory、v3 压缩及历史 Pair 均未变化。使用显式 `entries_sources_multi_knowledge_v1` 和候选 `v23_4_replay_multi_knowledge_v1`。Actor 背景和视图说明继续按既有方式拼接。

沿用 deepseek-v4.1-flash、temperature=1、thinking enabled/medium、max_tokens=32768、60/300 秒连接/读取超时和既有单请求 transport。每个案例最多首次加三次技术重试；首次合法即停止，没有语义重采样。本次没有扩大 max_tokens、修改输入或人工修补输出。

| 项目 | R05 | R06 |
|---|---:|---:|
| HTTP 次数 / 技术重试 | 2 / 1 | 1 / 0 |
| 合法结果所在 attempt | 002 | 001 |
| 每次输入 tokens | 287,068 | 277,492 |
| 合法调用输出 tokens（含推理） | 23,502 | 20,723 |
| 合法调用总 tokens | 310,570 | 298,215 |
| 合法调用耗时（秒） | 185.596 | 113.413 |
| Memory 提案 / Knowledge | 新增 1 / 4 | 修订 2 / 5 |

R05 首次 HTTP 200、finish_reason=stop，但正文不是一个合法 JSON 对象，校验报 `response: expected one valid JSON object`。原始响应、错误和调用记录完整保留；第二次使用完全相同输入及参数成功。首次失败额外消耗 315,531 tokens、113.410 秒。

三次调用合计 **851,628 输入、72,688 输出、924,316 总 tokens**。两次合法调用输入相对上一版单 Knowledge 候选分别增加 962 / 925 tokens。这里测量的是完整候选 Prompt 与表示调整后的请求，不将变化归因于单一字段，也不从单次耗时推断稳定速度。

## 语义结果

| 审查重点 | 本轮观察 |
|---|---|
| 历史 heat plate 13 成功对 50 失败 | R06 M13/K2 明确保留双方机会、动作和结果，不再压缩成泛化的“未触发” |
| cool tomato 局部温变与整体效率 | R06 M13/K1 明确双方直接冷却动作相同，18→10 来自搜索差异，不再将八步作为新增温变收益 |
| apple 改善与退化 | R05 保留当前 14→11 数字，但未在搜索 Knowledge 中解释具体响应；R06 保留历史 38→46 的效率退化 |
| 范围外能力比较 | R05 仍把 desklamp pillow 多一步混入非 desklamp 搜索响应；成功 butterknife 的独立比较未进入新增知识 |
| 事实准确性 | R05 虚构 Q7:25 的非法 drawer 8 动作，实际为合法 drawer 2；仍否认已有 Parent 直接开柜行为 |
| 事实与解释边界 | R05 soapbar、R06 历史 butterknife 仍有“未找到→不存在”的过强判断 |
| 完整数组修订 | R06 实际替换 M10/M7，主要历史正负比较得到保留；R05 只新增条目，不能验证跨轮替换与旧认识校准 |
| 可采用性 | R05 M10、R06 M12 暂不采用；R06 M13 本次定向审查未发现阻断项，仍不自动发布 |

逐条原文、反证、历史保留边界和判断见 [SEMANTIC_REVIEW.md](SEMANTIC_REVIEW.md)。本轮不是完整消融，不能区分 Prompt、表示和随机采样各自的贡献，也不能由两个案例推断自动学习可靠性。

## Memory 粒度与增长

| 指标 | R05 | R06 |
|---|---:|---:|
| 活跃 MemoryEntry | 7→8 | 7→7 |
| 活跃 Knowledge | 7→11 | 7→10 |
| 活跃认识文本字符 | 15,928→19,430 | 14,576→16,688 |
| 新提案最长 Knowledge 字符 | 941 | 1,947 |

R05 四条较短，但没有整合历史；R06 五条中，温变正面与保持比较仍集中在一条较长 Knowledge。长度下降不等于语义更可靠。v3 视图也随新增当前轨迹及引用窗口增长，不能把全部增长归因于多 Knowledge 开销；精确同字段测量见 [GROWTH.json](GROWTH.json)。目前不能判定长期 Memory 是否会不必要地膨胀。

## 技术验收与兼容边界

- 候选 Prompt 的 25 项相关测试通过；本轮不改生产实现，未重复无关全量回归。
- P4 的 62 个冻结文件校验和实际 Editor Diff/Plan 来源复核通过；实际请求消息、参数、超时及无 transport 隐式重试均核对通过。
- 每条 Knowledge 结构和引用、Memory 级 revises 通过；原样提案只提交到原 Memory 的隔离副本。
- 两轮均通过完整数组提交/重载、幂等性、旧 archive 字节不变、全部动作/反馈保留、详细状态与菜单一致、数字 Evidence 的详细窗口、后续 Preconditioner 新契约投影、未来 Replay Pair 来源恢复。
- 隔离上下文：`v23_4_R05_multi_knowledge_p6_001` / `v23_4_R06_multi_knowledge_p6_001`。新 Memory 编号只属于各自隔离目录。
- 11,575 个受保护文件未变，包括旧归档、原 Active Memory、前期实验和默认 Prompt；没有重新运行 Actor/Editor，也没有 Candidate 提升或正式 Memory 发布。

冻结 Editor 来源属于旧实验 attempt 档案，沿用 P4 专用来源核验；没有伪装成生产 `run.json` 谱系，也不宣称本次真实数据经过生产 Editor loader。真实提案的提交/消费通过当前新契约接口验证。

## 产物与离线复核

- [调用审计](AUDIT.json)、[结果汇总](RESULTS.json)、[冻结清单](config/freeze.json)、[事实断言](FACT_CHECKS.json)。
- 原样提案：[R05](runs/R05_replay/attempt_002/parsed.json)、[R06](runs/R06_replay/attempt_001/parsed.json)。R05 首次失败归档保留于 `runs/R05_replay/attempt_001/`，不人工修补。
- 隔离 Memory 审计：[R05](cases/R05/results/MEMORY_AUDIT.json)、[R06](cases/R06/results/MEMORY_AUDIT.json)。

以下命令只读已保存调用结果或重放隔离提交，不发起模型调用：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.multi_knowledge_p6_001.run audit
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.multi_knowledge_p6_001.check_memory R05
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.multi_knowledge_p6_001.check_memory R06
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.multi_knowledge_p6_001.review_facts
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.multi_knowledge_p6_001.summarize
```

本轮支持继续研究条件性 Knowledge 与历史比较保留；尚未证明多 Knowledge 足以解决事实校准，也未达到可自动采用整个 Replay 提案的程度。
