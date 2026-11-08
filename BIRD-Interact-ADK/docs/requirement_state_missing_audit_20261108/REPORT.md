# 8-task 重跑：7 次 State 缺失的只读分析

本报告完成下一阶段的第一步；没有启动 72-task 实验，没有修改生产源码、Prompt 或工具行为。只新增本报告与证据摘录，不改变原运行目录。原目录 manifest 的全部文件哈希验证通过，当前生产源码也与该次运行快照一致。

归档备注：按用户后续要求，本报告对应的两个 8-task smoke 原运行目录已移入回收站，因此下方旧原运行链接不再可用。本报告与 evidence.json 的完整证据摘录保留；未重写其中的历史路径。

## 结论

这 7 次是回调入口处确实没有 State JSON，不是外层标记解析失败：4 次回复只有一个 FunctionCall Part；3 次包含一个普通叙述 Text Part 加一个 FunctionCall Part。全部保留旧 State，7 个工具都执行并获得正常 FunctionResponse。

不能将它们全部判为无害 no-op，也不能全部判为任务失败：

- 5 次没有发现当轮新增、与现有 State 矛盾且必须改写的任务约束。结合相邻证据，可以视为语义上允许不改变 State 的轮次，但模型并没有显式输出 `upserts: []`，不能把缺失伪装成已接受更新。
- `robot_1` 第 11 次回复附近存在歧义重开晚记一轮的问题。怀疑已在第 10 次的普通文本出现，当次 State 却是合法空补丁；第 11 次只有 FunctionCall；第 12 次才写入 conflict。因此是局部语义状态滞后，不能只归因于第 11 次缺失。
- `credit_3` 第 8 次回复之前已得到最终计数 **95**，但 State 的对应 Value 只保留计数要求/规则，没有保存这个答案。提交成功后原框架立即停止，未再调用模型，所以终态没有补记。按 Value 保存当前答案的目标，这是实质性的终态答案遗漏；不是计数要求遗漏，也不是任务失败。

没有发现这 7 次造成任务要求被删除、用户澄清丢失、State 被破坏、跨任务污染或工具被阻止。它们尚不足以判定当前 Native State Runtime 不适合进入 72-task 实验；但足以否定“State 始终完整、实时反映所有已知信息”的强结论。建议保持当前版本冻结，把后续实验作为同时评估任务效果与 State 语义质量的实验，明确计入滞后和终态答案遗漏，不为提高接受率改 Prompt。

## 证据边界与索引

- 原运行：[README](../../results/agent-deepseek-deepseek-flash/simulator-deepseek-deepseek-flash/requirement_native_smoke8_rerun_20261108T092023Z/README.md)。
- [evidence.json](evidence.json) 的 `cases` 共 7 项，按下表顺序排列。每项保存完整原始 Parts（包括 SQL、ID、参数）、前一轮决策及工具结果、当轮工具结果、State before/after、下一次合法回复、最终 State。不是仅保存工具名称或摘要。
- 序号 Rn 指该 Task 的第 n 次正常模型回复，不是第 n 次用户交互，也不是 phase 编号。
- “原始模型响应”准确指 `after_model_callback` 入口处的 **ADK LlmResponse.content**，与 Session Event content 完全相等。本次没有保存 provider HTTP 原始响应，不能进一步证明 DeepSeek 原始 HTTP payload 与 LiteLLM/ADK 转换前是否完全相同。
- “忘记输出”只是外部行为描述。没有文本 Part 不等于模型内部认为无需更新，普通叙述也不能证明其有意省略 State；内部动机不可观察。
- 本报告不读取隐藏正确 SQL 来推断需求，只使用 Agent 当时可见的用户输入、工具结果和已记录 State；不对全部 8 题做完整语义评分。

## 七次逐项分析

| Task / 回复 | Phase | ADK Parts | 前序信息 | 当轮行动 | State 内容影响 |
| --- | --- | --- | --- | --- | --- |
| cross_db_3 / R11 | 1 | Text + FunctionCall | R10 的 SQL 返回 10 行；用户约定已在 R10 入 State | submit_sql | 未见新约束遗漏；可接受 no-op，但缺失不能算有效空更新 |
| robot_1 / R6 | 1 | Text + FunctionCall | R5 SQL 返回 6 行；用户阈值、LIMIT、排序已入 State | submit_sql | 未见新增约束；SQL 可运行不证明其语义正确 |
| robot_1 / R9 | 1 | FunctionCall | 前一多语句查询只显示最后语句的空结果 | execute_sql | 重查总数，不应从前一个空结果擅自推断 cardinality |
| robot_1 / R11 | 1 | FunctionCall | 前一结果给出 safety_state 分布，前一文本已怀疑筛选定义 | execute_sql | 对筛选歧义的 State 重开迟至 R12；一轮滞后 |
| credit_3 / R5 | 1 | FunctionCall | 枚举查询确认存在用户指定的投资类别组合 | execute_sql | 用户规则已入 State；字段映射没单独入 State 是更早的 coverage 问题 |
| credit_3 / R6 | 1 | Text + FunctionCall | R5 返回满足筛选的客户列表 | submit_sql | 无新任务约束；P1 成功后 R7 正常记录新追问 |
| credit_3 / R8 | 2 | FunctionCall | R7 的计数结果为 95 | submit_sql | 计数要求已记录，最终答案 95 未入 Value，且无后续补记 |

