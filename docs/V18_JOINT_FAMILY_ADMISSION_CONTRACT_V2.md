# v18 Joint Family Admission Contract v2

状态：`FROZEN BEFORE REPLICATION`  
版本：`v18-joint-family-admission-2`  
日期：2026-09-20

v1 的历史结果保持不变。v4 在 v1 下仍为 `HOLD_GATE_1`，同时其机制设计结论记录为 `JOINT_MECHANISM_VALIDATED`：它实现了双维 headroom、组件主维修复、残余另一维缺口和 6/6 Joint CS。

v2 不再要求加入局部 Skill 后另一维 outcome 几乎不变。LLM 会依据完整 prompt 重规划整条轨迹，因此跨轴改善或退化必须报告，但不单独否决。准入改为检验：

1. E0 在两维均有可重复 headroom；
2. E_CAP 修复 Success，同时保留 Governance violations；
3. E_GOV 修复 Compliance，同时保留 Capability failures；
4. E_JOINT 相比两个单组件分别提供可观测的增量修复；
5. 两段 Skill 在文本语义上互不包含另一维规则；
6. Train 与 Monitor 使用 fresh entities、surface forms 和 seeds，并分别通过全部门槛。

机器可验收契约见同名配置目录中的 `admission_contract.json`，冻结摘要见 `manifest.json`。
