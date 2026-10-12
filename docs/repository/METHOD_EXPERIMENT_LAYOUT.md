# 第 3 步：统一方法实验目录

> 这是前序步骤的历史记录。兼容链接现已删除，当前状态见 [直接路径整理记录](CANONICAL_PATHS.md)。

执行日期：2026-10-12。统一入口：[v01–v21 方法实验](../../experiments/methods/README.md)。

## 当前归属

```text
experiments/methods/
  README.md
  path-map.json
  migration.json
  v01/ ... v21/
    README.md
    <原实验ID>/
      README.md
      config/     # 实际存在的配置、冻结输入、manifest、Skill 种子
      results/    # 实际存在的精选 JSON 结果
      reports/    # 实际存在的实验报告
```

每个方法版本均有导航。没有配置或结果的实验不补造文件；运行材料目录数量不代表独立实验次数，也不表示运行完成。

| 材料 | 当前归属 |
|---|---|
| v01–v14 的 17 个 Autonomous GSE campaign 包 | 各方法版本、原 campaign ID 下的 `config/`；v04 的三个 seed 分开保留 |
| v01 精选结果与 v14 TGE 计划报告 | 各实验的 `results/` |
| v14 Phase-A Pilot 报告 | `v14/phase_a_unified_v14_step1_pilot/reports/` |
| V15 内嵌实验的 split 与报告 | `v15/benchmark_v2_v15_pilot_001/config/split/`、`reports/` |
| V16 内嵌实验的配置与契约 | `v16/benchmark_v16_one_step_001/config/` 及实验根目录 |
| v17–v21 的方法冻结配置 | 各版本、原实验 ID 下的 `config/` |
| V18 三组联合家族准入配置 | `experiments/benchmarks/tau2/joint-admission/`，从 v18 索引交叉导航 |

剩余 `experiments/campaigns/`、`configs/`、`results/` 中的早期基线和 POC 不按文件名误归为 Autonomous GSE 方法版本。

## 依赖处理

**历史身份与文件位置分离。** 既有 JSON、冻结 manifest、配置和 Skill 内容保留原始字节。41 个相对软链接使旧入口指向新目录中的同一份文件；没有复制数据。旧运行器、测试和冻结源码保持迁移前字节，原哈希校验继续工作。[experiment_paths.py](../../src/skill_evolution/shared/experiment_paths.py) 另提供显式旧路径查询工具，不接管旧运行器，也不读取归档来替代当前文件。

**V20 仍使用 V18 formal_003 的同一冻结包。** V20 配置内旧路径与摘要均保留，读取时解析到 `methods/v18/v18_formal_003/config/`，仍按原摘要检查实际文件；没有复制冻结包或更新哈希使其通过。

**V15/V16 的共享实现与完整运行保持原位。** V16 的 `benchmark_runtime.py` 继续供 V17/V18 导入，配置和初始 Skill 经旧路径兼容链接读取新位置的同一份材料。V15 的 split 也通过兼容链接读取。原始 run、候选 Skill、轨迹和恢复材料仍在原目录，第四步再处理。V14 Pilot 只移出独立报告，没有整体搬动 attempt 目录。

**旧入口与新入口共用一份材料。** V14 TGE 配置包内的 `plan_report.json` 只是指向 `results/` 的文件链接；V15 原报告位置指向新 `reports/`。写入这些旧入口会操作同一目标，不产生第二份结果。本轮不执行这些写入命令。完整运行输出位置不变。

兼容链接是本轮明确保留的例外：`campaigns/`、`configs/` 中仍能看到旧名称，但它们不再持有独立方法材料。日常编辑从新目录进入；在后续解除冻结源码依赖之前不能删除这些链接。链接使用仓库内相对路径，Git 可记录它们。

## 历史证据与核验

- [路径映射](../../experiments/methods/path-map.json)只记录位置，供读取兼容和导航使用。
- [迁移摘要](../../experiments/methods/migration.json)登记实际移动/修改文件的前后哈希。
- [迁移前快照](../archive/method-layout-20261012.zip)保存本轮涉及的既有源码、文档和定义文件，供历史核查；不含原始请求响应或凭据。
- 两次前序快照与迁移记录仍保留；第一步 inventory/path-plan JSON 仍是原盘点时点，不能当作当前执行状态。
- 两份实验日志和完整运行产物不修改；不暂存或提交修改。

```sh
python3 scripts/maintenance/verify_method_layout.py
python3 scripts/maintenance/verify_method_layout.py --manifest experiments/methods/v18/v18_formal_003/config/manifest.json
```

核验明确区分当前源码匹配、历史快照匹配和无法匹配。旧清单可能已有早于本轮的源码漂移；校验会报告，不会改写旧哈希。历史快照匹配仅证明可找回旧字节，不证明当前实现与冻结实现等同。需要严格复现历史实验时，应使用独立历史工作副本。

## 验收

共迁移 108 个既有文件、41 组材料，建立 21 个方法版本入口，并保留 41 个相对兼容链接。对照基线，1,099 个既有 JSON 与 1,081 个既有实验/测试 Python 文件保持原字节；137,681 个本地非版本化文件的位置、大小和修改时间未变。文档无新增断链。

相关测试合计 2,213 项通过、17 项失败；17 项均在迁移前基线中已存在，没有新增失败。新增 7 项路径、身份及摘要拒绝检查通过。V18 formal_003 的 992 个冻结条目全部与当前文件匹配，V20 仍绑定 36 个训练任务与 45 个 Monitor 任务；8 个 τ² edition 结构检查通过。

本机详细记录：[validation.json](../../artifacts/repository_inventory/method-layout-20261012/validation.json)。测试对照迁移前基线，既有失败与新增失败分别登记；没有执行付费模型实验。

下一步为原始运行产物目录整理。此处的每版索引已经列出原始材料位置，可作为第四步的迁移入口。

## 第四步后续状态

本页记录第三步完成时的状态。原始运行现已迁移，见[第四步记录](RUNTIME_LAYOUT.md)；第三步逐文件收据和快照保持原始字节，由后续迁移收据串联校验。
