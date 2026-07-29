# 协作与贡献指南

本项目以可复现研究为目标。代码是否复杂并不重要，重要的是每个结论都能追溯到配置、轨迹、版本和实验结果。

## Git 协作

1. 从最新 `main` 创建短生命周期分支：

   ```bash
   git switch main
   git pull --ff-only
   git switch -c student/<short-topic>
   ```

2. 一次提交只完成一个清楚的目的，避免把代码、数据和无关格式化混在一起。
3. 推送分支并创建 PR；PR 说明至少包括：
   - 要回答的问题；
   - 修改内容；
   - 验证命令；
   - 新增 artifact；
   - 已知限制或失败。
4. 未经 review 不直接合并实验框架、verifier 规则或 Skill 更新逻辑。

推荐的 commit 前缀：

- `docs:` 文档与研究记录；
- `feat:` 新能力；
- `fix:` 修复；
- `exp:` 实验配置或报告；
- `test:` 测试；
- `chore:` 工程维护。

## 实验约定

- 实验前先写 Question 和 Hypothesis；
- 配置放在 `experiments/configs/`；
- 数据划分与 ID 放在 `experiments/manifests/`；
- 结论和小型结果表放在 `experiments/reports/`；
- 原始大文件放在被忽略的 `outputs/` 或外部存储；
- 运行后在 `docs/04_EXPERIMENT_LOG.md` 追加记录，不覆盖旧记录；
- 每次记录 `git rev-parse HEAD`、完整模型 ID、temperature、policy version 和重复次数。

## 代码约定

- 第三方仓库放在 `external/`，通过薄 adapter 调用；
- 统一 schema 必须保留原始 payload，避免转换时丢失证据；
- verifier 输出必须包含版本、证据和对应 step；
- deterministic rule 要有单元测试；
- 产生 Skill patch 时必须保存 parent、diff、source trajectories 和 decision；
- 候选 Skill 默认进入 staging，不自动覆盖 accepted 版本。

## 提交前检查

至少完成：

```bash
git status --short
git diff --check
```

有代码后，还应运行与修改相关的测试和最小 smoke test。不要为了得到绿色结果删除失败案例。

## 禁止提交

- `.env`、API key、token 或凭据；
- 内部业务数据、个人信息和未脱敏轨迹；
- 第三方仓库副本；
- 大体积原始输出；
- 无法说明来源的数据与生成结果；
- 只挑选最好一次运行得到的结果。
