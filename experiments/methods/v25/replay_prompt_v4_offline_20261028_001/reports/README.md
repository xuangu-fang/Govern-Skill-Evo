# Replay v4 默认安装与离线校验

2026-10-28。按用户确认，将 v3 加局部修改的生产稿安装为默认 `v25_replay_decision_fidelity_v4`。输入视图保持 v4、Preconditioner 保持 v7。本次模型调用数为 **0**；未发布 Memory、未跑完整链路或训练。

## 安装内容

- 运行正文与文档镜像均逐字采用 [production_candidate.md](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/production_candidate.md)，只输出 `entries`。
- 原 v3 正文逐字归档为 `replay_legacy_v3.md`；v1/v2 归档不变，按原 Prompt 版本读取。
- 注册 v4 默认并更新供后续运行使用的 batch15 配置；旧 campaign 配置、输入、响应及实验报告不回写。
- 采用理由与实验限制见 [Replay v4 说明](../../../../../docs/methods/v25/REPLAY_DECISION_FIDELITY.md)。此前诊断初筛的失败结论保留，本次没有重新判定为成功。

## 校验结果

| 检查 | 结果 |
|---|---|
| Prompt 版本选择、旧布局、共享输入、代码去重、默认配置及离线管线测试 | **93 passed**，19.63 秒 |
| 旧原生归档读取 | **18 份通过**，涵盖 v1/v2/v3 Prompt 和 v1–v4 输入视图；包含实际模型响应及既有离线 fixture |
| 旧请求精确重建 | 18 份均与保存的 messages 一致；切换新 Prompt 只改变学习正文，user 与 system 其余部分不变 |
| 新版归档保存/读取 | R05、R06 两份通过，复用已有 v3 响应，没有生成新响应 |
| 正文、镜像、归档 | 生产稿与审阅稿逐字一致；v3 原字节保留；所有 Prompt 镜像一致 |
| 冻结文件保护 | 校验修改前快照的 6,337 个文件，除预期的源码和当前文档修改外保持一致；旧实验记录不变 |
| 配置 | 后续 batch15 配置通过校验；Replay v4、输入视图 v4、Preconditioner v7 |

保存响应 fixture 的 `response.json` 带有 `offline_reused_from` 来源标记。它们验证新版工程契约可以保存与读取合法响应，**不是 v4 的模型实验，不能用于判断学习质量**。离线归档脚本拦截网络请求和生产 generator；pytest 使用离线替身。

环境记录：首次使用 spreadsheetbench Python 启动 pytest 时因该环境未安装 pytest 而退出；随后使用已有 `/tmp/govern-skill-v25-venv` 完成测试，没有安装依赖。

## 复核

- [测试日志](../../../../../artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/pytest.log)、[JUnit 结果](../../../../../artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/pytest.xml)。
- [归档校验明细](../../../../../artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/archive_validation.json)、[校验脚本](../../../../../artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/validate_archives.py)。
- [修改前文件哈希](../../../../../artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/before_manifest.json)及 `before/` 中的本次编辑前副本。
- `saved_output_fixtures/R05`、`saved_output_fixtures/R06`：复用旧响应的 v4 原生归档。

```sh
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/replay_prompt_v4_offline_20261028_001/validate_archives.py

/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_replay_versions.py \
  tests/skill_evolution/v25/test_replay_input_views.py \
  tests/skill_evolution/v25/test_replay_shared_initial.py \
  tests/skill_evolution/v25/test_replay_exact_code.py \
  tests/skill_evolution/v25/test_task_requirement_versions.py \
  tests/skill_evolution/v25/test_configuration.py \
  tests/skill_evolution/v25/test_pipeline.py
```

旧归档可读与旧 campaign 可继续运行是不同契约：旧 campaign 的 method freeze 继续生效，不能静默切换到 v4 后恢复训练。
