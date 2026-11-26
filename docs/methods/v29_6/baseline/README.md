# v29.5 冻结基线

冻结日期：2026-11-05。本目录仅供设计对照，不是可执行的 v29.6 配置。

- prompts/diagnosis.md、preconditioner.md、editor.md：逐字复制 v29.5 实际加载的三份本地 Prompt。
- prompts/replay.md：逐字复制 v29.5 实际加载的 `src/skill_evolution/v29_2/prompts/replay.md`，不是另造的 v29.5 Replay 文件。
- v29_5_config.json：原运行配置，保留全部参数、批次 IDs 和方法身份。
- actor/：共享 DocVQA Actor 原始 system/user/runtime 与初始 Skill。
- split_ids.json、optimization160_manifest.json：原数据分区/顺序与优化池身份；未复制 Test 问题、答案或图像。
- README_v29_5.md：原设计/实现说明快照，其中历史状态不代表本次运行状态。

逐文件原始路径与 SHA-256 见 [source_map.json](../source_map.json)。v28.5 首次冻结 Prompt 是设计迁移参考，另存于 [sources/v28_5_initial/prompts](../sources/v28_5_initial/prompts/)，不替代本目录的直接基线。
