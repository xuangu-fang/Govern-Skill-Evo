# Evidence Review 输入与输出预算修正

> 当前新运行已切换为 [单次 Evidence Review v19.3](V19_ONE_PASS_EVIDENCE_REVIEW.md)，下文补充上下文协议保留作为历史说明。

来源：`experiments/archive/v19/v19_v4_local_review_once_002`。本次仅离线分析和工程验证，不发模型请求，不修改该目录。

## 真实失败原因

Fusion 完成 9 个议题，8 个 PROPOSE。1 个审阅完成，6 个在本地 32,000 proxy input token 检查时停止，另 1 个收到 `finish_reason=length`。该响应 completion_tokens=8,192，其中 reasoning_tokens=7,391，正文仅余约 801 token，JSON 未结束。这是输出截断，不是网络错误、拒答或已完成 JSON 的契约错误；保存的响应不应交给契约修复。

旧输入并不是完整轨迹的直接复制，但仍过度展开：全部关联轨迹的事件目录、种子事件 ±1 邻域及工具配对、完整可见政策逐行目录（每行重复上下文/摘要）、长引用 ID 在多处重复。最大议题含 119 个可读事件（种子 55）、232 行政策。canonical 字段单独估算：政策约 27,277、事件约 22,861、事件目录约 17,505 token；这些值不等于经过 wire interning 后的可加总贡献。

## 通用修正

- 新输入版本 `evidence_review_input_v19.2`。全部直接种子事件、已知反证与可识别的工具调用/结果配对保留原文；不默认加入不相关的相邻事件。
- 政策首轮只加载 Findings 明确引用的行；未加载行仍在完整目录中，可通过 `MORE_CONTEXT.policy_refs` 补充。缺失摘录不表示政策不存在。仍然最多一次上下文补充，补充和 repair 均受 32,000 预算限制。
- 目录用共享前缀、列和常量进行无损表示；只索引尚未加载的对象。已加载对象本身仍可引用。
- Wire 层长 ID 使用显式 `reference_prefixes` 字典。正文未被摘要或裁剪；扩展后必须与 canonical payload 一致。模型引用可以用完整 ID 或声明的紧凑 ID，程序仅做确定性 ID 解码，保存原始响应，并对解码后的引用重新执行全部契约校验。这不是修补引用或补充证据。
- Evidence Review 输出上限调整为 24,000，包含 reasoning。`ModelOutputTruncated` 单独记录 `length` 与 token 用量，不消耗唯一一次契约修复，不自动重发。
- 新尝试可显式导入旧 Fusion 与已完整通过的提案；校验旧产物哈希、输入、原响应及来源，审计逐项记录输入版本。失败提案在 v19.2 下重新请求。旧产物不覆盖，不把旧结果标为新输入生成。

## 实际输入离线重建

| 议题 ID 前缀 | 旧输入 token | 新输入 token |
|---|---:|---:|
| 59ff08f1 | 33,726 | 12,557 |
| 86789b0f | 34,472 | 14,296 |
| f2fb3bbd | 38,904 | 13,888 |
| b39548d2 | 39,515 | 15,275 |
| 16bc8826 | 62,492 | 24,223 |
| cbef8dc9 | 89,104 | 29,742 |
| 68e5dbbb（输出截断） | 26,574 | 8,519 |
| 0937ed45（已完成，保留原结果） | 29,745 | 10,235 |

这些是 cl100k_base 本地估算，不是网关实测。新输入保留所有直接证据与反证，但少看默认周边上下文；不能由 token 降低推断判断质量提升。新增上下文或 repair 仍可能超过预算，届时明确停止，不截断证据或提升上限。

明细：`artifacts/v19_review_budget_fix_002.json`，包括来源文件哈希、字段分解和 API usage。`fix_001` 是目录常量合并前的中间分析，保留供审计。

## 下一次运行命令（未启动）

```bash
python scripts/run_v19_local_review.py run \
  --upstream experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local experiments/archive/v19/v19_v4_local_review_once_002 \
  --output experiments/archive/v19/v19_v4_local_review_once_003
```

该入口复用 9 个 Fusion 议题与 1 个完成的审阅，仅处理余下 7 个；完整核验和编译后停在 Editor 前。恢复同一新尝试时改 `run` 为 `resume`，保留其他参数。遇到无完整响应仍不自动重发；截断响应是完整的失败尝试，不能冒充网络无响应归档重试。

### 本次选择：只复用 Fusion，统一重跑 Evidence Review

在上述命令中增加 `--fusion-only`，则旧审阅结果仅留档，不参与本次编译。8 个 PROPOSE 均按 v19.2 重新核验，包括此前已完成的 1 个。复用策略写入输入绑定与 receipt，resume 必须保持相同选项；不能中途切换为复用旧审阅。

```bash
python scripts/run_v19_local_review.py run \
  --upstream experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local experiments/archive/v19/v19_v4_local_review_once_002 --fusion-only \
  --output experiments/archive/v19/v19_v4_local_review_once_003
```
