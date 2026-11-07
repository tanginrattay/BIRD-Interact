# BIRD-INTERACT 72 条轨迹：第一轮结构化分析

## 覆盖范围与阅读入口

本轮完整读取指定目录中的 **72 份任务 Markdown**，成功处理 **72/72 个唯一 task_id**，覆盖18个数据库；无无法读取文件、遗漏或重复。全部卡片保留七节结构，使用简短事件摘要，未复制原始 Schema、完整知识定义或查询结果。原始文件未修改。分析没有修改 Agent、Prompt、工具或 Callback，没有调用数据库、模型、网络或运行新 Benchmark。

- [72条任务特征表](task_features.csv)：每个任务一行，表头之外72行。
- [逐任务卡片目录](task_cards/)：下方提供逐个任务的可点击索引。
- [证据索引](evidence_index.json)：每次问答摘要及候选类型、重复调用对、SQL错误/改写、阶段、裁剪位置及预算账面差异；适合统计和复核，不含完整SQL/Schema。
- [处理进度](progress.json)：72条均为COMPLETE，并记录源文件哈希。
- [验证报告](validation.json)：文件数量、72份Markdown的全部叶子字段与JSON一致性、原文件前后SHA-256及汇总校验。
- [生成脚本](generate_analysis.py) 与 [逐任务观察标注](annotations.py)：可复核并离线重新生成卡片、CSV、证据与验证文件；不运行评测。命令：`python3 trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/generate_analysis.py`。

源目录：`results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/markdown/tasks/`。逐份读取Markdown后，逐个叶子代码块与同批`eval_a_interact.json`及`tasks.jsonl`做完整有序比对，72份全部一致，才使用JSON计算字段；不是用旧记录或文件名推测数据。`tasks.jsonl`是任务定义，评测结果来自`eval_a_interact.json`。隐藏任务定义只用于研究者识别歧义项，未作为Agent曾经知道的证据；没有重新判定SQL语义或运行参考SQL。

## 指定任务的完整可读时间线

新增5条按ADK事件顺序展开的轨迹：[polar_M_4](trajectory/polar_M_4.md)、[credit_11](trajectory/credit_11.md)、[disaster_3](trajectory/disaster_3.md)、[virtual_1](trajectory/virtual_1.md)、[cybermarket_1](trajectory/cybermarket_1.md)。从Agent实际收到的问题开始，逐次保留公开说明、每次工具调用与返回、完整澄清问答、每一版SQL及最后提交/终止；大段原文和SQL可折叠查看。没有逐事件墙钟时间戳，使用原始ADK序号；同批并行调用不假定严格先后决策。

[生成脚本](generate_readable_trajectories.py)、[中文事件说明](trajectory_annotations.py)与[覆盖校验](trajectory_manifest.json)位于本实验目录。仅覆盖这5条，不将Task Card替换为时间线。credit_11的旧卡片已更正：CES分量封顶来自T2知识定义，不能因用户回复未重述就将LEAST视为无依据变换。

5条时间线末尾、引用定义之前均附原始Priority及Follow-up Ground Truth SQL。对3条Priority失败任务另附最终SQL差异分析；2条成功任务保留通过结论。附录仅供研究者对照，未执行参考SQL，未重新评分，也不将未知的Follow-up失败原因混入Priority分析。[静态对照说明源码](trajectory_sql_analysis.py)随生成脚本保存。

## 结果与日志边界

|原始评测结果|任务数|补充区分|
|---|---:|---|
|Priority未通过|43|Follow-up未进入，phase2_passed=FALSE不等于Follow-up提交失败|
|两阶段均通过|13|直接采用评测字段|
|Priority通过、Follow-up未通过|16|9条有Follow-up工具行动，7条没有|

没有Follow-up工具行动的7条为：disaster_7、insider_8、virtual_6、archeology_M_4、disaster_2、fake_9、vaccine_6。它们均在最后一次Priority提交通过时达到记录的预算终止状态；是否有其他内部终止因素无法由现有日志确证。

