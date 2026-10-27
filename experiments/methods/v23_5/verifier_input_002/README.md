# Verifier 输入 v2：动作候选列表共享引用

2026-10-27 材料整理入口：[候选、结果与归档导航](evidence/README.md)。以下保留原阶段说明；本次没有重跑实验或测试。

已完成 R01–R03 的无损去重。只改变列表的存储与寻址，不改 Knowledge、Evidence ID、任务身份、观察、动作、反馈、执行背景或原始 `commands_ref`。没有调用模型、重跑核验实验或修改正式 Memory。

## 新结构

顶层增加共享 `command_sets`。每份 source record 的内嵌列表改为局部 `command_set_refs`，保留原始局部 ID：

```json
{
  "source_records": {
    "Q6:9": {
      "record": {
        "before": {"commands_ref": "C43"},
        "after": {"commands_ref": null}
      },
      "command_set_refs": {"C43": "CS8"}
    }
  },
  "command_sets": {"CS8": ["look", "inventory"]}
}
```

上例仅说明寻址，不是真实 Q6:9 内容；其他字段省略。解析顺序：当前 record 的 `commands_ref` → 当前 source 的 `command_set_refs` → 顶层 `command_sets`。新版 Prompt 仅调整输入格式和寻址说明，核验要求及输出 Schema 不变。

- 按完整有序字符串列表去重，不排序、不去掉列表内部重复项、不摘要或筛选动作。
- 同名 C43 在不同来源中可指向不同共享列表；不同局部 ID 的完全相同列表可共享。历史 Evidence 前缀和执行身份保持原样。
- 共享 ID 只在当前输入内有效，不能用作 Knowledge/issue 的 Evidence ID。
- null 仍为 null，空列表仍为空列表，不能互相替换。
- 还原时恢复原局部字典及全部原始记录；各列表独立复制，避免修改一个还原记录影响另一个记录。

## 校验与结果

对新输入展开全部引用，再与冻结旧输入做完整 JSON 值比较：包括字段、字符串、数组顺序、重复项、null、布尔值和数值类型。JSON 排版和对象键排列不要求逐字节相同；旧输入文件另按原字节复制并校验 SHA-256。

另外检查 Evidence 与 source 集合一致、每个非空 `commands_ref` 恰有对应局部映射、全部映射都可解析、没有闲置或重复的共享列表。即使引用存在但错误地指向另一份合法列表，还原对照也会拒绝。新输入、消息、Prompt、代码及源文件均记录哈希，旧输入包和原始档案复核不变。

| 轮次 | 原列表出现次数 | 共享列表数 | 原数据字符数 | 新数据字符数 | 减少 |
|---|---:|---:|---:|---:|---:|
| R01 | 72 | 44 | 72,566 | 64,207 | 11.52% |
| R02 | 174 | 91 | 198,192 | 149,504 | 24.57% |
| R03 | 186 | 79 | 251,407 | 168,950 | 32.80% |

字符数按紧凑 JSON 统计，不是 API Token，也不代表准确率或完成率改善。完整 messages 的字符/字节数另见 [统计](results/summary.json)。

19 项离线测试通过，覆盖三轮真实输入、历史同名 ID、相同内容别名、完整执行/初始状态/结果记录、顺序/重复/null/空列表、引用遗漏或错指、JSON 类型差异、冻结文件篡改和原输出引用权限兼容。读取旧响应只是确定性格式校验，不是重新运行或比较模型效果。

## 文件与命令

- [转换、还原和校验代码](prepare.py)
- [新版 Prompt](verifier_prompt.md)
- [离线测试](test_prepare.py)
- [R01 新输入](../../../../artifacts/methods/v23_5/verifier_input_002/cases/R01/verifier_input.json)
- [R02 新输入](../../../../artifacts/methods/v23_5/verifier_input_002/cases/R02/verifier_input.json)
- [R03 新输入](../../../../artifacts/methods/v23_5/verifier_input_002/cases/R03/verifier_input.json)
- [校验结果](results/validation.json)

各轮还保存 `original_input.json` 和适配新格式的 `messages.json`。旧 v1 包及此前真实核验结果不覆盖；正式主流程和旧运行器不自动切换到 v2。

在仓库根目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_002/prepare.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_002/prepare.py restore --round R01 --restored-output /tmp/verifier-R01-restored.json
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python -m pytest -q experiments/methods/v23_5/verifier_input_002/test_prepare.py
```

`prepare --output <新目录>` 可重建独立包，已有目录拒绝覆盖；restore 也拒绝覆盖目标文件。所有入口均无模型调用。
