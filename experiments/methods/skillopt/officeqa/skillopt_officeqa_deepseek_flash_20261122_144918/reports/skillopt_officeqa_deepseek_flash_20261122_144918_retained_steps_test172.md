# OfficeQA SkillOpt 各步保留 Skill 的测试集成绩

固定测试集为 172 道题，成功率按精确匹配（EM）计算。第 1、2 步各独立测试一次。第 3～8 步的保留文件哈希相同，共用第 3 步三次测试的 EM 中位数。

| Epoch | Step | 保留文件 | 答对题数 | 测试集 EM | 取值方式 |
|---:|---:|---|---:|---:|---|
| 1 | 1 | `skill_v0001.md` | 122/172 | 70.93% | 单次实测 |
| 1 | 2 | `skill_v0002.md` | 117/172 | 68.02% | 单次实测 |
| 2 | 3 | `skill_v0003.md` | 121/172 | 70.35% | 三次测试中位数 |
| 2 | 4 | `skill_v0004.md` | 121/172 | 70.35% | 复用第 3 步中位数 |
| 3 | 5 | `skill_v0005.md` | 121/172 | 70.35% | 复用第 3 步中位数 |
| 3 | 6 | `skill_v0006.md` | 121/172 | 70.35% | 复用第 3 步中位数 |
| 4 | 7 | `skill_v0007.md` | 121/172 | 70.35% | 复用第 3 步中位数 |
| 4 | 8 | `skill_v0008.md` | 121/172 | 70.35% | 复用第 3 步中位数 |

第 3 步三次分别答对 124、121、120 题。第 2 步比第 1 步多一段空的 slow-update 标记，仅凭各一次测量无法判断标记对成功率的影响。

## 原始报告

- [第 1 步](../results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step01_test172_20261122_213534/report.md)
- [第 2 步](../results/skillopt_officeqa_deepseek_flash_20261122_144918_retained_step02_test172_20261122_213534/report.md)
- [第 3 步第一次](../results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172/report.md)
- [第 3 步第二次](../results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat2_20261122_204658/report.md)
- [第 3 步第三次](../results/skillopt_officeqa_deepseek_flash_20261122_144918_best_test172_repeat3_20261122_205701/report.md)