共1226次工具调用：get_schema 72、get_all_external_knowledge_names 71、get_knowledge_definition 440、get_column_meaning 45、get_all_column_meanings 10、get_all_knowledge_definitions 15、ask_user 86、execute_sql 308、submit_sql 179。72条任务的ADK function_call参数/次数均与tool_trajectory匹配，响应数也一致。dialogue_history与86次ask_user逐次配对一致，每次均有回复文本；**有回复文本不等于有效解决所有问题**。62个任务使用ask_user，10个未使用。

发现4次明确的部分回复（fake_8 T16、fake_1 T9、mental_1 T34、polar_M_4 T18），1次明确拒答（gaming_7 T9）。这些是可见覆盖情况，不是对模拟器正确性的整体评价。没有独立核验其余回复的所有业务事实，标为SUBSTANTIVE_UNVERIFIED。

SQL错误分开统计：execute_sql中19次是只读策略拒绝，3次为数据库执行错误（2次列/关系不存在、1次除零）；submit_sql中7次报告具体执行错误（3次函数签名/类型、2次外键、1次关系不存在、1次对象已存在）。其余“SQL failed Phase”不能等同语法错或数据库失败。执行返回结果也不等于评测通过。

**全部72条的部分工具/ADK返回载荷存在原始裁剪。** tool_trajectory中149个结果带`<truncated>`，ADK亦有裁剪。get_schema每条均裁剪；全量知识定义也不能据导出认定模型未看见或已看见某条知识。某些SQL表格中的单元格本身也呈缩略样式，不能恢复为全量结果。记录字段齐全与返回内容完整是不同维度，CSV明确标为`RECORDED_FIELDS_COMPLETE_WITH_TRUNCATED_PAYLOADS`。未知信息不补全。

模拟器action parser的 **AMB/LOC/UNA原始标签没有写入这批保存字段**。CSV中真实分类统一UNKNOWN；逐次问答中仅提供分析者的AMB/LOC候选，并明确标为候选。候选依据问题是否直接对应预设意图、语义、知识、Schema或规格歧义；可由已给规则/数据推知的附加问题可列LOC候选。复合问题可能混合类型，**不能拿候选数量当模拟器类别统计**。gaming_7的拒答不证明它一定被内部标成UNA，也没有凭拒答断言Agent索取ground-truth SQL。

可见ADK文本仅是对外保存的说明/推理片段，不是完整隐藏reasoning。因此全任务reasoning_action_gap_candidate保守填UNKNOWN；没有把自我评价当成已完成行动。polar_M_4、vaccine_7的用户公式与后续表达式变化在卡片单独标注，它们不自动等于“计划调用A却调用B”。

## 判断与计数标准

