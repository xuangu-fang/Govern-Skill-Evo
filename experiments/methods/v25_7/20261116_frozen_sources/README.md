# 11 月 16 日 v25.7 冻结源码

初始版 v25.7 的准备档和内网训练共用同一份冻结合同。相较于 11 月 18 日运行，三份源码的哈希有变化。原 `method.py` 和 `prompts/diagnosis.md` 的 SHA-256 分别匹配 v25.6 的对应文件。[方法实现](../../../../src/skill_evolution/v25_6/method.py) · [Diagnosis](../../../../src/skill_evolution/v25_6/prompts/diagnosis.md)

[历史 Replay](replay.md)从内网 R01 首次 Replay 请求的 system 消息提取，截点为版本入口附加的固定引用说明。提取字节通过两份冻结合同中的 SHA-256 验证。[原始请求](../../../../artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116/campaign/rounds/R01/replay/attempts/001/messages.json)
