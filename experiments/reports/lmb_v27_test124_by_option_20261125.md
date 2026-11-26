# LMB v27 系列测试成绩

正式测试清单含 124 个固定题目 ID。按展示的选项是否逐字包含整项 “One of the remaining options is correct, but a stronger result can be proven.” 分成 53 题与 71 题。单元格为答对数 / 已评分数，百分比使用已评分数作分母。缺失结果不计入正确或错误。[测试清单](../../artifacts/methods/v27_18/v27_18_lmb53_repeat_20261125_192207/evaluations/v27_18_lmb53_repeat_20261125_192207_test124/evaluation.json)

同一版本的独立训练、不同 Actor、复测和中间轮分别列出。每份记录按题目 ID 去重，能对应同一评测的补测填入其缺失项。部分历史评测提高了输出预算或重试次数。目录名中的 test32 指 32 并发。v27.6、v27.14、v27.16 在本工作区未找到可归属的测试作答。

## 版本结果与最终 Skill 的复测

| 归档或实验 | 测试 Actor | 含指定项（53 题） | 其余（71 题） | 全部已评分 |
|---|---|---:|---:|---:|
| [v27_lmb124_actor49152_20261031_152036](../../artifacts/methods/v27/v27_lmb53_actor49152_20261031_152036/evaluations/v27_lmb124_actor49152_20261031_152036) | deepseek-flash | 14/53（26.4%） | 44/70（62.9%） | 58/123（47.2%） |
| [v27_1_lmb53_20261104_test](../../artifacts/methods/v27_1/v27_1_lmb53_20261104_132025/evaluations/v27_1_lmb53_20261104_test) | deepseek-flash | 19/53（35.8%） | 36/70（51.4%） | 55/123（44.7%） |
| [v27_2_diag_v3_precond_v3_lmb53_20261105_210532_test](../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/evaluations/v27_2_diag_v3_precond_v3_lmb53_20261105_210532_test) | deepseek-flash | 16/53（30.2%） | 39/71（54.9%） | 55/124（44.4%） |
| [v27_2_diag_v3_precond_v3_test32_20261108_1811](../../artifacts/methods/v27_2/v27_2_diag_v3_precond_v3_lmb53_20261105_210532/evaluations/v27_2_diag_v3_precond_v3_test32_20261108_1811) | deepseek-flash | 18/53（34.0%） | 36/70（51.4%） | 54/123（43.9%） |
| [v27_2_precond_v3_lmb53_20261105_131046_test](../../artifacts/methods/v27_2/v27_2_precond_v3_lmb53_20261105_131046/evaluations/v27_2_precond_v3_lmb53_20261105_131046_test) | deepseek-flash | 15/53（28.3%） | 35/69（50.7%） | 50/122（41.0%） |
| [v27_3_lmb53_20261113_test](../../artifacts/methods/v27_3/v27_3_lmb53_20261113/evaluations/v27_3_lmb53_20261113_test) | deepseek-flash | 15/53（28.3%） | 40/70（57.1%） | 55/123（44.7%） |
| [v27_4_lmb53_20261113_1200_test](../../artifacts/methods/v27_4/v27_4_lmb53_20261113_1200/evaluations/v27_4_lmb53_20261113_1200_test) | deepseek-flash | 11/53（20.8%） | 38/70（54.3%） | 49/123（39.8%） |
| [v27_5_lmb53_20261113_test](../../artifacts/methods/v27_5/v27_5_lmb53_20261113/evaluations/v27_5_lmb53_20261113_test) | deepseek-flash | 16/53（30.2%） | 38/70（54.3%） | 54/123（43.9%） |
| [v27_7_lmb53_20261114_test](../../artifacts/methods/v27_7/v27_7_lmb53_20261114/evaluations/v27_7_lmb53_20261114_test) | deepseek-flash | 0/1（0.0%） | 3/5（60.0%） | 3/6（50.0%） |
| [v27_8_lmb53_20261114_test](../../artifacts/methods/v27_8/v27_8_lmb53_20261114/evaluations/v27_8_lmb53_20261114_test) | deepseek-flash | 12/53（22.6%） | 41/70（58.6%） | 53/123（43.1%） |
| [v27_9_lmb53_20261114_test_project_v41](../../artifacts/methods/v27_9/v27_9_lmb53_20261114/evaluations/v27_9_lmb53_20261114_test_project_v41) | deepseek-v4.1-flash | 8/52（15.4%） | 35/69（50.7%） | 43/121（35.5%） |
| [v27_10_lmb53_20261115_test_project_v41](../../artifacts/methods/v27_10/v27_10_lmb53_20261115/evaluations/v27_10_lmb53_20261115_test_project_v41) | deepseek-v4.1-flash | 16/52（30.8%） | 32/70（45.7%） | 48/122（39.3%） |
| [v27_11_lmb53_20261115_test_project_v41](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_lmb53_20261115_test_project_v41) | deepseek-v4.1-flash | 23/53（43.4%） | 38/71（53.5%） | 61/124（49.2%） |
| [v27_11_lmb53_repeat_20261117_140123_test_project_v41](../../artifacts/methods/v27_11/v27_11_lmb53_repeat_20261117_140123/evaluations/v27_11_lmb53_repeat_20261117_140123_test_project_v41) | deepseek-v4.1-flash | 12/51（23.5%） | 35/66（53.0%） | 47/117（40.2%） |
| [v27_12_lmb53_20261118_test_deepseek_flash](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_test_deepseek_flash) | deepseek-flash | 25/53（47.2%） | 39/71（54.9%） | 64/124（51.6%） |
| [v27_12_lmb53_20261118_test_gpt_5_4_mini](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_test_gpt_5_4_mini) | gpt-5.4-mini | 10/53（18.9%） | 33/71（46.5%） | 43/124（34.7%） |
| [v27_13_lmb53_20261124_test_deepseek_flash](../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash) | deepseek-flash | 33/53（62.3%） | 36/71（50.7%） | 69/124（55.6%） |
| [v27_13_lmb53_20261124_test_deepseek_flash_retest1](../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash_retest1) | deepseek-flash | 40/53（75.5%） | 33/71（46.5%） | 73/124（58.9%） |
| [v27_13_lmb53_20261124_test_deepseek_flash_retest2](../../artifacts/methods/v27_13/v27_13_lmb53_20261124/evaluations/v27_13_lmb53_20261124_test_deepseek_flash_retest2) | deepseek-flash | 31/53（58.5%） | 39/71（54.9%） | 70/124（56.5%） |
| [v27.15](../../artifacts/methods/v27_15/v27_15_lmb53_20261125/evaluations/v27_15_vs_v27_17_final_meta53_20261125/v27_15) | deepseek-flash | 17/50（34.0%） | — | 17/50（34.0%） |
| [v27.17](../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_lmb53_20261125_test124) | deepseek-flash | 43/53（81.1%） | 37/71（52.1%） | 80/124（64.5%） |
| [v27.17 retest](../../artifacts/methods/v27_17/v27_17_lmb53_20261125/evaluations/v27_17_final_meta53_retest1_20261125) | deepseek-flash | 19/23（82.6%） | — | 19/23（82.6%） |
| [v27_18_lmb53_repeat_20261125_192207_test124](../../artifacts/methods/v27_18/v27_18_lmb53_repeat_20261125_192207/evaluations/v27_18_lmb53_repeat_20261125_192207_test124) · [单题补测](../../artifacts/methods/v27_18/v27_18_lmb53_repeat_20261125_192207/evaluations/v27_18_lmb53_repeat_20261125_192207_202511_24_81920/result.json) | deepseek-flash | 53/53（100.0%） | 38/71（53.5%） | 91/124（73.4%） |
| [v27.18 first](../../artifacts/methods/v27_18/v27_18_lmb53_20261125/evaluations/v27_18_lmb53_20261125_test124) · [53 题](../../artifacts/methods/v27_18/v27_18_lmb53_20261125/evaluations/v27_18_final_meta53_20261125) | deepseek-flash | 42/53（79.2%） | 41/69（59.4%） | 83/122（68.0%） |