1. **事件定位**：卡片Tn=tool_trajectory[n]、An=adk_events[n]、Dn=dialogue_history[n]，全部零基；链接回原Markdown对应标题。Tn也是事件编号，不另造不可追溯时间线。并行同批调用的数组顺序只表示归档顺序，不宣称依次决策的因果。
2. **事实/解释/未知**：事实来自元数据、问答、实际参数及返回；“候选”仅是初步解释。正确性/因果/完整意图状态缺少证据时为UNKNOWN。卡片最多3个现象、最多2个人工复核问题。
3. **完全重复**：同工具+JSON键排序后的完全相同参数；SQL字符串保留大小写、空格及注释，未做SQL语义归一化。每组从第2次算额外调用，合计17次；不是所有两两组合。阶段是否相同、返回是否相同均另记。工具调用计数包含被策略拒绝的尝试。
4. **重复知识**：仅get_knowledge_definition名称去多余空白、忽略大小写后重复，合计11次；不同定义不计重复。先读单项、再取全量是覆盖候选而非同参重复。不能据多次查询直接判定浪费。
5. **相似SQL**：同阶段相邻两次execute_sql，压缩空白/忽略大小写后SequenceMatcher文本相似度≥0.85；这是文本候选，可能是合理诊断或改写，不是语义等价/低信息增益判定。
6. **信息利用**：逐任务人工指出回复中的指标、阈值、列名或规格与后续SQL/行动的局部对应，并给出工具索引；不以SQL成功作为利用证据，也不以失败否定利用。OBSERVED只表示可见局部采用，不能推定所有答复都完整忠实。没有额外实验判断Schema/知识与SQL的因果来源。
7. **修正候选**：出现执行错误、策略拒绝或提交未通过反馈之后，同阶段有不同SQL。证据索引标注反馈类型与下一次不同SQL的位置，不能据文本变化保证修正成功。后续不再报执行错误只说明该局部错误未在该次返回重现，不证明业务语义正确。
8. **预算**：初始取ADK首条任务消息；最终与消耗严格取原始任务字段。budget_exhausted仅看最终<=0。59条末余0；其余13条有余量，不自动解释为提前停止异常。cost是日志标称工具成本，不能相加当实际扣费或token费用：终止常出现budget_after=-1且上层budget_remaining截为0，预算/成本不总可直接相减。59条含这类账面差异，逐次列于evidence_index.json。nonnegative_ledger_delta_by_tool仅统计终值非负的账面变化，不是完整实际扣费。
9. **任务结果和歧义分离**：Priority的正确反馈作为阶段边界；has_follow_up只表示有后续题，follow_up_attempted表示边界后存在工具调用。ambiguity_fully_resolved统一UNKNOWN，因为局部澄清/最终通过都不能证明完整认知状态。未ask_user不记为失败策略，卡片给出通过工具自行解释的可见路径。

## 特征字段说明

所有布尔型字段使用TRUE/FALSE/UNKNOWN；不适用或无证据时不强填FALSE。数值字段保留原值或按上述标准计数。其他状态字段使用下表枚举。

|字段|含义|
|---|---|
|task_id / database|任务ID / 数据库，来自评测元数据|
|phase1_passed / phase2_passed / has_follow_up|原始阶段成功字段 / 是否具有后续任务|
|total_reward / elapsed_seconds|原始奖励 / 运行耗时秒数|
|budget_used / budget_remaining|原始消耗 / 最终剩余bird-coins|
|initial_budget / budget_exhausted|初始任务消息中的预算 / 最终是否<=0|
|dialogue_agent_turns / dialogue_user_turns|对话记录中agent/user消息数；本批一问一答配对，不含内部模型轮次和工具响应|
|ask_user_count / tool_call_count|ask_user调用数 / tool_trajectory总条目数|
|get_schema_count / get_column_meaning_count|对应工具调用数|
|get_all_external_knowledge_names_count / get_knowledge_definition_count|知识名列表 / 单个定义工具调用数|
|get_all_knowledge_definitions_count / get_all_column_meanings_count|全量知识 / 全量列含义调用数|
|execute_sql_count / submit_sql_count|试执行 / 提交调用数，含被拒绝的尝试|
|repeated_identical_tool_call_count|按同工具完全同参数计的额外调用数|
|repeated_knowledge_query_count|按规范化知识名计的额外单项查询数|
|ambiguity_recognized|TRUE=有提问或可见文本明确使用ambiguity/unclear/uncertain；没有可见表达为UNKNOWN，不用未提问推断FALSE|
|ask_user_used|是否存在ask_user调用|
|user_clarification_received|有ask时至少一次具体回复为TRUE；均拒答为FALSE；没有ask为UNKNOWN。部分回答也可TRUE，另看partial计数|
|user_information_utilization|OBSERVED=有局部采用证据；PARTIAL=局部采用但关键问题/另一回复未解决；PARTIAL_OR_CHANGED=采用后又存在公式变化；NOT_APPLICABLE=无ask。均不表示全部信息已忠实采用|
|reasoning_action_gap_candidate|严格工具计划与行动落差，本批均UNKNOWN|
|sql_executed|是否调用execute_sql，TRUE包含政策拒绝的尝试；不代表成功执行SQL|
|sql_execution_error_count|execute_sql中明确数据库执行错误数，排除只读政策拒绝|
|sql_correction_candidate|有错误/拒绝/评测未通过后的不同SQL为TRUE，无相应证据为UNKNOWN|
|data_completeness|本批为RECORDED_FIELDS_COMPLETE_WITH_TRUNCATED_PAYLOADS：已有字段齐全但载荷被裁剪|
|manual_review_priority|HIGH/MEDIUM/LOW，人工阅读优先级，不是失败严重程度或模型性能排名|
|follow_up_attempted|Priority成功边界之后是否有实际工具调用|
|failure_stage|NONE / PRIORITY / FOLLOW_UP / FOLLOW_UP_NOT_ATTEMPTED；后者保留未尝试的区别|
|sql_policy_rejection_count|execute_sql明确Only SELECT allowed的次数|
|sql_submit_execution_error_count|submit_sql返回的明确SQL执行错误数，独立于execute_sql|
|sql_empty_result_count|execute_sql明确写empty result set的次数；没标记不等于一定非空|
|similar_consecutive_execute_sql_pair_count|同阶段相邻执行SQL文本相似度>=0.85的对数|
|user_partial_reply_count / user_refusal_count|人工确认的部分回复 / 明确拒答次数|
|simulator_action_classification|模拟器原始AMB/LOC/UNA，本批UNKNOWN；分析者候选在证据索引和卡片|
|ambiguity_fully_resolved|完整歧义认知是否解决，本批UNKNOWN|
|nominal_tool_cost_sum|各工具cost字段之和，仅标称成本，不能视作实际支出|
|budget_ledger_anomaly_count|budget_after<0或(before-after)!=cost的条目数|
|tool_payload_truncated_count / adk_event_truncated_count|工具结果 / ADK事件含显式<truncated>的数量；两者可能描述同次返回，不应相加当独立损失|
|tool_calls_match_adk|ADK function_call工具名/参数多重集合是否与tool_trajectory完全一致；不额外推断并行因果顺序|

