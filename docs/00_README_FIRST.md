# Governed Skill Evolution：学生启动包

版本：2026-07-28  
状态：研究起点，不是最终方案

## 先做什么

第一次打开本项目时，请按下面顺序阅读：

1. `01_PROJECT_NARRATIVE.md`：理解我们在研究什么，以及暂时不研究什么。
2. `02_HANDS_ON_TODO.md`：照着命令跑，不要先自行重构框架。
3. `03_PAPERS_AND_CODE_MAP.md`：只读“第一周必读”，其余按需查。
4. `04_EXPERIMENT_LOG.md`：从第一次安装开始持续记录。

前三天的目标不是“做出自进化 Agent”，而是拿到四个可检查的产物：

- 一条真实的 tool-using Agent trajectory；
- 一份人工写出的极简 Skill；
- 一次有 Skill / 无 Skill 的对照；
- 一份能够指出“任务是否完成”和“过程是否合规”的人工标注。

如果前三天没有拿到这四件东西，不要继续堆框架。

## 这个项目目前的一句话

我们研究 Agent 如何把运行轨迹沉淀成可复用的 Skill，同时避免把违规捷径、偶然经验和错误归因一起固化下来。

项目的长期名字暂定为：

> **Governed Self-Evolution for Real-World Agents**

当前三个月的论文切口暂定为：

> **When Success Teaches the Wrong Lesson: Compliance-Aware Skill Evolution from Agent Trajectories**

支付欺诈工作流是未来的应用映射，不是第一周必须搭建的业务系统。第一阶段先使用公开、可运行、带政策和工具调用的 Agent benchmark。

## 这是一组“活文档”

这些文件允许学生和 AI 修改。修改时遵守三条规则：

1. 不静默改写研究目标。对 narrative 的实质修改要在 `04_EXPERIMENT_LOG.md` 的 Decision Log 中记录日期、原因和证据。
2. 不用最新一次成功运行覆盖旧结果。每个实验保存配置、代码 commit、模型名、原始轨迹和结果路径。
3. 区分事实、假设和决定：
   - **Fact**：代码实际行为、实验结果或论文明确陈述；
   - **Hypothesis**：等待实验验证的判断；
   - **Decision**：当前为推进项目做出的选择，未来可以推翻。

## 建议的项目目录

把本启动包放入新 Git 项目的根目录。跑通第三天后，再建立下面的结构：

```text
governed-skill-evolution/
├── docs/
│   ├── 01_PROJECT_NARRATIVE.md
│   ├── 02_HANDS_ON_TODO.md
│   ├── 03_PAPERS_AND_CODE_MAP.md
│   └── 04_EXPERIMENT_LOG.md
├── external/
│   ├── tau2-bench/
│   ├── SkillOpt/
│   └── Trace2Skill/
├── src/
│   ├── trajectory/
│   ├── verifiers/
│   ├── skill_evolution/
│   └── adapters/
├── experiments/
│   ├── configs/
│   ├── manifests/
│   └── reports/
└── tests/
```

第一周不要复制第三方仓库的大量代码到 `src/`。先把仓库放在 `external/`，通过薄 adapter 调用；只有确定需要修改的部分才 fork。

## 安全与复现底线

- API key 只能放在 `.env` 或秘密管理工具里；不得写进 Markdown、代码、日志或 Git。
- `.env` 必须加入 `.gitignore`。
- 不向外部 API 发送滴滴业务数据、内部轨迹、个人信息或未脱敏材料。
- 每次实验记录 `git rev-parse HEAD`，因为这些仓库在快速变化。
- 先限制任务数和并发，再运行完整 benchmark；Skill 优化会产生大量模型调用。
- 任何“自动采用 Skill 更新”的功能，第一阶段一律关闭。候选 Skill 先进入 staging，再人工检查。

## 遇到问题时的处理顺序

1. 运行命令的 `--help`；
2. 查看当前 checkout 的 README、`.env.example` 和 config；
3. 把完整报错、环境版本、执行命令写入实验日志；
4. 让 AI 基于当前仓库代码定位问题；
5. 修复后记录根因，不只记录“已解决”。

不要在依赖尚未跑通时重写一个自己的 Agent loop。我们需要先理解现有 benchmark 如何表达 policy、tool、task、trajectory 和 reward。
