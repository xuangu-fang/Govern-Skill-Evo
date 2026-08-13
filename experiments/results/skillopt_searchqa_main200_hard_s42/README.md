# SkillOpt SearchQA Main200 Hard 实验结果

本目录保存 2026-07-31 SkillOpt SearchQA 正式实验的精简结果。

实验使用200道训练题连续运行5个步骤。每一步都会提出一个候选 Skill，然后在一组固定的选择题上评测。评测采用严格完全匹配准确率：只有答案与标准答案完全一致才算正确。候选版本的分数更好时，系统才会接受它。

下文保留程序中的英文名称：`step` 表示步骤，`Candidate` 表示候选版本，`selection` 表示用于选择版本的固定评测，`test` 表示最终独立测试。

## 核心结果

- 选择评测的严格准确率：`0.75 → 0.80`
- 独立测试的严格准确率：`0.90 → 0.91`
- 5个候选版本中，3个被接受、2个被拒绝
- 最佳 Skill 来自第4步

## 文件说明

- `config.json`：程序合并默认值后实际使用的完整配置。
- `summary.json`：实验最终分数、最佳 step 和整体运行统计。
- `history.json`：5个步骤的逐题运行摘要、修改内容、选择评测分数和接受/拒绝决定。
- `skill_v0000.md`：实验开始前的初始 Skill。
- `best_skill.md`：实验最终保留的最佳 Skill。
- `test_baseline_summary.json`：初始 Skill 的独立测试结果。
- `test_final_summary.json`：最佳 Skill 的独立测试结果。
- `steps/step_0004/`：第4步被接受并成为最终最佳 Skill 的候选版本及修改记录。
- `steps/step_0005/`：第5步被评测门槛拒绝的候选版本及修改记录。

step 目录包含：

- `trajectory_digest.json`：该步骤的任务交互和失败原因摘要。
- `merged_patch.json`：汇总后的候选修改集合。
- `ranked_edits.json`：筛选后最终保留的修改。
- `edit_apply_report.json`：各项修改是否成功应用。
- `candidate_skill.md`：应用修改后生成的候选 Skill。
- `step_record.json`：该步骤的分数、耗时和接受/拒绝决定。

## 归档范围

主仓库只归档第4步和第5步的核心文件，用于分别展示一个被接受和一个被拒绝的候选版本。第1至第3步的分数与决定仍保存在 `history.json` 中。

完整的逐题运行记录、提示词、对话、小批次修改和选择评测预测保存在本地：

```text
external/SkillOpt/outputs/searchqa_main200_hard_s42/
```


## 相关文件

- 人工配置：`experiments/configs/skillopt_searchqa_main200_hard_s42.yaml`
- SkillOpt 代码版本：`7da46ae693ee0329b80225c0128a37d65db10e9e`
