# OfficeQA v26.2 实现与离线验收

2026-11-17。v26.2 使用独立的[训练与评测入口](../../../scripts/runs/run_v26_2_campaign.py)和[可执行配置](../../../experiments/configs/v26_2_officeqa_train74.json)。入口保留 v26.1 的 train、test、只读预检和显式恢复语义。实际模型调用继续要求显式提供凭据变量名。

## 与正式基线的差异

逐字段比较 v26.2 可执行配置与 [v26.1 正式训练归档](../../../experiments/campaigns/v26_1_officeqa_train74_roles_20261105_202041/config.json)，差异限于三处。

| 字段 | v26.2 |
|---|---|
| `batches` | 原 74 个题目 ID 同序切为 11 / 11 / 11 / 11 / 10 / 10 / 10。 |
| `method.prompts.preconditioner` | 阶段请求使用独立提示词标识，并加载[定稿全文](prompts/preconditioner.md)。 |
| `method.version` | 独立运行标识 `v26_2_campaign_v1` 用于区分配置、报告和断点。 |

v26.1 正式归档中记录的 26 份源码与提示词指纹均核对一致。此次验收使用的 v26.2 Preconditioner 文件 SHA-256 为 `5462d49f9d739b853fb6b6af71335e32955589f8a391f867bd24b6f3cff2a206`。

## 验收覆盖

合并运行 v26.1 回归与 [v26.2 验收用例](../../../tests/skill_evolution/v26_2/test_campaign.py)，共 123 项测试和 278 个子测试通过。其中 v26.2 专项 8 项。

- **真实 release 只读预检**　准备 74 道优化题和 172 道测试题的初始输入，核对七批顺序、R05 来源交界、模型配置和提示词。CLI 返回 `model_requests=0`，未创建 Campaign。
- **合成训练与评测**　在临时目录使用进程内模拟响应走完七轮，正常路径共 148 次合成 Actor 调用和 28 次合成方法调用。逐次检查四模块收到的 system message，核对 UID0007 两侧预算及 R07 终态。独立的 172 题合成评测覆盖中断、完整指标留空、恢复和最终 Skill 字节一致性。
- **提案与输入边界**　检查 11 条引用执行、无效动作反馈、全文 REPLACE 到 Editor 的交接、全 WITHDRAW、空 patch、合法 null 和未归因翻转。对实际 11 题 Preconditioner 消息加入长合成 Memory，验证无损投影及 400 万字符、600 万 UTF-8 字节的超限拒绝。
- **恢复与隔离**　合成训练在 Memory 提交后中断，恢复该轮无需新增调用。旧版本断点在新请求前被拒绝。验收时阻断网络，真实训练及真实 Test 均未启动。

### 复现

在仓库根目录使用 OfficeQA Python 环境，可运行以下两条离线命令。第一条执行合成验收与 v26.1 回归，第二条只读检查实际 release。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam:external/SkillOpt python -m pytest -q -p no:cacheprovider tests/skill_evolution/v26_1 tests/skill_evolution/v26_2
python scripts/runs/run_v26_2_campaign.py train /tmp/officeqa_v26_2_readonly_preflight --config experiments/configs/v26_2_officeqa_train74.json --validate-only
```
