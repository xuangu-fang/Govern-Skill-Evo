# DeepSeek 输出格式适配

2026-10-30：按用户要求参照 v23.5 action_only_v1，固定 Prompt 用文字描述名为 answer 的
XML 元素，不展示完整 answer/think 标签，不要求正文逐步解释。Actor 和五个方法模块同步，
Prompt 版本 v4。此处保存当前可执行方法 Prompt 的逐字副本；draft_20261030_001 保留历史。

v27 与本地 SkillAdam 共用 protocol.build_messages；后者仅适配原生请求的 system 和
prompt_profile，其余题目、选项、答案映射、解析和优化器流程保持原生。上游代码未改。
后续生成内容与原始轨迹不清洗，因此不保证所有动态输入均无标签，也不宣称根治服务端问题。

验证报告：artifacts/verification/v27_prompt_words_20261030、
artifacts/verification/lmb_prompt_words_skilladam_20261030。未请求真实模型。

本次文字澄清：Skill 的 single-label 要求适用于 answer 元素内部文本。没有加入具体标签示例，初始 Skill 和评分规则不变；Actor profile 更新为 lmb_answer_element_words_v2。
