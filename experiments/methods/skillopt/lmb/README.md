# SkillOpt · LiveMathematicianBench

三次独立训练均保存原生配置、保留的 Skill 和逐题回执。训练与选优题次包含初始 Selection、普通更新和慢更新的完整作答。

| 训练 | 最佳 Skill 来源 | 训练与选优题次 | DeepSeek Flash Test124 |
|---|---|---:|---|
| [第一次原生训练](lmb_skillopt_deepseek_flash/README.md) | 第 4 轮普通更新 | 404 | 首测 93/123，补测合并后 94/124 |
| [第二次原生训练](lmb_skillopt_deepseek_flash_repeat_20261123_010400/README.md) | 第 3 轮慢更新 | 386 | 首测 90/124，复测 89/122 |
| [第三次 native feedback 训练](lmb_skillopt_native_feedback_20261124/README.md) | 第 4 轮普通更新 | 404 | 86/124、91/124、89/124 |

第三次训练的 DeepSeek Flash 结果进入[三方法主对照](../../lmb/README.md)。同一最终 Skill 的 GPT‑5.4 mini 评测和已存的 Meta53、Other71 批次可从[专项评测](lmb_skillopt_native_feedback_20261124/README.md#专项评测)定位。

上游发布的 [Skill](upstream_meta53/skill.md) 独立使用 DeepSeek Flash 测得 Meta53 **16/53**。其[版本绑定](../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_upstream_meta53_20261124/binding.json)记录上游提交、文件路径、Skill SHA-256 和 53 道题目 ID。[原始评分](../../../../artifacts/methods/skillopt/lmb/lmb_skillopt_upstream_meta53_20261124/summary.json)

## 离线读回

从仓库根目录运行以下命令，验证两次原生训练的回执、三次运行的精选 Skill、11 条历史与专项评测，以及每项不完整评测的缺题 ID。

```sh
python3 scripts/verification/verify_lmb_skillopt_archive.py
```

[历史索引](history.json) · [归档还原](../../../benchmark_record_refs/README.md) · [主对照离线读回](../../lmb/README.md#离线读回)
