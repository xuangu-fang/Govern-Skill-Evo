# OfficeQA v26.1 独立运行与离线验收

实现日期：2026-11-04。已建立独立运行链路；真实训练和真实 Test 均未启动。原设计、Prompt、基线副本和历史实验保留。

## 实现位置

- `src/skill_evolution/v26_1/`：四模块、OfficeQA 事实与无损输入、逐 Update Gate、digest HEAD Memory、阶段 journal、训练、独立评估和只读统计。
- `scripts/runs/run_v26_1_campaign.py`：独立 `train` / `test` 入口；需要显式配置和凭据环境变量名才能发起真实请求。
- `experiments/configs/v26_1_officeqa_train74.json`：可执行配置。设计文件 `experiment_plan.json` 仍是原始设计快照，不用作 CLI 配置。
- `scripts/verification/verify_v26_1_campaign.py`：禁止网络及子进程的验收器，使用临时合成数据；真实 release 仅只读预检。
- `tests/skill_evolution/v26_1/`：新链路合同、选择、恢复、隔离与完整合成调度用例。

## 运行合同

方法由独立四模块驱动。Diagnosis 读取完整 Parent 批次；Preconditioner 只读取 Plan 引用的完整 runs 和历史 Memory；Editor 只读取 Parent 与有效 id/text；Replay 只读取 EM 翻转题的完整 P/Q，执行逐事件来源校验。标准答案和隐藏 reasoning 不进入四模块输入或纠错反馈。

保留原 OfficeQA Runtime、工具执行、评分器、持久化请求与工具恢复。P 编号取实际完成顺序，Q 按 task_id 对齐；预算例外仅训练 UID0007 两侧 65536，其他和全部 Test 为 32768。初始 Skill 为原887字符，Train/Test workers=4，24轮/每轮6次。新 I/O 层精确读取 Skill UTF-8 字节，避免 CRLF 在 Python 文本读取时被悄悄改写；实际 system/user 仍由原生 build_messages 生成，原生 Skill.strip 行为保留。

四个方法请求预算均32768，6次共享额度。技术和输出错误分类使用原 OfficeQA 方法 transport；Actor 保留其自身分类。空 patch、null patch、全 WITHDRAW、无翻转均有独立分支，无语义重采样。Selected 只组合 Retain，未执行的新组合 `selected_execution_source=null` 且分数留空。

Memory 使用内容摘要提交、单写者锁和原子 HEAD。当前轮核验原始 journal、state、已提交工具、实际任务输入和配对。OfficeQA 以 release revision、题目 ID 和来源文件名标识数据，运行时免做源文件指纹复核；发布前再次检查当前证据。已发布历史只读取提交链、结构及随轮次发布的 `round_summary.json` / `cost_summary.json`，不回放旧 Actor/Gate；CLI恢复和汇总也不重新打开历史原始轨迹。运行器只冻结本版本实现及 Prompt 身份，不扫描全仓库作为运行门槛。

## 命令

以下仅为使用说明，本次只执行离线验收与只读预检。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam:external/SkillOpt \
  /Users/didi/miniforge3/envs/OfficeQA/bin/python \
  scripts/verification/verify_v26_1_campaign.py \
  --output docs/methods/v26_1/offline_acceptance/20261104
```

不读凭据、不发请求、不创建 Campaign 的预检：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/OfficeQA/bin/python \
  scripts/runs/run_v26_1_campaign.py train /tmp/v26_1_preflight_not_created \
  --config experiments/configs/v26_1_officeqa_train74.json --validate-only
```

后续真实执行接口为 `train <新目录> --config <配置> --actor-key-env <变量名> --method-key-env <变量名>`。恢复同一身份需显式 `--resume`，原额度不重置。训练完成只导出最终 Skill 和训练报告。Test 单独使用 `test <已完成Campaign> --output <独立新目录> --actor-key-env <变量名>`，只能评最终 Selected，不能自动补测或提高预算。没有创建自动化任务。

`--resume --archive-only` 不构造真实传输，仅可复用完整 Actor journal 和已保存方法响应；缺少新执行所需记录时停止，不挪用新的请求额度。Actor 自身保存的第六次响应恢复由原 Runtime 保证，正常显式 resume 不会发出第七次请求。

## 报告与结果解释

每轮保存 Original、动作、Effective、mapped patches、Candidate、全部配对、Replay 事件、Gate、Selected、Memory prepared/receipt、结果及停止原因。训练汇总包含各轮 Parent/Candidate EM/F1、G/L、F1-only、归因/未归因翻转、有效更新和 patch 数量、Selected 分数来源。技术未完成的 Test 有 pending/errors，完整集 EM/F1 为 null；全覆盖后才发布完整指标。

成本按原始 request slots 和 Actor state 计数，包含失败、length、格式纠错及中断未知请求。记录每次发生新请求额度分配的阶段/Actor/训练调用耗时；不同层次时间可能重叠，不可直接相加。token 未知保留 unknown_requests，不记作已知零。未知发包状态只提供物理请求数量上界，不伪装成确认计费数量。合成 fixture 的 requests 是计数对象，不是网络请求。

离线验收验证接线、合同和恢复能力，不验证模型判断质量，也不证明 OfficeQA 提升。后续真实实验仍须独立启动；旧混合预算118/172仅作历史参考。

## 验收证据

当前机器可复现验收结果：见 [summary.json](offline_acceptance/20261104/summary.json)、[pytest.log](offline_acceptance/20261104/pytest.log)、[JUnit](offline_acceptance/20261104/junit.xml)。A01–A42 分别列出实际测试节点和预检证据；原 `acceptance_matrix.json` 的 planned 状态作为设计基线保留，执行状态以本次 summary 为准。

真实 release 的246题来源均只读验证；原始初始消息最大85,101字符/字节。独立容量用例验证约150万汉字、450万UTF-8字节及精确越界拒绝，长 Memory 和 Skill 保持完整。此结果不承诺真实演化后一定满足服务端 context 容量；超限时按合同停止。

旧语料 corrected/corrected_v2 的5个可选检查因本机缺少对应历史构建目录而跳过，不创建或重建旧语料；所选 release 不受影响。阻断的网络负例来自网络保护自检；真实网络请求为0。没有执行 DocVQA 实验或真实 OfficeQA 训练/Test。

保护检查核对原版本源文件字节、20份设计基线副本及3,548个旧 OfficeQA 实验文件的大小/修改时间。实施开始前另保存了3,285个旧源文件摘要，最终核对记录为 [implementation_protection.json](offline_acceptance/20261104/implementation_protection.json)。验收只在临时目录运行合成任务；未复用旧实验缓存。
