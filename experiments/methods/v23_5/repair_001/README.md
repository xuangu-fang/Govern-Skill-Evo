# Repair 离线契约与真实输入

本阶段仅准备 Prompt、严格局部输出校验与 R01–R03 输入。没有模型调用、Repair 效果评价、Actor 执行或 Memory 提交。

## 输入来自哪里

使用 `verifier_fact_screen_run_001` 的真实输出，仅选择实际 `CONFLICT`：R01 `[0,4]`、R02 `[0,2]`、R03 `[0,1]`。R03 `[0,3]` 是核验漏检，不加入 Repair，不将基准答案、人工建议或替代文本放入 Prompt。

模型输入只有 `context`、`targets`、`source_records`、`command_sets`。

- 每个 target 包含冻结位置、原始 Knowledge、实际 Verifier issues；这一列表就是允许修改的位置集合，无需重复字段。
- source_records 是上述 Knowledge 的 evidence 与 issues.evidence 的并集，从已去重的冻结 Verifier 输入原样选取。保留完整原始 before/action/after/feedback、身份和局部菜单映射，不做模型摘要、不扩展邻近轨迹。
- command_sets 只保留这些记录实际引用的共享菜单。原始局部 ID、共享 ID、数组顺序和重复项保持原样，并验证还原后的每条记录等于旧输入。
- context 保留真实 Parent、Diff、执行条件，仅保留关联当前执行对。历史记录若有独立上下文仍保留在原记录中。
- 完整候选输出保存在本地用于合并，不作为额外模型输入。轮前 Memory 和原始 payload 通过冻结来源读取用于正式权限校验。

## 局部输出

```json
{"changes":[{"target":{"entry_index":0,"knowledge_index":4},"knowledge":{"text":"修正后的经验","evidence":["diff","Q5:49"]}}]}
```

例子只说明格式，不是实际 Repair 结果。`knowledge: null` 删除该项；不接受空对象、空文本或操作类型字段。必须每个授权位置恰好返回一次，不得增加其他位置。所有位置始终对应冻结候选，删除不会改变其他修改的定位。

严格检查完整 JSON、重复键、字段集合、位置类型、覆盖率、非空文本、引用存在与不重复、正常结束标志。完全未改的 Knowledge 拒绝作为修正。引用必须来自本次提供的 source_records，且合并后仍需通过正式 v23.5 Schema 和历史引用权限校验。

合并仅重建授权 Knowledge，保留所有其他 Knowledge 的值/顺序、Entry 顺序及 revises。删除最后一条 Knowledge、删除 Entry 最后一个 Diff/执行引用会因现有 Schema 被拒绝；不会自动删除 Entry 或改变修订目标。历史条目是否仍成立无法确定性判定，本层保证候选中未授权的旧内容不变，不能追溯证明 Replay 已保留所有应保留的历史经验。R01–R03 无整体替换 Entry，另用结构测试验证有 revises 时的保留行为。

这些校验不证明新文本真实、引用确实支持新表述或问题已解决。Repair 后不再调用第二次语义 Verifier。Prompt 要求修正连带推论、保留有效经验，并避免把反馈的局部反证扩写成全程否定。效果需要后续真实运行与独立审阅。

## 命令

在仓库根目录运行，Python 环境为 `/Users/didi/miniforge3/envs/alfworld/bin/python`：

```bash
python -m unittest experiments.methods.v23_5.repair_001.test_repair -v
python experiments/methods/v23_5/repair_001/prepare.py prepare
python experiments/methods/v23_5/repair_001/prepare.py verify
```

默认输出 `artifacts/methods/v23_5/repair_001/`：Prompt/代码/README/测试冻结副本、manifest、summary、validation；各 case 的 candidate、verifier_output、repair_input、messages。构造拒绝覆盖，verify 校验完整来源链、冻结哈希及输入重建。结果只包含字符/字节统计，不估算 API Token。

以后拿到真实模型响应（包含 finish_reason/content）可执行：

```bash
python experiments/methods/v23_5/repair_001/prepare.py validate \
  --round R01 --response /absolute/path/response.json \
  --result-dir /absolute/path/new_validation_directory
```

失败保存 validation.json，返回非零退出码，不生成合并候选。成功保存局部结果及 `merged_candidate.json`，仍不写入正式 Memory，不标记再次独立语义核验通过。result-dir 必须不存在，避免覆盖任何既有结果。
