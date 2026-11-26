# SkillAdam：UID0007 的 Actor 输出预算

2026-10-29 用户明确要求仅调整 SkillAdam。配置：`experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash_uid0007_64k.json`。

- UID0007：training、validation_parent、validation_candidate 的每次 Actor 请求均为 65536。
- 其他题：32768；优化器生成仍为 16384。
- 思考模式、工具、线程池、24 个模型轮、每个模型轮最多六次总尝试、恢复不补额均保持不变。
- 74 题、8 次迭代，连续失败早停仍关闭。

独立 SkillAdam 包装中的 TaskBudgetRuntime 为 UID0007 创建私有 transport 副本；不修改共享 transport，避免并发任务串用预算。实际 max_tokens 写入 HTTP 请求，该题 Actor state 和完成记录也记录实际 65536。全局默认 Actor JSON 保持 32768；任务例外在训练 plan 的 config.actor_task_output_limits 中冻结。恢复同时校验配置和启动包装源码哈希。

使用新运行目录 `experiments/baselines/skilladam_officeqa_train74_epoch1_deepseek_flash_uid0007_64k_20261029_001`。从旧 `_corrected_v2_20261029_002` 运行导入首批状态：8 道完成题的结果直接复用；UID0030 原样续跑，原 requesting 请求按未知结果计入已消费额度；UID0007 不在原目录修改身份，而从首次请求以 65536 重新执行。旧 UID0007 的全部请求与费用证据保留在原运行中，不能把此次新执行称为原请求额度的恢复或把旧请求记成零。尚未进入任何优化器阶段，因而不迁移或重算优化器 checkpoint。

新目录的 task_budget_import.json 记录原目录、导入文件哈希、复用题目、继续题目和新执行题目。导入只复制文件，不修改旧目录，不重标旧结果的预算。Parent/Candidate 的 UID0007 均从第一轮起使用相同 65536。

启动与恢复（第一次导入完成后也用 --resume）：

```sh
conda activate OfficeQA
python scripts/runs/run_officeqa_skilladam_task_budget.py train \
  experiments/baselines/skilladam_officeqa_train74_epoch1_deepseek_flash_uid0007_64k_20261029_001 \
  --config experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash_uid0007_64k.json \
  --start --resume
```

离线验收覆盖实际请求体、Parent/Candidate 一致、并发隔离、其他题原样恢复、旧预算身份拒绝复用，以及 65536 下仍最多六次尝试。另在临时目录完整演练真实首批状态导入并校验源目录字节未变。记录：`artifacts/benchmarks/officeqa/uid0007_budget65536_20261029_001/`。
