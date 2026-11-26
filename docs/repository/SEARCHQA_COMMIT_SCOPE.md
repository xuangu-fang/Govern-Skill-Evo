# SearchQA v28 提交范围与验收

分支为 `wyy/day60-tau-autonomous-gse-v28`，从 `wyy/day58-tau-autonomous-gse-v26` 的 `7a50f728dd8` 建立。逐文件变更可用 `git diff --name-status 7a50f728dd8..HEAD` 查看。

| 提交 | 范围 |
| --- | --- |
| `773111b814d` | v28–v28.16 方法实现、运行与验证入口、测试、方法文档、环境及数据锁。共享 v27 文件限于 SearchQA 调用所需的依赖。 |
| `f5f0387d073` | 39 条训练记录和 96 次评测对应的精选材料、三份验收清单、图表与离线读回入口。 |
| 导航与本说明 | 方法总索引接入 SearchQA，登记复核所需的本机材料。 |

[SearchQA 实验索引](../../experiments/methods/SEARCHQA.md) · [整理盘点](SEARCHQA_INVENTORY.md) · [早期和历史基线验收回执](../../experiments/benchmarks/searchqa/remaining-history-verification.json)

## 从独立检出复核

分支包含 SearchQA 数据锁、2,000 道题的 ID 和冻结分批。运行和逐题复算时，按锁文件指向的原路径接入 `data/searchqa/prepared_v1/{train,val,test}/items.json`。原题、完整运行和压缩记录留在本机。压缩清单和共享内容位于 `experiments/benchmark_record_refs/searchqa/`。各验收清单以仓库相对路径登记精选文件的来源、评测计划、受测文本和逐题回执。Main200 的两份 Test100 逐题记录在 SkillOpt 原始输出目录。[环境说明](../../benchmarks/searchqa/README.md) · [归档恢复说明](../../experiments/benchmark_record_refs/README.md)

三份验收均支持从仓库根目录运行。将上段所列输入接到原路径后，以 `SearchQA` 环境运行。

```sh
for bundle in main-comparison v28_11-v28_15 remaining-history; do
  conda run -n SearchQA python -B scripts/runs/searchqa/verify_comparison.py \
    --manifest "experiments/benchmarks/searchqa/$bundle.json" || exit
done
```

独立工作树在禁网环境下复跑了三份清单，**96 次评测与 131,800 份逐题评分**均与已有验收回执一致。环境检查核对了数据锁中的 13 个文件。入口测试在复原所需历史输入后完成了 v28.16 的训练与 Test 预检、SkillAdam 冻结配置预检，以及 SkillOpt 运行配置、40 步日程和已选 Skill 核对。

历史运行入口使用 `external/SkillAdam/` 和 `external/SkillOpt/` 的本机上游检出。SkillAdam 精确历史预检还读取冻结清单列出的 19 份本机 v27 快照文件，以复核全部 377 项历史源码哈希。临时入口验收按独立目录实际位置绑定历史绝对路径，归档中的冻结配置保持原字节。

直接使用历史绝对路径的单测全量检查在发现 8 个配置路径或压缩输入问题后停止。仅在临时副本中重绑路径并还原冻结输入后，40 项聚焦单测及 63 个子测试通过，已观察到的 8 个失败也全部复验通过。
