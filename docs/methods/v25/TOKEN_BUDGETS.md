# V25 与 SkillAdam 的输出额度

2026-10-27 按用户确认更新当前源码的新配置默认值。未启动新实验，未调用真实模型，未改动既有实验配置、冻结清单、归档或 Replay 机制。

| 方法 | 模块 | 单次输出上限（tokens） |
|---|---|---:|
| V25 / SkillAdam | Actor | 49152 |
| V25 | Grouping | 16384 |
| V25 | Diagnosis | 32768 |
| V25 | Preconditioner | 49152 |
| V25 | Editor | 16384 |
| V25 | Replay | 49152 |
| V25 | Verifier | 49152 |
| V25 | Repair | 32768 |
| SkillAdam | 轨迹压缩、Patch 生成、Momentum 更新 | 16384 |

Gate 不调用模型。SkillAdam 的 96000 是优化器上下文字符阈值，与输出 token 额度不同；该阈值及其他原生方法参数不变。

## 配置实现

`src/skill_evolution/v25/baseline.py` 的 `configuration()` 为新配置显式设置 Actor 49152，并设置：

```json
{
  "module_max_tokens": {
    "diagnosis": 32768,
    "preconditioner": 49152,
    "replay": 49152,
    "verifier": 49152,
    "repair": 32768
  }
}
```

默认 `call_config.max_tokens` 保持 16384；Grouping 和 Editor 使用这个默认值。实际 Actor 请求由 `actor_profile.actor_max_output_tokens` 覆盖默认值，因此不会误用优化器的 16384。

SkillAdam 没有第二份独立的 Actor 额度：其 `shared_config.json` 必须与所对照 V25 campaign 配置完全一致。共享 Actor 的请求构建器使用该配置中的 49152；SkillAdam 自身的 `optimizer_transport.max_tokens` 仍为 16384。预检报告分别展示 `actor_max_tokens` 和 `optimizer_max_tokens`。

后续对齐补齐：新配置准备器现在同时默认并发 4、无累计任务时限、实际执行计数和 `execution_only_v1`，不再需要手工补字段。带 `comparison_profile=execution_only_actor48k_v1` 的配置严格检查这些条件与全部模块额度。统一生成与预检入口见 [PAIRED_PREPARATION.md](PAIRED_PREPARATION.md)。已有配置不自动升级。

## 旧配置兼容

正式 Actor 配置接受 16384、32768、49152，拒绝未经确认的其他额度和非法类型。保留 `protocol.DEFAULTS` 中的旧协议默认值用于旧记录重建；新的配置准备器显式覆盖 Actor 额度，不通过修改历史默认值重新解释旧归档。

已保存的 config 和 campaign 不会自动升级。恢复仍要求配置一致、冻结源码一致；不能在旧实验目录中改额度后继续运行，也不重新计算或覆盖旧统计。未来启用新额度应准备新的配置、实验目录和冻结清单。

## 验证范围

配置测试逐项核对全部 V25 模块额度、旧配置兼容及非法额度拒绝。Actor 请求测试通过本地 HTTP 替身检查实际发送的 `max_tokens=49152`，不访问模型服务。SkillAdam 测试验证共享 Actor 的 49152、预检报告以及原生优化器的 16384，保留其压缩、Gate 和 Momentum 流程。

本次验证：相关配置／传输／SkillAdam 测试 52 项通过，随后 V25 全套回归 234 项全部通过。另核对 V25 `_007` 和 SkillAdam `exec30_gen6` 旧实验配置仍保留 Actor 32768。本次没有运行真实模型请求、训练或 Test。
