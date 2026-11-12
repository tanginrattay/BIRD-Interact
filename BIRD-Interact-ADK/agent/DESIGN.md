# Scaffold 设计与研究问题

最近核查：2026-11-12。已同步网页讨论并核对 Part B。M1 为优先研究候选，下一版实现与正式实验方案尚未确定。

## 研究目标与边界

研究如何在交互预算内把用户需求、数据库信息与澄清反馈转化为正确 SQL，并在 P2 追加要求时保留仍有效的约束。主要可改部分是 system agent 的指令、上下文、状态、行动选择和控制流程。Simulator、评分、题集和预算属于评测环境，改变它们需要单独标识，不能当作 scaffold 收益。

## 已实现的三条探索

| 方案 | 机制 | 所在分支 / 状态 |
| --- | --- | --- |
| Prompt 信息获取策略 | 在原指令后追加成本、信息状态、歧义与来源选择规则 | `prompt/exploration-policy`；已做小规模对照 |
| Native Requirement State | 同一模型回复产生 State 文本和原生工具调用，callback 解析、验证、保存 State，下次请求注入 | `state/requirement-tracking`；已做多 Backbone 测试 |
| 2-calls Requirement State | 独立模型调用更新 State，再进行正常决策；更新失败不阻断后续行动 | `state/requirement-tracking-2calls`；已做 DeepSeek 72 题 |

实验成绩和限制统一见 [EXPERIMENTS](EXPERIMENTS.md)，不把已实现误写成已证明有效。

## Native 的具体语义

代码入口（`state/requirement-tracking` 分支）：`system_agent/requirement_state.py`、`system_agent/requirement_tracking.py`、`system_agent/agent.py`。main 与 Prompt 分支不具备 State 模块；2-calls 的同名文件实现不同，下述 Native 语义不套用于其他分支。

State 以任务为作用域，包含 runtime 管理的 revision 与 requirements。条目记录 id、requirement、category、status、value、priority；reason 用于变更审计。status 为 unresolved / candidate / conflict / resolved；resolved 的 priority 必须为 0，其余为 1..3。来源写在 value 中，当前没有独立 source 字段。

模型应记录所有正确性约束，包括明确要求，而不只记录歧义。更新使用 upserts，保留旧条目；结构校验不负责证明证据充分或语义完整。before-model callback 注入当前 State，after-model callback 从同条响应提取更新，runtime 负责 session 持久化。缺失或无效更新记录错误并保留旧值，不额外调用模型、不阻断原生工具和正常回复。

当前机制没有自动把 requirement 映射为 SQL 验证条件，没有强制按 priority 排序行动，也没有提交前的确定性语义验证器。提示模型“检查全部要求”不等于程序已验证覆盖。

### 网页设计与当前代码的差别

- 网页中的 `field` 对应设计概念，当前字段名是 `requirement`，另有稳定 id；更新不允许对已有 id 的 requirement 重命名。
- 网页曾允许动态删除条目；当前 `Update` 只有 upserts，**未实现删除**。不因同步设计而修改 schema；是否需要作废/删除及如何保留历史约束，留作后续设计问题。
- candidate 用 `&`、conflict 用 `|` 保留解释属于当前提示约定；代码强制 conflict 含 `|`，不对候选值或来源建立复杂语法。未实现 realized 状态或 SQL AST 对应表，priority 仍仅供参考。
- revision 已由 runtime 管理；缺失更新不阻断工具。解析可忽略外部装饰并提取完整 JSON，但不修复破损 JSON，重复 key、多个更新和歧义容器会拒绝；“容错”不表示宽松接受非法结构。
- 网页 Version 1/2 是讨论中的命名；文档统一用 2-calls / Native 区分机制，不用编号推断本地实现时间顺序。

## 当前证据支持的问题

1. **生成与行动兼容性：** 同条 State 文本加原生工具调用在不同 Backbone 上遵从不稳定。DeepSeek 的伪调用和 Qwen 的 State-only 终止应分别诊断。
2. **语义质量：** 接受、保存和注入只证明结构或传递成功；需求覆盖、错误解决、冲突处理需要逐轮证据标注。
3. **实际利用：** State 与同条 SQL 相符不能证明先前 State 驱动了该决策。`robot_6` 等题即使没有有效 State 更新也可能改善，不能全归因于持久状态。
4. **成本与混杂：** 2-calls 增加调用成本，同时改变指令和执行流程；现有结果不足以分离 State、额外推理和指令变化的作用。

依据：[五组分析](../trajectory_analysis/docs/five_variants_trajectory_analysis.md)、[Qwen 分析](../results/agent-qwen3.8-flash/simulator-deepseek-v4.1-flash-1017/comparison36_20261112/analysis/REPORT.md)。

## State 效果的四层问题