### 1. cross_db_3 / R11：省略空更新，没有发现新任务要求丢失

原始 Text 为 `The query works. Let me submit.`，另一个 Part 是原生 submit_sql。完整 SQL 与上一轮 execute_sql 相同。之前的用户回答明确了 DTE=SuccessPct、top 10、BSI 降序；R10 已更新 r4、r1、r6，当前 revision=9。

R10 的执行结果为 flow_id/bsi/dte 三列、10 行，没有提供新的定义或阈值，也未报错。当轮没有必须新增的任务要求，保持旧 State 合理；不应因为“返回了结果”把尚未确认的映射或整个 SQL 自动标记正确。

当轮提交 P1 失败。这个反馈发生在 R11 之后，不是 R11 本应已知而漏写的信息。R12 正常新增 r9（Flow ID column，flowtag vs recordregistry，candidate），说明后续重新探索没有被 State 缺失阻断。r9 具体解析是否充分属于另一个语义评估问题。

### 2. robot_1 / R6：测试成功到提交之间省略 State

原始 Text 为 `The query works and returns results. Let me submit.`，另一个 Part 是原生 submit_sql，SQL 与 R5 execute_sql 相同。R5 返回 6 行 robot/sis/faultpredscore，State revision=5 已记录 RFPS>0.5、LIMIT 100、SIS 降序等规则。

该执行结果不引入新的需求，也不证明整条 SQL 逻辑正确；从这次缺失本身，没有发现必须写入而被永久遗漏的新约束。提交 P1 失败后，R7 正常新增 latest maintenance record selection 的 candidate，后续流程继续。

注意：R5 的 r1 Value 把 SIS>20 与 RFPS>0.5 一并注明 source:user，但实际 ask_user 回答只明确 RFPS 阈值、数量和排序，未确认 SIS>20。这个证据归属/过早 resolved 的风险在缺失之前已存在，不能归咎于 R6，也不能因补丁结构有效而忽略。

### 3. robot_1 / R9：只有 FunctionCall，重查被多语句结果遮蔽的信息

原始回复只有 execute_sql Part，无 Text、无 State。前一轮 R8 同一个 SQL 字符串包含两条查询：总行数/robot 数，以及每 robot 多行的样例。FunctionResponse 只显示最后语句的 `Query executed, empty result set.`，没有返回第一条计数。

R9 单独重查总数，得到 total=1000、robots=1000。R9 决策前，并没有这个计数结果，因此不能说 R9 漏写了“1000/1000”。原生历史保留了这个新结果；R10 普通文本明确说 One row per robot，说明后续模型实际读取了它。

但是 R10 是合法空补丁，没有把这个 cardinality 事实单独写入 State。因此“该事实未进 State”真实存在，却不能只归因于 R9 缺失。当前 State 没有承诺保存每个探查结果；此事实是已有 SIS 聚合规则的佐证，不必机械新增每一项数据观测。如果未来希望 State 单独支持回忆所有探查证据，需要另行定义范围，不能在本轮悄悄扩大职责。

### 4. robot_1 / R11：语义歧义重开存在一轮滞后

原始回复只有 execute_sql Part，查询 issuelevelval 的分布。R10 已在普通文本中提出 high safety issue 可能指 maintenance.issuelevelval='High'，也可能指 safety_state，但该轮 State 是 `upserts: []`，r1 仍是 resolved。

R10 的多语句查询只返回 safety_state 分布（Warning 348、Normal 317、Emergency 335），没有返回 issuelevelval；R11 单独补查，才得到 Low/None/Critical/High/Medium 分布。

因此 R11 决策时已经存在应显式表达的不确定性：原来 resolved 的解释正在被模型重新质疑。更保守的 State 应反映这个重新怀疑（如 candidate；是否已经构成 conflict 要看真实证据，不能仅因新猜测就强行称为实际矛盾）。R12 将 r1 写为 conflict，保存 SIS>20 与 issuelevelval='High' 两种解释，priority 恢复为 1。

