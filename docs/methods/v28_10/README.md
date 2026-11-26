# v28.10 SearchQA

基线为已完成的 v28.9 实验 `v28_9_searchqa600_batch60_reusable_actions_v1_20261106_120000`。四个模型模块中，仅调整 [Preconditioner](prompts/preconditioner.md) 对 Original Update 的取舍标准。

Preconditioner 依据 Parent、当前训练证据和相关 Memory，提炼 Actor 在新题上可以观察、比较或保留的判断依据。修改已有步骤时，交给 Editor 的是修改后的判断。若 Original 只给已有判断增加例子，则撤回。若多个答案都合理，而选择依据只来自参考答案，则允许该问题暂时无解。短对照只在比增加条件更能说明区别时使用。

方法标识为 `v28_10_campaign_v1`，Preconditioner 标识为 `v28_10_searchqa_preconditioner_reusable_increment_v1`。从仓库根目录可运行以下离线预检。

```sh
python scripts/runs/run_v28_10_campaign.py train experiments/campaigns/v28_10_searchqa600_batch60 \
  --config experiments/configs/v28_10_searchqa_train600_batch60.json --validate-only
```

已与 v28.9 的训练归档核对四个实际加载的 prompt、600 道训练题的顺序、10 个大小为 60 的批次、104 字符初始 Skill 和空 Memory，并与评测归档核对 1400 道测试题的顺序。已有 validator 支持整轮撤回，也可从任意位置选取最多四个 KEEP 或 REPLACE，选中五个会触发输出校验错误。
