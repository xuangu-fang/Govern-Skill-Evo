# SkillOpt SearchQA Main200 Hard Results

本目录保存 2026-07-31 SkillOpt SearchQA 正式实验的精简结果。实验使用 200 道训练题运行 5 个 step，通过固定 selection set 上的 hard exact-match accuracy 决定是否接受 Candidate Skill。

## 核心结果

- Selection hard：`0.75 → 0.80`
- Test hard：`0.90 → 0.91`
- 5 个 Candidate 中接受 3 个、拒绝 2 个
- 最佳 Skill 来自 Step 4

## 文件说明

- `config.json`：程序合并默认值后实际使用的完整配置。
- `summary.json`：实验最终分数、最佳 step 和整体运行统计。
- `history.json`：5 个 step 的 rollout、patch、edit、selection 分数和 gate 决策。
- `skill_v0000.md`：实验开始前的初始 Skill。
- `best_skill.md`：实验最终保留的最佳 Skill。
- `test_baseline_summary.json`：初始 Skill 的独立 test 结果。
- `test_final_summary.json`：最佳 Skill 的独立 test 结果。
- `steps/step_0004/`：被接受并成为最终最佳 Skill 的 Candidate 及其 edit 记录。
- `steps/step_0005/`：被 validation gate 拒绝的 Candidate 及其 edit 记录。

step 目录包含：

- `trajectory_digest.json`：该 step 的轨迹与失败模式摘要。
- `merged_patch.json`：Aggregate 后的候选 edit 集合。
- `ranked_edits.json`：Select 后最终保留的 edit。
- `edit_apply_report.json`：edit 的实际应用状态。
- `candidate_skill.md`：应用 edit 后生成的 Candidate Skill。
- `step_record.json`：该 step 的分数、耗时和 gate 决策。

## 归档范围

主仓库只归档 Step 4 和 Step 5 的核心文件，用于展示一个 accepted Candidate 和一个 rejected Candidate。Step 1–3 的分数与 gate 决策仍保存在 `history.json` 中。

完整的逐题 rollout、prompt、conversation、minibatch patch 和 selection prediction 保存在本地：

```text
external/SkillOpt/outputs/searchqa_main200_hard_s42/
```


## 相关文件

- 人工配置：`experiments/configs/skillopt_searchqa_main200_hard_s42.yaml`
- SkillOpt commit：`7da46ae693ee0329b80225c0128a37d65db10e9e`
