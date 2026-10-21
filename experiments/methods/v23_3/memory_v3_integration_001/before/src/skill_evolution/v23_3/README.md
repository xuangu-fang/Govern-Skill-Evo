# Govern V23.3

状态：2026-10-20 完成 P0/P1、P1-R 和 P2 最小工程实现与离线验证；未注册默认方法，未运行真实模型或环境实验。

代码基线是正式 V23 commit `08c442f202f05a25a0c30412ef89f8312df0c0f0`，不是 V23.2。复用 V23 的事实输入、Schema 校验、Unified Diff 引擎、编译器和 Editor 策略；只增加本版 Prompt、转换器与必要加载入口。

核心研究问题：历史实际编辑及其条件化行为响应，能否改善当前 Update 的变换选择，并最终提高任务表现？Unified Diff 仅承担修改落实。

从 [P0/P1 决策](../../../experiments/methods/v23_3/P0_P1_DECISION.md)进入设计历史；当前实现与边界见 [P2 决策](../../../experiments/methods/v23_3/p2_offline_001/P2_FINAL_DECISION.md)。

调用入口：

- `diagnosis.run_diagnosis(grouping_directory, directory, generate=...)`
- `preconditioner.run_preconditioner(grouping_directory, diagnosis_directory, directory, generate=..., memory=...)`
- `editor.run_editor(preconditioner_directory, directory, generate=...)`

每个入口均有同模块 `load_*`，并沿版本匹配的上游链恢复验证。`generate(messages, directory)` 沿用已有注入式接口；本次只使用 Fake。恢复时必须传回相同 Memory 和调用配置。大体积历史输入需显式声明合适的 `max_input_chars`，不自动截断。

`normalize_update_patches(result, payload)` 返回 `(normalized, effective_plan)`；结构拆合和新 ID 暂不支持。旧单行 text 不迁移，合法停点不进入 Editor。

离线复现：

```sh
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/run_tests.py D
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/build_mock_archive.py
```

最终回归 434 项通过，仅证明工程贯通。第二条命令使用明确标记的人工 Mock，已有归档则只重载；没有真实模型、Replay 或完整自进化入口。P2 完成后停止，P3 需另行授权。