| 层次 | 要验证什么 | 不足以证明它的现象 |
| --- | --- | --- |
| Reliability | 更新能否稳定生成、解析、持久化并保持行动通道正常 | 偶尔有合法 JSON |
| Quality | 是否覆盖需求、证据充分、冲突和 resolved 判断正确 | 字段通过结构校验 |
| Utilization | 后续决策是否实际使用已注入 State | State 被放进上下文、与同条 SQL 一致 |
| Utility | 在受控比较中是否改善任务表现及成本 | 单题成功、接受率或注入率提高 |

上述层次应分别测量，不用“记录了信息”替代“利用并获益”。

## 优先候选 M1：Requirement Gap-driven Information Source Switching

**状态：优先研究，未实现、未验证。** 依据 [Part B](../trajectory_analysis/docs/gpt_deepseek_transfer_analysis_part_b.md) 与用户网页讨论；当前 Native tracker 不等于 M1。

研究问题：预算受限的多轮 Text-to-SQL 中，显式表示会改变 SQL 的未确定条件，并根据该缺口选择信息源，能否改善交互决策？

最小机制候选：标明缺少的条件、替代解释及 SQL 影响；判断 Schema、Knowledge 或 User 哪一方能提供证据。确切定义未命中或只有引用时，继续查找须说明可能解决哪个缺口，没有新增相关证据则停止该搜索分支。用户选择不能用样本值替代。相关条件可以合问，但回答后逐项检查覆盖，只追问仍影响 SQL 的未答项；拒答、部分回答和冲突不能自动标为 resolved。

主要案例为 `disaster_2`，辅以 `credit_4`、`robot_10`；`robot_8` 和 `virtual_1` 限制“越早问、越多问越好”的泛化。缺定义不代表已有知识不能推导，不能把固定次数阈值当成机制有效的证据。

建议验证分两步，均尚未执行：先在相同可见历史下区分“缺定义／尚未查到／已有证据可推导”，盲评下一动作与提问覆盖；再冻结同期 Baseline，仅加入 M1 做端到端重复对照，不同时更换 State 表达与调用通道。观察无关查找、关键未答项、过度澄清/错误确认、P1/P2 及真实成本；仅减少 get 次数不算成功。

## 后续候选 M2 / M3

| 机制 | 要解决的问题与候选行为 | 证据、验证及边界 |
| --- | --- | --- |
| M2：Requirement-to-SQL Contract Checking | 已确认要求未落实或在 P2 遗失；提交前检查投影、行粒度、过滤、聚合、排序/limit 的来源，标记 follow-up 的新增、替换与保留约束 | `archeology_M_4`、`virtual_1`；对照提醒文本、等信息量契约、可触发行动的检查流程；测约束违背、错误阻断与额外成本。AST 无法独立完成语义判断，错误澄清也可能被忠实执行 |
| M3：Discriminative Failure Diagnosis + Budget Awareness | 失败后列少量可区分假设，每次 execute/ask 对应可改变下一步的证据，避免重复无效改写；使用真实预算判断后续动作 | `solar_10`、`mental_9`；分别消融预算提示、区分性诊断及二者结合，测重复、恢复、提前放弃和 P2 到达。generic rejection 不等于语法错误，不向 Agent 泄露研究者知道的隐藏 P2 信息 |

两者均未实现、未验证，暂不与 M1 一起实现。新机制需要可审计的行动差异；新增“仔细检查”的提醒本身不能直接宣称新的 scaffold 贡献。

## 跨 Backbone 行为迁移

目标是让低成本模型通过 scaffold 学到可复用的决策纪律，不训练或蒸馏 Backbone，不复制 GPT 成功轨迹。区分可外置的信息源选择、覆盖检查，与仍依赖模型的语义理解和复杂 SQL 能力；不能把 GPT 的全部判断当作正确标签。

原网页中“小规模新增模型对照”的想法已有部分本地进展：Qwen3.8-Flash 36 题 Baseline/Native 已完成，GLM 正式实验取消。它们测的是既有 Native，**并非 M1 的迁移验证**。Qwen3.7-Plus、Qwen3.8-Max、GLM/Flash 等其他提名仍只是历史候选，不自动转成待运行清单。下一 Backbone 和是否扩大到 72 题未定；选择需核对成本、Function Calling、思考控制和 ADK/API 兼容性。

固定历史测试与自由 Simulator 交互要分开报告；只对语义等价的问题考虑受任务契约约束的一致回答，不能任意回放另一问题的答案。真实运行保留反馈分布差异，按任务配对并考虑数据库相关性/留出验证。新增检查调用计入成本，并设计等调用或等资源对照；不以隐藏 query、参考 SQL 或 GPT 成功示例作为运行时可见信息。

## 决策与待确认项

- 2026-11-12 同步：明确 inference-time scaffold 与低成本 Backbone 目标；Part B/网页建议先研究 M1，M2/M3 保留候选。已同步设计，未授权实现或实验。
- 当前不实现 realized / SQL AST 对应表；网页“可删除 State”与本地 upsert-only 实现的取舍尚待讨论。
- MERIT/BTP 的具体论文版本、阅读笔记细节与创新性比较待核对原文；M1 的模块边界、决策点样本、指标标注及资源对照需先形成可审阅方案。
