# v28.11 SearchQA

本版以 v28.9 `reusable_actions_v1` 为基线，检验三个模块能否保住影响作答的判别条件，同时合并重复指导。历史参照为 v28.5 `promptv2` 的 1,182/1,400 和 v28.10 的 7,027 字符。长度作为观察指标。

- [Diagnosis](prompts/diagnosis.md) 调整已有默认做法时，从当前批次寻找需要保留原行为的成功题，把判别线索与直接引用传给下游。
- [Preconditioner](prompts/preconditioner.md) 检查 Parent 能否区分有竞争力的答案，在有效更新中保留 Actor 作答时可见的条件。
- [Editor](prompts/editor.md) 在获准范围内把同一判断写在一处，合并导向同一选择的说明。

方法标识为 `v28_11_campaign_v1`，三份修订 prompt 使用 `decision_boundaries_v1` 后缀。[Replay](prompts/replay.md) 沿用 v28.9 的文本和版本标识。训练配置继承相同顺序的 600 道题、10 个 batch、初始 skill、空 Memory 和独立的 1,400 道测试题。

从仓库根目录执行离线预检：

```sh
python scripts/runs/run_v28_11_campaign.py train experiments/campaigns/v28_11_searchqa600_batch60 \
  --config experiments/configs/v28_11_searchqa_train600_batch60.json --validate-only
python -m unittest tests.skill_evolution.v28_11.test_prompt_binding
```

第一条命令校验配置、数据划分与运行时 prompt。第二条使用临时目录、合成题目和预写响应检查实际阶段调用、最终评测准备与恢复。
