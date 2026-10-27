# R03 首轮执行记录（已停止）

用户在 Preconditioner Memory v3 三次失败后要求将 max_tokens 翻倍并重新实验。该组保留为 32,768 上限下的实际记录，后续结果见 ../knowledge_only_single_round_002。

| 模块 | 视图 | 已发请求 | 有效结果 | 已知输入 token | 已知输出 token | usage 缺失请求 |
|---|---|---:|---|---:|---:|---:|
| preconditioner | memory_v3 | 3 | 无 | 675,700 | 80,576 | 0 |
| preconditioner | knowledge_only | 2 | 无 | 89,652 | 15,935 | 1 |
| replay | memory_v3 | 0 | 无 | 0 | 0 | 0 |
| replay | knowledge_only | 0 | 无 | 0 | 0 | 0 |

Memory v3 Preconditioner 三次错误依次为：JSON 正文混入额外文字；引用未按单反引号标注；finish_reason=length（32,768 completion tokens 全部为 reasoning）。
Knowledge Only Preconditioner 首次因 reason 内包含非正式 ID 的反引号内容等引用格式问题失败；第二次等待响应时按用户要求停止，本地未取得响应与 usage。该次成本未知；已知成本不是完整成本。
两组 Replay 均未启动。该组没有有效输出可供完整语义对照，不将输出失败解释为知识内容质量或任务成功率结论。
所有失败与中止请求保留；新组从头运行四个单元，成本分开统计。

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](../README.md)。