## 中间轮、基线和单独对照（含部分评测）

| 归档或实验 | 测试 Actor | 含指定项（53 题） | 其余（71 题） | 全部已评分 |
|---|---|---:|---:|---:|
| [lmb124_round_skills_project_v41_20261116/shared_R00](../evaluations/lmb124_round_skills_project_v41_20261116/shared_R00) | deepseek-v4.1-flash | 4/53（7.5%） | 35/71（49.3%） | 39/124（31.5%） |
| [lmb124_round_skills_project_v41_20261116/v27_11_R01](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/lmb124_round_skills_project_v41_20261116/v27_11_R01) | deepseek-v4.1-flash | 6/53（11.3%） | 40/71（56.3%） | 46/124（37.1%） |
| [lmb124_round_skills_project_v41_20261116/v27_11_R03](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/lmb124_round_skills_project_v41_20261116/v27_11_R03) | deepseek-v4.1-flash | 5/53（9.4%） | 45/71（63.4%） | 50/124（40.3%） |
| [lmb124_round_skills_project_v41_20261116/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/lmb124_round_skills_project_v41_20261116/v27_11_R04) | deepseek-v4.1-flash | 4/53（7.5%） | 39/71（54.9%） | 43/124（34.7%） |
| [v27_11_R04_repeat_project_v41_20261116/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261116/v27_11_R04) | deepseek-v4.1-flash | 5/52（9.6%） | 36/70（51.4%） | 41/122（33.6%） |
| [v27_11_R04_repeat_project_v41_20261117_0238/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261117_0238/v27_11_R04) | deepseek-v4.1-flash | 3/53（5.7%） | 40/71（56.3%） | 43/124（34.7%） |
| [v27_11_R04_repeat_project_v41_20261117_110952/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261117_110952/v27_11_R04) | deepseek-v4.1-flash | 5/52（9.6%） | 32/69（46.4%） | 37/121（30.6%） |
| [v27_11_R04_repeat_project_v41_20261118_021739/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261118_021739/v27_11_R04) | deepseek-v4.1-flash | 2/29（6.9%） | 19/45（42.2%） | 21/74（28.4%） |
| [v27_11_R04_repeat_project_v41_20261118_073949/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261118_073949/v27_11_R04) | deepseek-v4.1-flash | — | — | — |
| [v27_11_R04_repeat_project_v41_20261118_074003/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261118_074003/v27_11_R04) | deepseek-v4.1-flash | — | — | — |
| [v27_11_R04_repeat_project_v41_20261118_074025/v27_11_R04](../../artifacts/methods/v27_11/v27_11_lmb53_20261115/evaluations/v27_11_R04_repeat_project_v41_20261118_074025/v27_11_R04) | deepseek-v4.1-flash | 4/53（7.5%） | 40/71（56.3%） | 44/124（35.5%） |
| [v27_11_repeat_final_stronger51_retest_20261117](../../artifacts/methods/v27_11/v27_11_lmb53_repeat_20261117_140123/evaluations/v27_11_repeat_final_stronger51_retest_20261117) | deepseek-v4.1-flash | 6/27（22.2%） | — | 6/27（22.2%） |
| [lmb124_final_skill_retests_20261120_2022/v27_12_R03_repeat4](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_R03_repeat4) | deepseek-flash | 24/53（45.3%） | 38/70（54.3%） | 62/123（50.4%） |
| [v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R00](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R00) | deepseek-flash | 5/53（9.4%） | 39/71（54.9%） | 44/124（35.5%） |
| [v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R01](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R01) | deepseek-flash | 24/53（45.3%） | 40/71（56.3%） | 64/124（51.6%） |
| [v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R02](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_checkpoints_R00_R02_deepseek_flash/R02) | deepseek-flash | 28/53（52.8%） | 38/71（53.5%） | 66/124（53.2%） |
| [v27_12_lmb53_20261118_repeat_R02_R03_deepseek_flash_20261119/R02](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_repeat_R02_R03_deepseek_flash_20261119/R02) | deepseek-flash | 34/53（64.2%） | 40/71（56.3%） | 74/124（59.7%） |
| [v27_12_lmb53_20261118_repeat_R02_R03_deepseek_flash_20261119/R03](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_repeat_R02_R03_deepseek_flash_20261119/R03) | deepseek-flash | 23/53（43.4%） | 38/71（53.5%） | 61/124（49.2%） |
| [v27_12_lmb53_20261118_repeat_R03_third_deepseek_flash_20261119/R03](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_repeat_R03_third_deepseek_flash_20261119/R03) | deepseek-flash | 26/53（49.1%） | 40/71（56.3%） | 66/124（53.2%） |
| [v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R01](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R01) | deepseek-flash | 21/53（39.6%） | 36/71（50.7%） | 57/124（46.0%） |
| [v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R02](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R02) | deepseek-flash | 33/53（62.3%） | 37/71（52.1%） | 70/124（56.5%） |
| [v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R03](../../artifacts/methods/v27_12/v27_12_lmb53_20261118/evaluations/v27_12_lmb53_20261118_serial_repeat_R01_R03_deepseek_flash_20261119/R03) | deepseek-flash | 26/53（49.1%） | 39/71（54.9%） | 65/124（52.4%） |
| [v27.18 with R04](../../artifacts/methods/v27_18/v27_18_lmb53_20261125/evaluations/v27_18_final_with_r04_meta53_20261125) | deepseek-flash | 51/53（96.2%） | — | 51/53（96.2%） |
