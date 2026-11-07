"""逐任务人工观察；仅描述已有轨迹，不评价 SQL 语义是否正确。"""
# task_id | 行为过程 | 重点事实 | 证据工具索引 | 信息利用说明 | 利用证据索引 | 核查优先级
ROWS = r'''
alien_11|先读 AOI/OOW 定义并执行分组 JSON 查询，随后多次改动 JSON 键和名称空白后提交。全程未询问用户。|4 次提交均未通过 Priority；执行返回数据，不能据此定位为语法错误。|5,6,9,11,12|无 ask_user；AOI/OOW 条件可见于后续 SQL。|2,3,5|HIGH
alien_7|探索多个观测条件定义后询问阈值，用户将 AOI>0.8 的候选解释纠正为组合 OOW 条件。首次提交失败后，又询问 JSON 键并修改输出。|明确采用了用户的阈值和键名，仍连续未通过；失败原因不能由键名猜测确证。|8,9,15,16,17,18|SQL 使用 AOI>0.85、月相/距离/太阳条件；后续使用 station、aoi、is_optimal_window。|9,16|HIGH
archeology_1|先查询多个质量指标，再两次询问 scan quality 的指标及公式。随后检查关联键并生成站点聚合 SQL，最后改变关联条件重提。|用户两次澄清后，SQS 公式进入 SQL；新增排名列及关联选择是否影响提交需另核。|5,6,7,12,13,14|后续查询采用 LOG/POWER、覆盖率和噪声因子，并按站点 AVG。|12,14|MEDIUM
archeology_9|先查询多个不同知识定义，再询问 FEE 含义与公式。探索跨表关联后遇到字段错误，改字段直接提交，又收到类型错误。|先修正不存在的列，最终提交仍因 round(double precision, integer) 不存在而失败。|22,23|FEE 分子、PCDR 与 sqrt(clouddense)、正值保护进入查询；PCDR 与 SDI 的等同关系未获明确确认。|15,22,23|HIGH
credit_8|先查 DTI 和列含义，再询问指标及分组阈值。探查住房 JSON 后，第二次询问 rentpayment 字段，最后直接提交聚合查询。|用户指明的租金 JSON 路径在抽样中返回 NULL；最终提交报 ROUND 类型错误。|15,16,17|使用 rentpayment 路径和 COALESCE，计算 TDSR，分组过滤 COUNT>10。|16,17|HIGH
credit_M_6|定义查询未找到 FSI 后，询问列名及公式。写操作试执行受限，改用 SELECT 检查公式，再提交 DDL/DO；Follow-up 查询最大 FSI。|只读工具限制后改用 SELECT 验证并通过两个阶段。|5,6,7,8,9|新增 fsi NUMERIC(5,3)，更新公式包含用户给出的四项权重和资产/收入比例。|4,7|LOW
cross_db_5|先根据跨境合规知识自行解释问题并提交，失败后补查知识与列含义。随后询问 transfer path 和排序，继续修改过滤及别名提交。|询问只覆盖路径和排序，compliance issues 的过滤解释仍在多次提交间变化。|7,11,14,15,16|后续使用 Origin -> Destination 拼接和合规 ID 升序。|13,14|MEDIUM
cross_db_4|查 DSI 及安全定义，缺失 SRS 公式后询问用户。看到 Critical 枚举值后再问权重，最后尝试 JSON 聚合与逐行 JSON 两种输出。|第二次回复给出 ELSE=1，但同时反问偏好；Agent 按该默认解释执行。|8,10,11,12,13,14|SRS 使用 Full/Strong 组合 CASE，Critical 落入 DSI 的 ELSE 1。|12,14|MEDIUM
crypto_3|先查多个不同风险定义及全量知识，再询问 PVaR 公式和 top 数量。先自行选择最新波动率，失败后改成市场对与交易所双键关联。|用户限定的公式和 top5 被采用，但最新波动率的关联/时间解释仍变化。|15,18,19,20,21,22|采用 possum×volmeter×0.01，riskandmarginpivot 降序 LIMIT 5。|18,21|MEDIUM
crypto_M_4|查询 Whale Order 定义，探索订单方向和市场深度，再尝试创建视图。试执行受限后提交；失败后将流动性从按方向选择改为买卖两侧之和。|失败后更换 available_liquidity 的业务解释，未询问用户；不能由此判定哪种解释正确。|8,9,11,13|无 ask_user；Whale Order 的 10% 条件可见于 SQL。|2,8|MEDIUM
cybermarket_2|先询问 trustworthy 阈值、附加条件和输出细节，执行并提交。失败后补查列含义、再次询问输出，再改别名重提。|用户明确的过滤规则进入查询；后续主要改别名，仍未通过。|3,5,6,10,11,12|使用 VTI>80、Advanced/Premium、争议率<5%、span>90；后续使用 market 别名。|5,11|MEDIUM
cybermarket_1|初始把 suspicious chains 对应到另一种可疑模式，用户纠正为 TCR 及钱包条件。提交通过后，补查 CSR 和 VPN 枚举，扩展 SQL。|用户纠正了指标映射，后续两个阶段通过。|4,5,6,7,9,10|采用 TCR 加权式、TCR>150、wallage<30、wallturnrt>5 和 linkedtxcount>=3。|5,9|LOW
disaster_3|查分类、列含义和全量知识后询问 EIF 公式。执行后多次调整是否关联 operations、输出粒度及排序，再提交。|获得明确公式后，后续改动集中在粒度/排序，Priority 仍未通过。|7,8,9,13,15|使用碳排放可再生能源调整项和回收率惩罚项，并 ROUND 到两位。|8,15|MEDIUM
disaster_7|先连续读取大量不同知识定义，最后询问 CEE 公式和社区分类。执行一次并提交，Priority 通过后没有后续工具调用。|末次 Priority 提交已到预算终止状态，未观测到 Follow-up SQL。|27,28,29|查询含 BSI、参与等级映射、利益相关者满意度和社区分类 CASE。|28,29|HIGH
fake_8|先查放大网络与多种影响指标，再集中询问多个歧义。首答只解释 reach score，第二次询问补齐阈值与 top 定义，随后处理字段错误并提交。|首答明确要求其余歧义另问；第二次补齐后 SQL 仍未通过。|16,17,19,21|采用 netinflscore、>80、postfreq>30 和 Amplifier/coordscore 条件。|18,21|HIGH
fake_1|查询 Bot Network、LBS 和检测字段，提出同时涉及 BBI/过滤/top 的问题。回复只明确 top100，随后自行调整 BBI 标度与最新检测聚合。|回复未确认 BBI=botlikscore/100 的假设；后续 SQL 仍采用该映射。|9,12,17|LIMIT 100 与平均 BBI 降序可见；BBI 的指标映射未获回复确认。|12,17|HIGH
gaming_7|获取 PER 及耐久定义后询问 DS 公式与 high endurance 阈值。首次提交失败后问 registry ID，收到拒答，随后改输出 ID 再提交。|第二次询问明确被拒绝；这只证明该回复无效，不能直接确定模拟器内部 UNA 分类。|5,8,9,11|DS 公式、IPX 映射和 PER>9 进入 SQL；registry ID 未得到有效澄清。|6,8,11|HIGH
gaming_M_4|探索音频质量知识与分布后询问 AQI/删除条件，再确认应返回被删记录。尝试删除受限后提交，收到两层外键约束错误。|先遇 audioandmedia→rgb 外键，再尝试处理相关表，仍遇 physicaldurability→interactionandcontrol 外键。|11,13,14,15,16|采用 AQI 公式与四条件 OR，DELETE RETURNING 返回被删设备的三项信息。|15,16|HIGH
insider_8|读取多种交易者定义、全量知识并探查数据，随后询问 fast movers 和 OMI。用户否定额外频率/持仓过滤并给出 OMI 公式，提交通过 Priority。|Priority 通过时记录已终止预算，没有 Follow-up 工具调用。|18,19,20,21|使用 modfreq/(1-cancelpct)，并按 Volatile Event Speculator 条件筛选。|19,21|HIGH
insider_M_5|根据 Peer Correlation Z-Score 定义与列含义生成标准化查询，检查异常分母处理后提交更新。Follow-up 对更新值分交易者类型统计。|未 ask_user，两个阶段均通过；可见知识定义提供了可操作规则。|2,4,5,6,7,8|无用户澄清；按 tradekind 分区、STDDEV_SAMP 和零分母保护进入更新逻辑。|2,5,6|LOW
mental_9|查询 PFIS、FRAI 和缺失的 RDD，询问差值公式与 prevalence 含义。之后尝试不同 top 限制并提交，未进一步确认 top 数量。|回复确认 RDD 和 SRP，未确定 top facilities 的数量；提交之间调整该选择。|8,12,13,15|采用 PFIS−FRAI 和 SRP>20；top 限制属于后续自行选择。|12,15|MEDIUM
mental_1|先读取大量不同知识条目和全量定义，再一次询问 urgent-risk 与 TES。回复只解释风险标准，之后构造复杂 SQL 并直接提交。|TES 公式问题未在回复中得到回答，最终查询中的 TES 映射需要核查。|34,35,36|回复的 suicrisk/PHQ/GAD 风险条件进入 SQL；TES 的用户信息来源不足。|35,36|HIGH
museum_6|读取环境异常定义并检查数据，未询问用户。先提交环境读数 ID，未通过后改为展示柜 ID；通过后关联展品并聚合列表。|只改 ID 选择即从 Priority 未通过变为通过，后续阶段也通过。|7,8,9,10|无 ask_user；环境变化阈值和展示柜关联可见于后续 SQL。|2,7,8|HIGH
museum_M_4|查列含义和现有评分范围，再询问允许区间。随后多次改变 CHECK 的名称或写法并提交；中间一次 DDL 试执行被拒绝。|用户给出 1–10 后仍多次未通过；日志不足以把原因归为约束名称。|4,5,7,8,9,10|各次约束均使用用户限定的 1≤histsignrating≤10。|5,10|MEDIUM
news_M_1|获取 UER 定义后试算公式，DDL/UPDATE 的 execute_sql 被拒绝，随后提交并通过。Follow-up 直接提交平均 UER 查询。|未 ask_user，两个阶段通过；写操作限制未阻止最终提交。|2,4,5,6|无用户澄清；定义中的 views×engscore/duration 进入 SQL。|2,3,5|LOW
news_9|先读推荐相关定义并探索数据，自行构造 CTR 后提交。失败后查更多知识，调整分母与关联，最后再次提交。|缺失 RCTR 定义时未询问用户；后续在互动数与推荐数两种分母间调整。|8,9,10,14|无 ask_user；CTR 分母改变可见，但不能据此判断歧义全部消除。|8,14|HIGH
polar_5|查水资源分类、列含义及多个知识条目，询问 WRMI 公式。两次提交失败后再问 classification/management situation 映射，随后重提。|后续提交与此前一次提交完全相同；补充回复确认了已有映射，但未使提交通过。|14,17,18,19,20|使用未对 waterlevelpercent 再除100的公式；分类分别基于组均值 WQCS 与 WRMSC。|16,18,20|HIGH
polar_7|查能源分类与列含义，多次重查同一定义，询问 ESI 公式后通过 Priority。Follow-up 查 WRMI 并关联水资源，但提交未通过。|3 次同参知识重查发生在提问前；Follow-up 有实际执行与提交。|8,10,11,12,15,16,17,18|采用用户规定的电源类型倍率，且在 Follow-up SQL 保留 ESI 表达式。|14,17|HIGH
robot_M_3|询问维修优先级规则后构建存储表与 upsert，失败后分别询问时间戳语义及确切列名。后续修改 DDL/DML，但最终仅 INSERT 报表不存在。|最后一次错误明确为 maintenance_status 不存在；不能混作优先级计算错误。|9,15,18,19,20|采用 CRITICAL/WARNING/NORMAL 阈值、current_timestamp 和指定五列名。|16,19,20|HIGH
robot_6|查工具磨损、周期和状态知识后，询问平均严重度及 top 数量/排序。Priority 通过，Follow-up 添加 URGENT 筛选和厂商/故障信息，失败一次后重提通过。|两个阶段通过；Follow-up 修订了最新故障的取得方式。|9,11,13,14,15|使用 AVG(toolwearpct)、LIMIT100、TWR/TPC 排序，后续保留相关聚合。|10,11,15|MEDIUM
solar_4|查 MROI 及成本相关定义，询问 MCE 公式后通过 Priority。Follow-up 加 MCE>100 筛选，多次执行和提交仍未通过。|Follow-up 最后一次提交与此前一版完全相同；不能将 Priority 正确公式直接视为 Follow-up 成功。|9,11,12,14,16|MCE 使用维护/清洁/更换成本之和除容量；Follow-up HAVING 使用该表达式。|10,12,16|HIGH
solar_3|查温度相关指标后询问 temperature impact 的含义及公式。Priority 通过，Follow-up 增加 critical alerts 和三个月时间窗，随后变更关联与参考时间。|Follow-up 将时间参考改为数据最大 alertmoment；这一解释没有用户确认。|8,11,14,17|采用功率×温度系数×(电池温度−25) 的平均值，Follow-up 保留公式。|10,17|HIGH
vaccine_7|查冷却分类和列含义后询问 CDR，按 CURRENT_DATE 计算出现空结果。失败后尝试数据参考日期并遇除零，最后加 NULLIF 重提。|最终从用户给定 CURRENT_DATE 改为 MAX(timemark)；是可定位的解释变化候选。|11,12,15,16,18|最初采用用户 CDR 公式，后续更换参考日；并非完全未使用用户信息。|12,18|HIGH
vaccine_2|查 CRI 及全量知识并探索传感数据，自行使用 tempstabidx 作为 TSS。询问 sensor status 后引入可用性标记，随后调整聚合与 CRI。|sensor status 已澄清，但 TSS/Container Health 的缺失定义没有对应询问。|6,10,12,14,16|使用传感记录是否存在来生成 No Sensor Data/Sensor Data Available。|11,16|HIGH
virtual_6|查 churn 映射及全量知识后，两次询问风险指标和 RRF 权重。首次提交失败后检查关联/计数再重提，通过 Priority 时预算终止。|Priority 通过后未执行 Follow-up；不是一份失败的 Follow-up SQL。|10,11,13,17|后续采用不一致度权重2、登录月数权重0.5和 churn_numeric，并分组四舍五入。|12,17|HIGH
virtual_M_4|查流失相关知识后询问 at risk 采用哪种标准。探索数据并提交 DELETE，通过 Priority，随后用同一筛选尝试统计删除数但未通过。|Follow-up 实际提交的是关联后的 COUNT(*)；其与被删账号数的关系需核查。|7,14,15|采用 Churn Candidate 的时间、engrate 和 RRF>3.5 条件。|14,15|MEDIUM
alien_8|读 NTM 分类等知识并查看调制类型，再问 narrowband 过滤与调制规则。按用户解释构造 SQL，未通过后调整频漂绝对值/过滤。|用户明确排除调制类型过滤，后续 SQL 无该过滤；频漂解释仍变化。|10,11,12,15,16|使用 BFR 和 drift 阈值，不再按 signalclass 或 Unknown 调制筛选。|11,16|MEDIUM
alien_6|探索多个指标和列含义，反复获取 Research Critical Signal，再询问 important 定义。用户给出 RPI/CCS 阈值后又查知识，最后未试执行即提交。|Research Critical Signal 共读4次；最终提交报 ROUND 类型错误。|5,9,13,26,29,30|RPI>3 和 CCS>0.8 阈值进入 SQL；RPI 具体计算式并未在该回复中给出。|26,30|HIGH
archeology_M_4|查环境知识及列含义后询问 ESI。先尝试较宽/聚合视图，失败后改为仅 zoneref、esi 的逐条视图，通过 Priority 时预算结束。|Priority 第3次提交通过；未观察到 Follow-up 工具调用。|8,11,12,14,15|采用用户 ESI 表达式与两位舍入，最后保留 zoneref/esi。|15|HIGH
archeology_6|读取多个不同网格/扫描知识后询问高保真阈值。生成站点聚合，提交失败后调整外关联/站点范围，再次提交。|用户给出的三条件已进入 SQL，Priority 仍未通过；不能简单归为未澄清。|16,17,18,20|高保真计数使用 MCR>5、facetresmm<1、geomdeltamm<0.5。|17,20|MEDIUM
credit_4|先查 CHS 和风险等级，询问信用分类到底采用什么。得到信用分段后执行查询，多次变更输出细节/排序重提。|分类已按用户给出区间实现，但 customers details 仍未明确收敛。|4,5,7,10,12|CASE 使用 Poor/Fair/Good/Very Good/Excellent 和 Unknown 区间。|5,12|MEDIUM
credit_11|探索 CES/季度及数字渠道知识后询问 digital natives 和高参与阈值。失败后进一步询问分组输出含义，再次提交。|首次把两个百分比视作冗余而删列，失败后补列并追问季度/分母；LEAST封顶来自已读CES定义。|11,14,18,19|采用 online/mobile 的 OR 加 autopay 条件；CES封顶来自T2知识定义，最终两个百分比的分母解释仍需核查。|12,19|HIGH
cross_db_3|先查高压力流量和多个效率知识，再询问 DTE 与 top。执行提交失败后检查流量 ID 及压力表达式，再次提交。|DTE 公式已澄清；flow ID 的列选择仍在反复分析，不能把失败归为 DTE 缺失。|12,13,14,18|使用 successpct/(errtally+1) 及 COALESCE/NULLIF，BSI 降序 LIMIT10。|13,18|MEDIUM
cross_db_M_4|读 Transfer Path 定义并查空值/跨境分布，再向用户确认国际转移和拼接。DDL 试执行被拒绝后提交，通过后直接提交路径计数。|用户回复明确了 transfer_path 列名，最终两个阶段通过。|6,7,9,10|采用非NULL且起讫不同条件和 ' -> ' 拼接，写入 transfer_path。|9,10|LOW
crypto_2|查 Order Fill Rate 与列含义，先自行选执行记录提交。失败后询问 recent 的排序含义，改为最高 orderexecmark，再提交仍未通过。|结束时剩0.5预算，未耗尽但不足一次提交标称成本；不能填 budget_exhausted=TRUE。|9,11,12|使用按 ordersmark 分组、orderexecmark DESC 选最新，以及用户确认的填单公式。|12|HIGH
crypto_M_2|根据 Effective Leverage 定义创建函数；DDL 试执行受限后直接提交并通过。Follow-up 尝试账户余额关联和风险分类，失败后更换查询细节。|未 ask_user；创建函数通过与后续余额/风险分类未通过需要区分。|4,5,8,13|无用户澄清；函数/分类定义被后续查询引用。|2,3,13|MEDIUM
cybermarket_M_4|询问缺失 TAS 公式后试算并提交写入，首次失败后再问列名和值域。Priority 通过，Follow-up 聚合市场可疑比例，调整排序后通过。|第二次澄清把写入列明确为 risk_category 及两个字符串；后续阶段也完成。|5,9,10,11,13,15|TAS 表达式和 risk_category='Suspicious Pattern'/'Normal' 进入更新与后续计数。|11,15|MEDIUM
cybermarket_M_1|先读多个供应商知识和全量定义，再询问 VTI 公式与有活动条件。提交失败后问列名并修改，继续提交仍未通过。|用户给定的 trust_index 名称已采用，失败原因仍未知，不能推断模拟器正确或错误。|7,11,12,13,14|使用 VTI 的成功率/争议率/评分表达式，仅更新 vendtxcount>0。|11,14|MEDIUM
disaster_2|读取多种不同灾害指标后询问缺失 OEI。执行公式并提交一次即通过 Priority，但此时预算已终止。|没有 Follow-up SQL，不能写成已经加 affected people 后失败。|24,25,26|使用运输成功率、交付小时和分配点数乘积，配合卓越标准。|25,26|HIGH
disaster_M_2|询问 EIF 后尝试物化视图、普通视图和 SELECT，多次未通过。随后才问 efficient storage 的语义和输出列，再回到物化视图提交。|存储形式在3次失败后才获得明确澄清；最终仍未通过。|6,9,10,11,12,13|最终使用物化视图和用户限定的灾害/环境ID、haztype、EIF及分类。|13|HIGH
fake_9|多次探索相关风险知识，依次询问 CPRI、SRS 依赖和 top。首次提交失败，补问 top 后改为按 CPRI 降序 top10，Priority 通过时预算终止。|Priority 澄清答 top10，而任务 Follow-up 写 these top5；记录存在数量衔接需核查。|14,15,17,19,21,22|SRS 权重、MAX/COALESCE、IP国家倍数及 LIMIT10 进入 SQL。|18,22|HIGH
fake_2|读取 Engagement Manipulator 定义后问 top 和记录保留。用户指定 LIMIT100/无排序/LEFT JOIN；Agent 在失败后变更关联与输出，最后重交相同 SQL。|最后提交与首次完全相同；是否恢复正确关联并不能由再次提交证明。|6,8,12,14|LIMIT100 与部分 LEFT JOIN 结构可见，正确保留记录的语义未确认。|7,14|MEDIUM
gaming_1|读取 IRS 与职业标准并检查原始值域，询问是否将9.0/9.5缩放为90/95。用户要求字面比较，之后在过滤与布尔标记间调整提交。|多次提交保留用户字面阈值，但没有通过；不能据数据值域直接否定澄清。|9,12,13,14|使用 joyprec>9.0、driftres>9.5，未乘10。|10,14|MEDIUM
gaming_2|查询电池分类与列含义并探查连接类型，询问无线范围和 BER。按回复生成指标和厂商内百分位，失败后调整分类边界/舍入，并重交相同 SQL。|末次提交与前次相同；BER 定义本身有明确利用证据。|11,14,16,17|无线匹配 Wireless/Bluetooth，BER=battlifeh×battcapmah/(pwractmw×10)。|12,17|MEDIUM
insider_4|查询网络模仿风险和两种调查指标，分别询问 Investigation Index 与 top。生成案件详情，失败后进一步检查筛选和关联再提交。|明确 III 和 top100 后仍未通过；PAS 的缺失定义未由这两问补齐。|9,10,12,17|III 使用0.6/0.4权重、两位舍入、降序 LIMIT100。|11,17|MEDIUM
insider_M_6|根据 Premature Resolution Block 知识创建触发器，试执行受限后提交通过。Follow-up 查询未解决但会被阻止的记录，后续改输出列再提仍未通过。|Follow-up 追加了分数等列；输出范围是否符合任务需人工核查。|7,9,11|无用户澄清；III>75 条件从知识进入触发器及 Follow-up 查询。|2,7,11|MEDIUM
mental_M_1|先按更严格风险标准探索并试算，之后向用户确认列名/标记。用户纠正为 risk_level='High Risk' 和较宽 OR 标准，Agent 修改并通过两阶段。|用户纠正了实际风险条件，后续落地且两个阶段通过。|12,14,16,17|使用 High/Severe OR PHQ>15 OR GAD>15，并写 risk_level。|13,16,17|LOW
mental_M_2|查一般 High-Risk 定义后询问 very risky 及审计表规格。用户给出更严格条件和表结构，Agent 验证 SELECT 后提交审计写入及分设施统计。|用户明确区分一般风险与更严格风险；两个阶段通过。|3,5,7,8|使用风险等级与症状严重度的组合，创建 high_risk_encounter_audit 并写入指定 reason。|7,8|LOW
museum_1|读取紧急保育与高价值定义，检查多表关联和百分位。询问 serious 状态后继续探索高价值范围，最后一次提交未通过。|已确认 Critical，但 top10% 与 percentile rank=1 的解释仍在推理中冲突。|10,13,18,19,20|使用 Critical 和 insured>1000000 或历史/文化评分双top-decile条件。|20|HIGH
museum_10|查 ERPS、阈值、DSD 和敏感度权重等知识，未问用户。探索关联与展示时长，首次未通过后改关联并再次提交。|知识公式被采用，但 display limit 和关联粒度是否匹配仍不确定。|2,3,4,14,17|无用户澄清；公式与权重在后续 SQL 可见。|14,17|MEDIUM
news_4|读取 USV/UDS 及权重定义，询问人口分组、最小规模及top数量。得到回复后生成聚合，失败后多次调整 shared interests 的处理。|回复解决分组和规模，shared interests 的并集/交集解释未单独澄清。|7,10,13,15|采用四维分组、五档年龄、COUNT>10 和 LIMIT15。|9,15|MEDIUM
news_M_4|获取 schema 后直接尝试创建 GIN 索引，受只读限制后提交通过。Follow-up 重交相同创建语句报已存在，随后 DROP+CREATE 指向 interests 并通过。|完全相同提交横跨两个阶段，第二次报索引存在；此重复不能无条件认定低信息增益。|1,2,3,4|无用户澄清；Follow-up 的 interests 路径落实为表达式索引。|4|HIGH
polar_M_3|查宜居条件与可靠性知识并探索数据，询问 slightly 的增幅。按1.15更新通过，Follow-up 用除1.15反推旧值并计算 EER，未通过。|Follow-up 旧值由当前值反算，而非保存的前值；误差或其他原因需核查。|9,12,14,15|采用 reliabilityindex×1.15；后续公式除1.15反算旧值。|12,15|MEDIUM
polar_M_4|查水资源指标及全量知识后询问 WRMI。提交失败后在原始水位和除100水位之间切换，补问 relevant equipment 只获范围回复，最后再采用除100版本。|最终 SQL 对 waterlevelpercent 额外除100，与已收到公式存在明确表达式差异。|12,14,17,18,19,20|曾采用用户公式；最终额外归一化，第二次回复未回答该归一化问题。|14,19,20|HIGH
robot_10|查 OCE、周期与多个机器人指标后，集中询问指标、低效、样本规模和top。首次未通过后再问 JSON/列结构，并重复查一个知识条目，再提交。|第二次回复明确 JSON 仅两个键；结构已调整但仍未通过。|14,20,21,22,24|采用 per-robot/program OCE、低效阈值、至少5机器人及top50；JSON包含指定两键。|20,24|HIGH
robot_8|查询 EER 与机器人活动知识后，询问 poor energy、rank及top。用户给出阈值后再查对应定义，生成 Priority 及按类型计数 Follow-up，均通过。|澄清将候选最低EER/过载解释纠正为明确阈值，两个阶段通过。|8,9,11,13|使用 EER>0.01、TOH>1000、top100，Follow-up 保留筛选。|10,13|LOW
solar_6|查系统损失和逆变器相关知识，询问 IEL 公式并获得确认。执行并提交后，补查列含义，改变输出/关联又提交两次。|IEL 已明确采用，仍未通过；不能把剩余失败直接归为公式缺失。|11,14,15,17,18|采用 measuredpower×(1-inverteffpct/100)，且取值自 power_metrics。|12,18|MEDIUM
solar_10|先查电网质量知识与 JSON 含义，询问 GIQ。Priority 通过，Follow-up 聚合top3厂名，尝试不同拼接/排序后仍未通过。|Follow-up 有一次完全相同的 execute_sql；多次提交围绕字符串聚合变化。|6,8,10,12,13,14|采用 pwrqualidx×(1-harmdistpct/100)×invertpowfac，并在后续 AVG 中保留。|7,14|MEDIUM
vaccine_M_2|根据 TSS 定义创建监测表/写入，失败后查列含义并询问 last_updated 的时间来源。改为 NOW 后继续改表结构和插入方式，均未通过。|时间戳已改为用户规定的 NOW，但最后版本不再显式挑最新传感记录；需人工核对。|7,10,11,13,14|采用 NOW 作为更新时间；其余 latest 语义并未因此确证。|11,14|HIGH
vaccine_6|查温度报警相关定义和列含义后，询问缺失 TBS。先按容器聚合提交未通过，调整为传感记录及关联警报数组后通过 Priority 时预算终止。|粒度修改后 Priority 通过；未观测到 Follow-up 添加当前温度。|11,14,18|采用 ABS(tempnowc-storetempc)/NULLIF(temptolc,0)×tempdevcount 和阈值。|12,18|HIGH
virtual_M_5|先查 creator 知识并询问枚举等级；多次创建未通过后再问名称与已有类型处理。采用幂等 content_creator_type 后通过 Priority，Follow-up 加列未通过。|名称及幂等语义的第二次澄清改变了 DDL；Follow-up 加列有提交但未通过。|5,8,9,10,11,12|使用三项枚举、content_creator_type 名称及存在检查。|11,12|MEDIUM
virtual_1|读取礼物支持者与成员知识后询问 gift score 和 lower-tier。执行并按回复提交，通过后将花费阈值从100改为20，两个阶段通过。|用户澄清排除了 tierstep 解释，并明确 GIQ，后续 SQL 可定位采用。|10,14,16|使用 giftvalusd×gifttot/100、Free/Basic、GIQ>50，Follow-up spendusd<20。|13,16|LOW
'''
NOTES={}
for line in ROWS.strip().splitlines():
    tid,story,finding,refs,use,use_refs,priority=line.split('|')
    NOTES[tid]=dict(story=story,finding=finding,refs=[int(i) for i in refs.split(',')],use=use,use_refs=[int(i) for i in use_refs.split(',')],priority=priority)

