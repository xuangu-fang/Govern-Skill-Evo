# Knowledge Only 单轮冻结对照

状态：`partial`。语义质量：尚未评审。

两组使用相同当前事实、轮前 Knowledge、模型配置及三次总尝试预算；只切换历史视图和配套 Prompt。
Preconditioner 与 Replay 独立运行；Replay 固定使用历史实际修改与轨迹，不使用新 Preconditioner 输出。

| 轮次 | 模块 | v3 消息字符 | KO 消息字符 | 字符下降 | 首次输入 token 下降 |
|---|---|---:|---:|---:|---:|
| R03 | preconditioner | 778,003 | 314,891 | 59.53% | 待 API usage |
| R03 | replay | 961,322 | 495,926 | 48.41% | 待 API usage |
| R04 | preconditioner | 1,039,143 | 305,766 | 70.58% | 待 API usage |
| R04 | replay | 1,154,582 | 418,204 | 63.78% | 待 API usage |
| R05 | preconditioner | 1,194,681 | 196,203 | 83.58% | 待 API usage |
| R05 | replay | 1,283,902 | 281,705 | 78.06% | 待 API usage |
| R06 | preconditioner | 1,385,061 | 174,798 | 87.38% | 待 API usage |
| R06 | replay | 1,539,156 | 324,392 | 78.92% | 待 API usage |

| 组 | 有效单元 | 请求 | 重试 | 输入 token（含失败） | 输出 token（含失败） |
|---|---:|---:|---:|---:|---:|
| memory_v3 | 0/8 | 0 | 0 | 未获得 | 未获得 |
| knowledge_only | 1/8 | 2 | 1 | 285690 | 45930 |

实际 usage 缺失时记为 null；known_* 仅为已知部分，不能当作完整成本。未计算货币价格。
失败尝试与重试均计入成本；另列首次请求输入 token，避免把视图缩减与重试差异混为一项。

结构统计与逐项核查材料在 summary.json、cells.csv 和 review_material/。
D/S/C 数量、引用数量、逐字保留率不等于判断质量。非逐字保留项需要核查，不能自动判为遗漏。
固定轨迹不证明新策略成功率或泛化能力提高。本次每单元一份有效输出，不代表稳定统计结论。
