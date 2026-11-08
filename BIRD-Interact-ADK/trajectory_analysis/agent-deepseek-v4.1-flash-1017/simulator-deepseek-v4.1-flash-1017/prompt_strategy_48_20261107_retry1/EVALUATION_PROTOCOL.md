# Prompt 对照实验评价标准

在完成首批轨迹审查前制定；研究者对 benchmark 原文和知识库进行评价，不使用 Agent 的自评分。任务隐藏信息仅用于离线分析，不能注入被评测 Agent。

## 计数口径

- 知识定义工具为 get_knowledge_definition 与 get_all_knowledge_definitions。Knowledge Tool Calls 默认二者之和；名称列表另列 Name Discovery Calls，并另报包含名称列表的总知识成本，避免成本转移。
- 调用区分 attempted（ADK function_call）、executed/recorded（tool_trajectory）、budget rejected（返回预算错误）。标价 cost 不等于实际扣费；用非负 budget_before→budget_after 差额核验。拒绝调用不算成功取得定义。
- Unique Definitions Retrieved：成功返回的不同知识条目 ID 数。全量返回用冻结知识库和原有 _filter_knowledge 隐藏规则重建完整集合；标注这是源文件重建，不是日志原文恢复。
- Exact Duplicate Retrievals：一次查询返回至少一个之前已返回的相同 ID，记一次重复调用；另报重复条目数。相同查询反复 not-found 另记 repeated failed lookups，不虚算取得定义。
- First Ask Timing：第一次实际 ask_user 在全部工具轨迹中的一基序号，并报此前知识调用次数、花费；未询问为 NA，单独报告 no-ask 比例。现有日志无可靠逐事件时间戳，不报秒。
- Priority Success / Follow-up Success 使用原 runner P1/P2 布尔值，P2 以全部 runs 为分母并补充以 P1 成功为分母的条件值。Remaining Budget 为原 runner 截零字段；保留原工具预算用于核验。
- Total Tool Calls 默认实际记录工具调用，另报尝试和拒绝数。
- Context Tokens 为 NA：原 ADK 事件不保存 usage，不能用字符数冒充 token。

## 语义指标

每个判断引用 run、task、工具序号和原文证据，并说明知识 ID 与所解决的信息需求。不能只看名称相似度。

Retrieval Relevance：以成功返回的“条目出现次数”为分母，内容直接支持当前或已公布 follow-up 中一个必要计算、筛选、分组、连接或输出需求记 1；只泛泛相关、不解决实际需求记 0。另报 useful-query rate（一次调用至少提供一个相关条目）和 failed-lookup rate。全量中不相关条目不能因整次调用有用而全部算相关。零返回时 relevance 为 NA。

Semantic Redundancy：已获信息之外，一次返回的相关内容若实质等价且不增加所需公式、阈值、映射或约束，则为语义重复；精确 ID 重复单列。主要报告语义重复调用数、重复条目数及无效探索（无新增相关信息调用数），不将不同但无关的条目误叫语义重复。解释性旁支若不能解决任务需求，计低相关，不计等价信息。

Knowledge Coverage：以固定 P1 必需知识单元为分母；分别报告 tool-only 和 tools+user。只有得到完整可用定义才算覆盖，名称列表、not-found、自行猜测公式都不算。覆盖不要求 SQL 最终正确；补充正确采用情况。Follow-up 新知识单独计算，避免 P1 未通过导致不同分母。

Ambiguity Resolution Rate：固定 P1 信息需求清单，只有工具或用户回答确实解决才算；部分解决单独列，不计完整解决。另报用户语义需求子集的比例。必须核对实际回复内容与 benchmark 证据，不因调用 ask_user 就视为解决。

Unnecessary Ask Rate：提问时，答案已在可见 schema/已取得知识/执行结果/先前回答中确定，或重复已解决问题而没有新缺口，记不必要；重要业务歧义、缺失定义、用户未明确的视图/范围不算。复合问题按整次 ask 标注必要/部分不必要/不必要，主率只计完全不必要，另报含部分不必要的上界。没有 ask 的 run 率为 NA；组率采用总不必要次数/总 ask 次数，并报告各 run 宏平均。

## 固定 P1 知识与信息需求

- credit_11：知识 K1 CES 完整公式（KB7）；K2 digital-first 判据（KB14，被隐藏）；K3 高参与阈值 CES>0.7（KB50，被隐藏）。语义需求 S1 digital natives 映射，S2 engagement score 指标映射，S3 high engagement 阈值，S4 cohort 与 digital-first 子集分母；结构/时间需求 S5 按 scoredate−tenureyrs 推导季度 cohort。CES KB 的封顶说明与参考 SQL 不一致，保留原评分并标注。
- virtual_1：知识 K1 GIQ 公式（KB34，被隐藏）；K2 Gift-Focused Supporter 判据 GIQ>50 且 spendusd<100（KB49）。需求 S1 supporters/gift-heavy 含义与阈值，S2 gift score 指标及公式，S3 lower-tier=Free/Basic；四舍五入/排序为补充非关键需求，单列。
- polar_M_4：知识 K1 WRMI 公式（KB7，被隐藏）；K2 三段状态分类及完整标签（KB53）。需求 S1 summary 是命名视图 water_management_view，S2 water-management-score 指标与公式，S3 状态阈值标签，S4 输出设备引用/分数/分类，S5 relevant=有水位数据的设备。保留 DDL 原执行协议。
- cybermarket_1：知识 K1 TCR 完整公式（KB16，被隐藏）；K2 Money Laundering Indicator 四项过滤（KB23）；P2 另需 CSR 公式（KB13）。需求 S1 suspicious chains 对应 laundering 条件，S2 chain risk 指标公式，S3 top risky ones 排序/是否 LIMIT（参考 SQL 不限制条数），S4 输出与连接来源。

组汇总报告 12 runs 的均值、样本标准差；每条任务 3 次同样报告。补充三个重复轮次中每组四任务均值的标准差。率说明分母，NA 不用 0 代替。只有三次重复，不作统计显著性结论。

用户语义子集固定为：credit_11 S1/S3/S4；virtual_1 S1/S3；polar_M_4 S1/S4；cybermarket_1 S1/S3。其余单位归为指标定义、结构或上下文需求。部分解决仍记未完整解决并保留说明。

条目相关性采用保守的内容支持集合：credit KB7/51，virtual KB3/7/49，polar KB53，cybermarket P1 KB23；P2明确公布后再加入KB13。它们分别提供目标公式、季度定义、会员/礼物字段语义、Gift-Focused判据、WRMI分类或laundering判据。其他相近概念不因名称或共享字段而自动算有用；原始全文保留以供复核。

审查补充口径：Knowledge Coverage 主值指最终无未解决冲突的可靠覆盖；若先得到正确公式、后收到未解决的相反回答，则该单元主值不算覆盖，并另报 ever-correct-seen 覆盖及 Simulator 错误证据。语义重复包含此前用户/结构证据已提供的目标信息；同次全量调用若同时有精确ID重复与跨来源语义重复，包含精确重复的总重复调用数按工具序号取并集，不重复相加。

公式复核的标注边界：明确引用新的执行值与定义尺度冲突的复核，视为必要（如WRMI数值达到数百而阈值为0.5/0.7）；仅笼统提到提交失败，同时再问已明确给定的公式，则该子问标为部分冗余。部分冗余仍不计整次完全不必要，另报上界供读者复核。cybermarket 的 S3 要求明确排序及 top-N/全部结果范围；只确认降序视为部分解决，不因最终SQL恰好无LIMIT而倒推已消歧。