# 每次询问的人工摘要，顺序严格对应各任务 ask_user 的工具索引。
QA = {
'alien_7':['询问良好观测阈值；答复为 AOI>0.85 加月相、距离、太阳条件。','提交失败后问 JSON 键；答复 station/aoi/is_optimal_window。'],
'archeology_1':['问 scan quality 指标；答复 SQS，非列出的候选。','知识查询未找到 SQS 后问精确公式；答复 LOG/POWER、覆盖率及噪声组合。'],
'archeology_9':['问 extraction efficiency；答复 FEE，并涉及点云密度比。','问 FEE 公式及聚合；答复 (traits+artifacts)/(PCDR×sqrt(clouddense))×1000 和按站点平均。'],
'credit_8':['问债务指标和 few customers；答复平均DTI、TDSR、中位DTI及排除≤10人组。','查不到租金列后问替代方式；答复 JSON rentpayment，空值 COALESCE 为0。'],
'credit_M_6':['问新增列名和 FSI 公式；答复 fsi NUMERIC(5,3) 及四项加权公式。'],
'cross_db_5':['问路径呈现与排序；答复单列 Origin -> Destination，按合规 ID 升序。'],
'cross_db_4':['问缺失 SRS；答复 EncState/AclState 的3级 CASE，同时补充 DSI>100/SRS<2。','问 Critical 的 DSI 权重；答复按 ELSE=1，但同时反问是否要其他权重。'],
'crypto_3':['问 PVaR 与 top few；答复 possum×volmeter×0.01，按 pivot 降序取5。'],
'cybermarket_2':['问 trustworthy 及 details；答复 VTI>80、检查等级/争议率/天数条件及三列详情。','提交失败后问输出和舍入；答复四列、market别名、不舍入、VTI降序。'],
'cybermarket_1':['问 suspicious chains/risk/top；答复纠正为 TCR 公式与钱包筛选，按TCR降序。'],
'disaster_3':['问 EIF 缺失公式；答复碳排放调整项加回收惩罚，保留2位。'],
'disaster_7':['问 CEE 及社区分类；答复 BSI/参与度/满意度公式和3类规则。'],
'fake_8':['一次问 reach、阈值和top；只答 reach=netinflscore，要求其余另问。','再问阈值；答复 netinflscore>80、postfreq>30，并补充top10/排名。'],
'fake_1':['一次问 BBI/过滤/top；只答按平均BBI降序取100，未确认BBI映射。'],
'gaming_7':['问 DS 字段/公式和 high endurance；答复 DS 公式、IPX映射、PER>9。','提交失败后问 registry ID 应选哪个；回复 out of scope 拒答。'],
'gaming_M_4':['问 AQI 和 poor quality 条件；答复 AQI 公式及四条件 OR。','问应展示删除还是剩余记录；答复被删记录及3个输出字段。'],
'insider_8':['问 fast movers/OMI；答复不加额外快交易过滤，OMI=modfreq/(1-cancelpct)。'],
'mental_9':['问 RDD 和 prevalence；答复 PFIS−FRAI、SRP>20%。'],
'mental_1':['同时问 urgent-risk 标准和 TES；只答 High-Risk 的 OR 条件，未给 TES。'],
'museum_M_4':['问评分允许范围；答复1到10含边界。'],
'polar_5':['问 WRMI 公式；答复水位×水质/100×(1-废水/100)。','问 classification/management情况；答复分别为 WQCS/WRMSC，均依据组均值。'],
'polar_7':['问 ESI 是否效率/100或需能源权重；答复效率原值乘电源倍率。'],
'robot_M_3':['问维修优先级规则；答复 WFPS/MRUL 的 CRITICAL/WARNING/NORMAL 阈值。','问时间戳与建表方式；答复 current_timestamp、CREATE IF NOT EXISTS 和upsert。','问确切列名；答复 robot_id/priority_level/calculated_wfps/calculated_mrul/last_updated。'],
'robot_6':['问平均严重度/top；答复平均toolwearpct、top100、TWR再TPC降序。'],
'solar_4':['问 MCE；答复维护/清洁/更换成本之和除容量，按厂聚合。'],
'solar_3':['问 temperature impact；答复 TPCI=功率×系数×(温度−25)，按面板类型平均。'],
'vaccine_7':['问 CDR；答复(100-coolremainpct)/(CURRENT_DATE-refilllatest)，排除空refilllatest。'],
'vaccine_2':['问 sensor data status；答复是否存在匹配传感器记录的可用性标记。'],
'virtual_6':['问 risk score/grouping；答复 RRF，按churnflag分组。','追问 RRF 权重；答复2×不一致度+0.5×距登录月数+风险等级数值。'],
'virtual_M_4':['问 at risk 标准；答复 Churn Candidate 三条件，而非仅churnflag=High。'],
'alien_8':['问 narrowband/调制过滤；答复 BFR+漂移阈值，不加调制类型过滤。'],
'alien_6':['问 important 指标；答复 RPI>3，promising 还需CCS_approx>0.8；未给RPI公式。'],
'archeology_M_4':['问 ESI；答复温湿光照公式、2位舍入和zoneref/esi。'],
'archeology_6':['问高保真网格阈值；答复 MCR>5、分辨率<1、几何偏差<0.5。'],
'credit_4':['问信用分类；答复 credscore 的五档区间，其他为Unknown。'],
'credit_11':['问 digital natives/高参与；答复 online或mobile为High且autopay=Yes，CES>0.7及公式。','问输出/季度/分母；答复完整季度时间、两个百分比列及组内count。'],
'cross_db_3':['问 DTE/top；答复successpct/(errtally+1)带保护，BSI降序top10。'],
'cross_db_M_4':['确认跨境范围与路径拼接；答复非空且起讫不同，写入transfer_path。'],
'crypto_2':['失败后问 recent 记录及填单式；答复最高orderexecmark、(dealcount-remaincount)/dealcount×100。'],
'cybermarket_M_4':['问 TAS 替代指标；答复明确TAS公式，否定TVM/fraudprob。','问风险列名和值域；答复 risk_category，Suspicious Pattern/Normal。'],
'cybermarket_M_1':['问 VTI 能否用VRS及活动范围；答复独立VTI公式，仅vendtxcount>0更新。','问列名；答复trust_index。'],
'disaster_2':['问 OEI；答复运输成功率×时间项×分配点项、2位显示和卓越条件。'],
'disaster_M_2':['问 EIF；答复碳排放与回收公式，2位及分类。','问 efficient storage/列；答复物化视图，灾害ID/haztype/环境ID/EIF/分类。'],
'fake_9':['问 cross-risk/活跃群；答复CPRI，采用高活动的OR条件。','问 CPRI 公式；答复SRS×(1+0.2×IP国家数)。','追问 SRS；答复0.4风险+0.3(1-信任)+0.3影响的MAX/COALESCE。','失败后问top；答复CPRI降序top10，非全部483个。'],
'fake_2':['问top/记录保留；答复LIMIT100、无排序、LEFT JOIN保留相关记录。'],
'gaming_1':['问9.0/9.5是否缩放；答复直接按原列值比较，不缩放。'],
'gaming_2':['问无线范围/BER；答复匹配Wireless/Bluetooth，BER=寿命×容量/(功耗×10)。'],
'insider_4':['问两种 Investigation Index；答复III，0.6/0.4权重并保留2位。','问top数与排序；答复III降序top100。'],
'mental_M_1':['问标记列名和值；答复risk_level/High Risk，并纠正为更宽OR风险条件。'],
'mental_M_2':['问very risky/审计表；答复严重风险AND症状条件，以及表名、列和reason。'],
'museum_1':['问serious状态；答复仅Critical，同时补充高价值条件。'],
'news_4':['问人口特征/组规模/top；答复订阅、性别、职业、年龄5档，>10人，top15。'],
'polar_M_3':['问slightly增幅；答复可靠性乘1.15。'],
'polar_M_4':['问WRMI；答复水位原值×水质/100×废水调整及分类。','问relevant设备/列/归一化；只答有非空waterlevelpercent记录的所有设备。'],
'robot_10':['问OCE/低效/规模/top；答复分机器人程序聚合、OCE<100且TPC>500000、至少5机器人、top50。','问输出结构；答复平均OCE、JSON仅两个键、程序数及低效数单独列。'],
'robot_8':['问poor energy/rank/top；答复EER>0.01且TOH>1000、最差rank聚合、top100。'],
'solar_6':['问IEL公式；答复确认measpoww×(1-inverteffpct/100)，来自power_metrics。'],
'solar_10':['问grid quality；答复确认GIQ三因子公式。'],
'vaccine_M_2':['问last_updated来源；答复NOW，alerttime只用于挑最新传感记录。'],
'vaccine_6':['问TBS；答复绝对温差/容差×偏离次数、除零保护、阈值与降序。'],
'virtual_M_5':['问creator等级；答复三项creator枚举值。','问名称/处理已有类型；答复content_creator_type、仅不存在时创建。'],
'virtual_1':['问gift score/lower-tier；答复GIQ公式和Free/Basic，非tierstep。'],
}
# 仅候选分类；原始记录没有保存模拟器 action-parser 分类。
LOC_CANDIDATES={('cross_db_4',11),('gaming_1',9),('gaming_M_4',13),('cybermarket_2',10),('alien_7',15)}
# 不完整答复或拒答，独立于 AMB/LOC/UNA 标签。
PARTIAL={('fake_8',16),('fake_1',9),('mental_1',34),('polar_M_4',18)}
REFUSED={('gaming_7',9)}