观察结论是歧义最终记入，但存在滞后。不能说 State 全程实时；也不能把 R12 的 conflict 字段合法当作“确有相互矛盾证据”的证明。这里有待核实的替代解释，尚不足以证明用户或 KB 的两个答案真正冲突。

### 5. credit_3 / R5：只有 FunctionCall，用户规则此前已完整记录

R4 之前的用户回答明确 Moderate/Aggressive、Extensive、投资额超过资产 30%；R4 已把这些规则写入 r1 resolved/0。R4 的 DISTINCT 查询返回类别组合，包括 Moderate/Extensive 与 Aggressive/Extensive。

R5 只返回查询客户 ID、investamt、totassets 的 execute_sql Part，没有 Text。前序结果佐证了字段值可用，没有改变用户条件，因此没有发现本轮必须改写的既有需求答案。

State 没有单独记录完整字段映射、四表连接规则，确实属于 coverage 不充分的候选问题；但它们从更早的 schema 探索就未入 State，不能认定由 R5 缺失新增。r1 及用户条件没有丢失，SQL 也使用了这些条件。

### 6. credit_3 / R6：省略空更新，不影响第二阶段需求新增

原始 Text 为 `The query works. Submitting.`，另一个 Part 为 submit_sql，与 R5 查询 SQL 相同。前序工具返回客户列表，没有新的业务规则。revision 仍为 4。

提交结果 P1 通过，并返回第二阶段追问 How many such customers are there in total?。这条新要求在提交以后才产生，不能算 R6 漏写。R7 正常新增 r3：Count total number of such customers，Value=COUNT of customers matching r1 criteria (source:follow-up)，resolved/0；随后执行 COUNT 查询。

因此即便 R5/R6 连续两轮缺失，关键用户规则保持，新阶段要求也成功进入 State。任务成功不是据以忽略缺失的理由，但这里有直接证据证明阶段切换的信息没有漏掉。

### 7. credit_3 / R8：最终答案 95 没有保存到 State

原始回复只有 submit_sql Part，没有 Text。上一轮 R7 的 FunctionResponse 明确返回 total=95；R8 已能读取这个结果。此时 r3 的 Value 仍只有 COUNT 的计算规则。

R8 本可用同一次响应更新 r3 Value，保留计数规则并写入 95 及执行结果来源；实际上没有提供更新。提交成功后 after-tool 设置 phase2_completed/task_done，下一次 before-model 直接返回 Task completed.，没有再次调用 LLM。最终 Session 的 r3 Value 仍没有 95，evidence.json 保存了最终状态以供核对。

这属于终态答案未写入 State，且不会在本次 Session 自动恢复。原生 FunctionResponse 仍有 95，完整 Session 没有丢失答案；只读 State 的下游使用者却得不到数值。当前 Agent 还可读原生历史，且任务已完成，所以本例未造成后续决策失败。

## 对进入 72-task 的判断

未发现必须先改生产代码才能继续的 Runtime 严重故障。当前版本可以作为冻结实验条件进入完整任务集，但应带着已知语义局限运行，而不是宣称 8-task 已证明语义可靠。

7 次缺失里没有直接跟在 ask_user/Knowledge 新定义之后就漏掉关键澄清的案例；已有用户澄清和 Phase 2 新要求均保留。这只是本样本的结论，不能外推所有任务。非阻断策略允许模型在缺失期间继续行动，所以更大样本仍可能出现重要新要求未记入、旧答案过时等风险，应继续保留每轮证据。

后续质量统计建议把以下维度分开，且在统计前固定分母：

1. 协议：有正常模型回复的轮次中，合法更新、缺失更新、非法更新分别占比；真实 no-op 只能在内容审查后另行标注。
2. Coverage：对用户原问题、澄清和追问拆出的独立可检查约束，逐项判断是否入 State；不能用 Requirement 条目数直接代替召回率。
3. False Resolution：对 resolved 的断言及转换，检查当时可见证据是否充分、是否真实矛盾；不能由最终 SQL 分数反推。
4. 更新及时性：新证据/新要求何时可见、何时首次写入，是否延迟、是否直到结束仍遗漏。
5. 终态答案完整性：明确区分计算规则已记录与执行答案已记录；特别留意成功提交后没有下一次模型回合的情况。

本报告没有据这 7 个选中样本给出完整 Coverage/False Resolution 百分比，也没有改 Prompt、插入修复调用、把缺失当空更新或新增结束时整理模型调用。
