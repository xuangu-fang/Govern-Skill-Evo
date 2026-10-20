# P3-C2-A：Commitment-Anchored Update Transformation

状态：先冻结此技术设计，再实现离线原型。无模型调用；人工夹具不是新模型结果或已验证策略。

## 1. 输入、输出和核心流程

输入为原Preconditioner payload（Parent、Original Plan、当前runs/候选、Grouping、真实Memory）以及一次生成的内部锚定方案。冻结Original Plan的canonical JSON SHA-256。未来模型直接输出编辑操作，不先自由生成整段Update再补解释。

流程：历史编辑—响应关联具体行为关系 → 定位Original精确片段 → 选择目标及必要配套/独立探索 → 校验全部原文锚点 → 一次确定性应用 → 汇总为原Adjustment → 原compile_effective_plan。

输出：原正式Preconditioner对象、原编译器生成的Effective Plan或合法停点、逐编辑UTF-8字节映射与保留片段哈希、可读Diff。内部role/依赖/锚点不进入Editor或Memory。最终完整text只能由应用器拼接，不接受另一份自由生成的完整结果覆盖它。

## 2. 承诺定位与变换范围

定位由模型利用真实证据完成，程序不以标点自动划分承诺，也不预设R05正确策略。一个承诺可跨多个不相连片段，用多个编辑表达；没有修改大小上限。配套编辑须说明若不改会出现什么矛盾、不可执行或必要行为损害，并显式指向本次目标/独立编辑。独立探索说明自己的问题动机和可检验预期。reason提供解释，basis引用真实输入证据；引用存在不等于语义支持。

没有锚定的字节保持不变，不等于旧规则正确。旧边界有问题时可独立列为target。有依据的大幅替换、扩大/收窄、删除均合法；全Update锚定替换也可表达，但此时保护范围缩小至零，不能声称获得细粒度保留收益。不得以最小字符差异作为目标。

## 3. 实验内部契约

顶层精确字段：`plan_sha256`, `decision`, `reason`, `edits`, `checks`。

每项edit精确字段：`update_id`, `operation`, `anchor_text`, `replacement_text`, `role`, `basis`, `reason`, `depends_on`。

- operation：replace/delete/insert_before/insert_after。
- role：target（目标关系）、supporting（必要配套）、independent（独立有据的新要求/探索）。
- depends_on：本次edits中0起始整数下标。supporting必须非空、唯一且指向target或independent；其余必须空。可跨Update，无递归依赖/循环/长期状态。多个片段可有共同目标。配套必要性由语义评价判断，程序只校验引用关系。
- anchor_text：非空且非全空白，必须在对应原text中精确唯一。允许多句和换行；重复（含重叠出现）拒绝；不模糊匹配。
- replacement_text：delete必须空字符串；其他非空非全空白，原样应用，不strip/改空格。replace不得与anchor相同，无动作Keep应提交空edits。
- basis：非空唯一字符串引用，合法域沿用原编译器；不因写了M6就认为内容有据。
- reason：非空，说明目标/依赖/独立动机与未验证预期。既有总reason描述决定。无Goal修改字段，无正式commitment ID。
- checks：null原样保留或完整数组，沿用原编译器规则。

Canonical哈希：对完整plan作JSON(sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)，UTF-8后SHA-256。包含Goal、Updates顺序/文本/basis、Checks；对象键顺序无关，数组顺序及字符串字节有关。哈希用于防止旧编辑用于新Plan，不是鉴权签名；调用方必须使用冻结payload，不能只信任模型声称的哈希。

## 4. 同时定位、冲突与应用

全部锚点先在同一原快照中定位为UTF-8半开字节区间；替换/删除修改该区间，插入修改锚前/锚后零宽位置。任何锚区间交叠拒绝（含两个插入共享锚）；插入点与另一锚区间边界/内部冲突也拒绝；相邻非插入区间允许。这是保守冲突策略，不猜测编辑顺序；不支持的情况明确失败。

定位后按原Update顺序、修改位置排序。复制原字节间隙并在指定位置写入replacement。记录每个未改区间的原/新字节范围及SHA-256，逐段核对相等。无换行、空格、标点自动修补；作者应显式包含必要分隔。后项不能匹配前项新文本。

任何锚点/契约/编译失败，整体失败，不发布部分正式结果，不回退自由生成。CLI保留输入引用/哈希、错误类型与原因；原始提案文件不变。

## 5. 正式Adjustment桥接与停点

每个被编辑Original Update汇总为一个`from:[原id]`的一对一replacement，`to:[{id:原id,text:确定性合成文本}]`。正式源码允许一对一复用ID；汇总basis取编辑依据有序并集，reason保留各项用途/依赖解释。正式输出不夹带内部字段。原compiler负责存活Checks/Goal不变/谱系/结构检查；未选Update由原compiler原样保留。

唯一整段delete且锚点等于完整原text映射`to:[]`（撤回）。不把多个局部删除碰巧清空文本当成隐式撤回，明确拒绝。部分撤回需用户提供合法Checks，程序不自动删Checks。

- ready + 空edits + checks:null = Keep；ready须至少一个Update存活。
- need_evidence须edits=[]、checks:null；映射原合法停点，不生成Effective。未知未来收益或缺少Memory不自动是need_evidence。
- no_change不是Keep，须通过整段delete显式撤回所有Updates且checks=[]；由原compiler确认，Effective=null。

暂不支持正式原契约已有的拆分、合并、新ID/新增独立Update；不修改正式契约补齐。未来实验遇到必须拆合而原型不可表达，记录范围阻断，不能伪装为证据不足。多目标跨Update和大范围替换仍可表达。

## 6. 工程增量与边界

旧模型直接返回完整替代text，未改部分靠它重述；新模型提交锚定操作，完整text由程序一次合成，未指定部分字节保持。可证明的增量是编辑作用范围与谱系可审计，非语义正确性。

程序不能保证：目标选对、配套必要、replacement没有偷渡停止条件、局部规则组合无冲突、原文有效、Actor真能执行、策略更好。专门的语义风险夹具必须结构通过并暴露新增文本，而不能伪称程序识别了自然语言错误。后续用承诺级评价与另行授权Replay检验。

## 7. 隔离与验收

全部实现、草案、夹具、日志仅在本实验目录。只读导入原编译器与Editor纯输入函数做兼容测试，不执行模型/环境阶段。离线测试包含真实R05文本、合成Unicode/重复锚点/非法引用、停点、跨Update、较大替换、语义风险。人工结果均标为synthetic，不能加入真实A/B结果。
