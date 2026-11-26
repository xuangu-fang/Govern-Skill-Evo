# SkillAdam OfficeQA 正式配置

后续正式训练、续跑与评分见 [OfficeQA SkillAdam 实验索引](../../../experiments/methods/skilladam/officeqa/README.md)。

当前 SkillAdam 运行已采用 UID0007 专用 65536 Actor 预算；其余题仍为 32768。新配置、状态导入与启动命令见 [UID0007 预算说明](SKILLADAM_UID0007_BUDGET.md)。下文保留前一版统一 32768 配置的来源记录。

本次配置已准备；2026-10-29 按用户要求关闭连续失败提前停止，离线验收通过后启动训练。配置文件：`experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash.json`；公共 Actor：`experiments/configs/officeqa_actor_deepseek_flash.json`，与正在运行的 V26 正式配置中的 Actor 对象逐字段一致。

## 参数来源

SkillAdam 上游 `skilladam/experiments/main_results.json` 的 OfficeQA 主实验，以及 `configs/backends/gpt55_main_result.example.json` 指定优化器输出上限 16384。通用示例中的 4096 不是此 benchmark 的主实验预算。本次 patch、LLM 轨迹压缩、Momentum 均使用原生同一生成 transport，输出上限均为 16384。

模型和路由改为与 V26 相同的 deepseek-flash / api.deepseek.com，思考 enabled、effort medium、temperature 1。公共 Actor 输出 32768，workers=4，300 秒超时、直接 HTTP、六次总尝试。优化器仍使用原生 SDK（max_retries=2），300 秒超时；原生应用层重试保留，不套用公共 Actor 的六次策略。

74 题池按 V26 的原 Train 50 + Validation 24 顺序，sequential、seed=42、不打乱，same_batch 验证。逐批 ID 已核验相同：7 批 10 题、末批 4 题，最多 8 次迭代。上游 profile 的 max/min iterations 是 15/5；其顺序采样器对这 74 题也只生成一遍的 8 批，本次显式将 max_iterations 冻结为 8。

2026-10-29 按用户要求，仅将 `max_consecutive_failures` 从 3 改为 99。由于本次仅有 8 次迭代，该阈值不可触发，从配置层关闭连续失败提前停止；`min_iterations=5` 及所有其他配置保持不变。正常执行将遍历全部 74 题、8 批，即使候选持续未被接受也继续。技术错误或请求额度耗尽仍会保存现场并停止，不通过自动扩额强行完成。V26 的 continue_no_change 不迁入 SkillAdam。

保留 OfficeQA 主实验的 prompt_profile（officeqa-main-result）与原生执行参数 gate_profile（main-result）、LLM 轨迹压缩、110000 优化器上下文估算限制、自适应编辑预算（em，v_max=0.05，base=4，minimum=1，beta=0.9）与 Momentum。初始 Skill 使用既定 SkillOpt initial.md，不调用 Stage0。最终 Test 不在训练中启动。

## DeepSeek 启动入口

使用 `scripts/runs/run_officeqa_skilladam_deepseek.py`，该独立包装将 `thinking: {type: enabled}` 注入每个原生 SDK 请求，原生响应解析、重试、工具结果处理和优化器历史保持不变。包装源码哈希写入配置及训练 plan，恢复时校验。不修改正在运行的 V26 所冻结的 src 或 external 源文件。

原生 Momentum 是一次生成工具调用、本地应用结果，下一次请求不续接该工具轮；patch 历史是普通 user/assistant 内容。这里没有公共 Actor 那种跨工具轮续传 reasoning_content 的链路；思考文本也不添加到原生优化器历史或轨迹证据。公共 Actor 已有的思考回传、持久化和恢复机制照常使用。

必须使用这个 DeepSeek 包装入口，通用 `run_officeqa_baselines.py train` 不读取本配置的 DeepSeek thinking 扩展。

```sh
conda activate OfficeQA
python scripts/runs/run_officeqa_skilladam_deepseek.py preflight \
  experiments/baselines/skilladam_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_002 \
  --config experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash.json

# 下面命令启动真实训练；已有运行必须使用 --resume，勿重复启动。
python scripts/runs/run_officeqa_skilladam_deepseek.py train \
  experiments/baselines/skilladam_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_002 \
  --config experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash.json --start
```

默认从 .env 安全读取 key 与 URL，不把凭据写入配置或命令行。恢复时同命令添加 `--resume`，仍遵循原生 checkpoint 边界与公共 Actor 不补额规则。报告与计划预检见 `artifacts/benchmarks/officeqa/skilladam_formal_preflight_20261029_001/`。

关闭提前停止的验收及启动记录：`artifacts/benchmarks/officeqa/skilladam_full8_training_20261029_001/`。原配置快照保留为 config_before.json；配置差异仅为 max_consecutive_failures。

首次启动因 gate_profile 使用了说明标签而非执行参数在请求前退出；该现场保留于运行目录 _001。已改为上游 planning.py 实际传入的 main-result，OfficeQA 原生 Gate 的 EM/F1 阈值不变。新启动目录 _002；验收与启动记录见 skilladam_full8_training_20261029_002。