优先人工核查：问答是否覆盖所有子问题、候选AMB/LOC类别、回复是否忠于任务定义、局部公式是否保持、SQL改写是否真正针对反馈、截断是否遮住关键上下文。原始日志不足以确认隐藏reasoning、真实action类别及全部歧义是否消除；不要求人工凭现有材料补出不存在的信息。

## 建议优先精读的10条

以下是阅读次序建议，不是Agent修改方案或研究创新结论。每条卡片提供具体事件链接。

|任务|优先理由|
|---|---|
|[mental_1](task_cards/mental_1.md)|T34–36：一次询问的 TES 公式未获回复，随后自行构造 TES；31次单项知识查询均为不同名称。|
|[fake_8](task_cards/fake_8.md)|T16–17、19、21：首答要求其余问题另问，二次补齐后又遇列错误，适合区分回复覆盖与SQL自纠错。|
|[polar_M_4](task_cards/polar_M_4.md)|T12、18–20；A27、29：用户明确公式后，最终又给水位除100；第二次回复只回答设备范围。|
|[vaccine_7](task_cards/vaccine_7.md)|T11–18；A19、21：先按用户 CURRENT_DATE 得到空结果，失败后改用数据日期，并处理除零。|
|[alien_6](task_cards/alien_6.md)|T5/9/13/29、26/30：同一知识读取4次；用户给出阈值后，RPI公式仍未获确认，未试执行即报ROUND类型错误。|
|[gaming_M_4](task_cards/gaming_M_4.md)|T11、13–16：删除规则已获明确答复，提交连续遭遇两个外键约束；应与策略拒绝、语法错误分开。|
|[disaster_7](task_cards/disaster_7.md)|T2–27、29：25个不同知识名称后才询问CEE；Priority通过时预算已终止，没有Follow-up SQL。|
|[news_M_4](task_cards/news_M_4.md)|T2–4：同参提交跨阶段，第二次报索引已存在，随后改DROP+CREATE并通过；是重复调用不能直接等同浪费的对照。|
|[fake_9](task_cards/fake_9.md)|T14–22：逐层澄清CPRI/SRS/top；回复top10而Follow-up写top5，且Priority通过后无后续工具行动。|
|[credit_8](task_cards/credit_8.md)|T15–17：用户给出rentpayment路径，抽样为NULL，SQL采用COALESCE后最终报ROUND类型错误，需区分信息利用与执行失败。|

