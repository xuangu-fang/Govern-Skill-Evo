# OfficeQA v26.3 实现与离线验证

[训练与测试入口](../../../scripts/runs/run_v26_3_campaign.py) 使用[可执行配置](../../../experiments/configs/v26_3_officeqa_train74.json)。与 v26.2 正式 Campaign 的配置逐字段比较，差异为 `method.version` 和 `method.prompts.preconditioner`。Actor 和四个方法模块使用正式归档中的 `deepseek-v4.1-flash`、内网代理和生成参数。训练与独立 Test 分别通过 `train` 和 `test` 进入。[设计稿](README.md) · [v26.2 正式配置](../../../experiments/campaigns/v26_2_officeqa_train74_20261117_013308/config.json)

[Preconditioner](prompts/preconditioner.md) 使用定稿英文全文，加载时核验其 SHA-256。Diagnosis、Editor 和 Replay 的提示词取自 v26.2 正式请求，其模型和端点描述与实际执行一致。运行身份使用 `v26_3_campaign_v1`。同一 Update 的 Original、调整理由、有效文本、Editor patch 和 Gate 决定保存在各轮相应阶段的归档中。[方法绑定](../../../src/skill_evolution/v26_3/protocol.py)

## 离线验证

2026-11-17，三个版本合并运行的结果为 **127 项测试、278 个子测试全部通过**，其中 v26.3 专项 4 项。正式数据只执行了只读预检，未创建 v26.3 实验目录。

在仓库根目录、OfficeQA Python 环境中执行下列命令即可复核。第一条仅验证配置并准备真实 release 的输入，目标目录保持不存在。第二条使用网络阻断夹具和临时目录中的合成轨迹。

```sh
python -B scripts/runs/run_v26_3_campaign.py train /tmp/v26_3_offline_release_check \
  --config experiments/configs/v26_3_officeqa_train74.json --validate-only
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam:external/SkillOpt \
  python -m pytest -q -p no:cacheprovider \
  tests/skill_evolution/v26_1 tests/skill_evolution/v26_2 tests/skill_evolution/v26_3
```

| 验证对象 | 核对内容 |
|---|---|
| 正式输入 | 74 个优化 ID，七批 11/11/11/11/10/10/10；172 个独立 Test ID。只读预检返回模型请求数 0。 |
| 提示词与交接 | 对四个模块模拟调用实际收到的 system message 计算摘要。合成的 REPLACE 保留 ID，将完整有效文本交给 Editor，并在 Selected Skill 和测试输入中核对。 |
| 训练与恢复 | 模拟执行 7 轮、148 次逐题作答及 28 次方法调用。Memory 提交后中断，恢复该轮时核对调用次数。单独验证 v26.2 断点会在模型调用前被拒绝。 |
| 预算与独立 Test | 训练 UID0007 两侧都使用 65,536 tokens；全部测试题使用 32,768。模拟 Test 中断时核对完成数、答对数和 pending ID，完整集 EM/F1 留空；恢复后覆盖 172 题，核对最终 Skill 字节和训练 Memory。 |
| 历史比较 | `compare <本次测试目录> --baseline <历史测试目录>` 只读配对相同 release、评分口径下，两侧都完成且单题预算相同的记录。用 v26.2 两次已有测试复核得到共同 171 题、120→118、6 题改善和 8 题退化。 |

专项用例和模拟响应见[v26.3 离线测试](../../../tests/skill_evolution/v26_3/test_campaign.py)。模拟数据验证执行、归档和报告行为；v26.3 在 OfficeQA 正式测试集上的 EM 和 F1 有待实际实验测量。
