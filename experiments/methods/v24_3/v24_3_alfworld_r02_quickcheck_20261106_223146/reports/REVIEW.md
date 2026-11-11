# R02 单次快检：修订后的 Preconditioner

同一份冻结输入和请求参数，单次真实模型调用，u1 返回 REPLACE，首次通过合同。输出包含 target、action、text、reason；编译器继承 Original 的依据。本次只运行 Preconditioner。

- P4:21：打开 cabinet 6 后观察到柜内为空。菜单提供 inventory、go to cabinet 7 等，实际选了 inventory。新文本在这个具体决策上明确提高了导航相对 inventory 的优先级。
- P6:32：打开空的 cabinet 9，实际返回 cabinet 8。最近两步分别去往、打开 cabinet 9，菜单同时提供 go to cabinet 8 和 go to drawer 1。两者都是不同于当前位置的合法去处。Actor 凭短历史无法判定 cabinet 8 先前已被搜索。新版能够处理近两步可见的折返，但无法据此排除更长周期的循环。最后一句限制回访时，若旧状态或过去访问不可见，仍可能难以判断。
- 此次回复已去掉“所有容器都检查过才能回访”的全局前提；据此可以进入正式训练验证，实际动作和成功率尚待测量。

[有效 Plan 和原始调整](../../../../../artifacts/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/preconditioner/result.json) · [冻结输入](../../../../../artifacts/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/preconditioner/input.json) · [来源和冻结记录](../../../../../artifacts/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/provenance.json)