## 全部72条卡片索引

|任务|Priority|Follow-up|Follow-up有工具行动|ask_user|阅读优先级|
|---|---|---|---|---:|---|
|[alien_11](task_cards/alien_11.md)|FALSE|FALSE|FALSE|0|HIGH|
|[alien_6](task_cards/alien_6.md)|FALSE|FALSE|FALSE|1|HIGH|
|[alien_7](task_cards/alien_7.md)|FALSE|FALSE|FALSE|2|HIGH|
|[alien_8](task_cards/alien_8.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[archeology_1](task_cards/archeology_1.md)|FALSE|FALSE|FALSE|2|MEDIUM|
|[archeology_6](task_cards/archeology_6.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[archeology_9](task_cards/archeology_9.md)|FALSE|FALSE|FALSE|2|HIGH|
|[archeology_M_4](task_cards/archeology_M_4.md)|TRUE|FALSE|FALSE|1|HIGH|
|[credit_11](task_cards/credit_11.md)|FALSE|FALSE|FALSE|2|HIGH|
|[credit_4](task_cards/credit_4.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[credit_8](task_cards/credit_8.md)|FALSE|FALSE|FALSE|2|HIGH|
|[credit_M_6](task_cards/credit_M_6.md)|TRUE|TRUE|TRUE|1|LOW|
|[cross_db_3](task_cards/cross_db_3.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[cross_db_4](task_cards/cross_db_4.md)|FALSE|FALSE|FALSE|2|MEDIUM|
|[cross_db_5](task_cards/cross_db_5.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[cross_db_M_4](task_cards/cross_db_M_4.md)|TRUE|TRUE|TRUE|1|LOW|
|[crypto_2](task_cards/crypto_2.md)|FALSE|FALSE|FALSE|1|HIGH|
|[crypto_3](task_cards/crypto_3.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[crypto_M_2](task_cards/crypto_M_2.md)|TRUE|FALSE|TRUE|0|MEDIUM|
|[crypto_M_4](task_cards/crypto_M_4.md)|FALSE|FALSE|FALSE|0|MEDIUM|
|[cybermarket_1](task_cards/cybermarket_1.md)|TRUE|TRUE|TRUE|1|LOW|
|[cybermarket_2](task_cards/cybermarket_2.md)|FALSE|FALSE|FALSE|2|MEDIUM|
|[cybermarket_M_1](task_cards/cybermarket_M_1.md)|FALSE|FALSE|FALSE|2|MEDIUM|
|[cybermarket_M_4](task_cards/cybermarket_M_4.md)|TRUE|TRUE|TRUE|2|MEDIUM|
|[disaster_2](task_cards/disaster_2.md)|TRUE|FALSE|FALSE|1|HIGH|
|[disaster_3](task_cards/disaster_3.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[disaster_7](task_cards/disaster_7.md)|TRUE|FALSE|FALSE|1|HIGH|
|[disaster_M_2](task_cards/disaster_M_2.md)|FALSE|FALSE|FALSE|2|HIGH|
|[fake_1](task_cards/fake_1.md)|FALSE|FALSE|FALSE|1|HIGH|
|[fake_2](task_cards/fake_2.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[fake_8](task_cards/fake_8.md)|FALSE|FALSE|FALSE|2|HIGH|
|[fake_9](task_cards/fake_9.md)|TRUE|FALSE|FALSE|4|HIGH|
|[gaming_1](task_cards/gaming_1.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[gaming_2](task_cards/gaming_2.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[gaming_7](task_cards/gaming_7.md)|FALSE|FALSE|FALSE|2|HIGH|
|[gaming_M_4](task_cards/gaming_M_4.md)|FALSE|FALSE|FALSE|2|HIGH|
|[insider_4](task_cards/insider_4.md)|FALSE|FALSE|FALSE|2|MEDIUM|
|[insider_8](task_cards/insider_8.md)|TRUE|FALSE|FALSE|1|HIGH|
|[insider_M_5](task_cards/insider_M_5.md)|TRUE|TRUE|TRUE|0|LOW|
|[insider_M_6](task_cards/insider_M_6.md)|TRUE|FALSE|TRUE|0|MEDIUM|
|[mental_1](task_cards/mental_1.md)|FALSE|FALSE|FALSE|1|HIGH|
|[mental_9](task_cards/mental_9.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[mental_M_1](task_cards/mental_M_1.md)|TRUE|TRUE|TRUE|1|LOW|
|[mental_M_2](task_cards/mental_M_2.md)|TRUE|TRUE|TRUE|1|LOW|
|[museum_1](task_cards/museum_1.md)|FALSE|FALSE|FALSE|1|HIGH|
|[museum_10](task_cards/museum_10.md)|FALSE|FALSE|FALSE|0|MEDIUM|
|[museum_6](task_cards/museum_6.md)|TRUE|TRUE|TRUE|0|HIGH|
|[museum_M_4](task_cards/museum_M_4.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[news_4](task_cards/news_4.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[news_9](task_cards/news_9.md)|FALSE|FALSE|FALSE|0|HIGH|
|[news_M_1](task_cards/news_M_1.md)|TRUE|TRUE|TRUE|0|LOW|
|[news_M_4](task_cards/news_M_4.md)|TRUE|TRUE|TRUE|0|HIGH|
|[polar_5](task_cards/polar_5.md)|FALSE|FALSE|FALSE|2|HIGH|
|[polar_7](task_cards/polar_7.md)|TRUE|FALSE|TRUE|1|HIGH|
|[polar_M_3](task_cards/polar_M_3.md)|TRUE|FALSE|TRUE|1|MEDIUM|
|[polar_M_4](task_cards/polar_M_4.md)|FALSE|FALSE|FALSE|2|HIGH|
|[robot_10](task_cards/robot_10.md)|FALSE|FALSE|FALSE|2|HIGH|
|[robot_6](task_cards/robot_6.md)|TRUE|TRUE|TRUE|1|MEDIUM|
|[robot_8](task_cards/robot_8.md)|TRUE|TRUE|TRUE|1|LOW|
|[robot_M_3](task_cards/robot_M_3.md)|FALSE|FALSE|FALSE|3|HIGH|
|[solar_10](task_cards/solar_10.md)|TRUE|FALSE|TRUE|1|MEDIUM|
|[solar_3](task_cards/solar_3.md)|TRUE|FALSE|TRUE|1|HIGH|
|[solar_4](task_cards/solar_4.md)|TRUE|FALSE|TRUE|1|HIGH|
|[solar_6](task_cards/solar_6.md)|FALSE|FALSE|FALSE|1|MEDIUM|
|[vaccine_2](task_cards/vaccine_2.md)|FALSE|FALSE|FALSE|1|HIGH|
|[vaccine_6](task_cards/vaccine_6.md)|TRUE|FALSE|FALSE|1|HIGH|
|[vaccine_7](task_cards/vaccine_7.md)|FALSE|FALSE|FALSE|1|HIGH|
|[vaccine_M_2](task_cards/vaccine_M_2.md)|FALSE|FALSE|FALSE|1|HIGH|
|[virtual_1](task_cards/virtual_1.md)|TRUE|TRUE|TRUE|1|LOW|
|[virtual_6](task_cards/virtual_6.md)|TRUE|FALSE|FALSE|2|HIGH|
|[virtual_M_4](task_cards/virtual_M_4.md)|TRUE|FALSE|TRUE|1|MEDIUM|
|[virtual_M_5](task_cards/virtual_M_5.md)|TRUE|FALSE|TRUE|2|MEDIUM|
