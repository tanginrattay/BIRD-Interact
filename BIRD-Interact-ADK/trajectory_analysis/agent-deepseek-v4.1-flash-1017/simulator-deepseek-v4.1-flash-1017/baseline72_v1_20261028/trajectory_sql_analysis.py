"""研究者附录：只读参考SQL的静态对照，不执行数据库或重新评分。"""

def failure_analysis(task_id,ref):
    if task_id=='polar_M_4':
        return f'''### 失败分析：最后提交 T20 与 Priority Ground Truth

**结论：主要错误首先是没有创建要求的视图，其次是 WRMI 公式被额外除以100。** 最后提交是 {ref('T',20)}；Priority未通过，Follow-up未进入，因此不把最后SQL与Follow-up参考答案混比。

|比较项|Ground Truth|Agent最后提交|判断|
|---|---|---|---|
|操作与对象|`CREATE OR REPLACE VIEW water_management_view AS ...`|只有`SELECT`，没有创建视图|明确任务操作缺失；返回结果集不能替代持久化视图|
|WRMI|`waterlevelpercent * (waterqualityindex/100) * (1-wastetanklevelpercent/100)`|第一个因子变成`waterlevelpercent/100`|在同一行上，Agent分数为GT的1/100（忽略浮点误差）|
|分类|用GT原分数与0.5、0.7比较|对缩小后的分数仍用0.5、0.7阈值|可改变状态分类；不仅是数值显示单位不同|
|视图输出接口|3列：`watereqref, wrmi, management_status`|4列：`equipmentcode, equipmenttype, water_management_score, status_category`|既未建立视图，也未提供约定的列接口；多出equipmenttype|
|数据来源|直接`waterandwaste`，过滤非空水位|额外INNER JOIN equipment，过滤非空水位|静态范围不同；是否实际丢行需数据验证，不能凭SQL文本断言|

**原记录已有直接数值证据：** {ref('T',13)} 使用原公式时，`PE100466`的分数为`17.691362845092772`，状态`Sustainable Management`；{ref('T',16)}改成除100后为`0.1769136284509277`，状态`Conservation Needed`。这证明该变更确实影响已观察样本的分类。最终{ref('T',20)}沿用了该归一化版本。

**测试实际要求：** [原始test_cases][gt-tests]会执行提交后查询`SELECT * FROM water_management_view`，并检查首条记录的设备引用、WRMI和状态。GT中首条期望值包括`PE593707`、`270.8554904382706`、`Sustainable Management`。最后提交没有任何建视图语句，也不满足其分数定义。日志只返回通用“Your SQL is not correct”，没有保存具体测试异常，不能声称已看到某条断言或“视图不存在”异常。

**为什么这不应简单归因于“用户信息没用”：** 用户在{ref('T',12)}给出了正确公式，Agent最初确实采用；{ref('T',18)}又询问设备范围、输出及是否归一化，但回复只解释了设备范围，没有补全应创建的视图名称/列接口。此后{ref('T',19)}一度恢复原公式，最后又改回除100。可确认的是规格未落实及已获公式被改写，不是完全未使用回复。

`ORDER BY equipmentcode`和普通结果列别名本身不是这里的首要问题；视图对象/列接口在这个Management任务中具有实际用途。以上为静态与已记录样本对照，没有执行GT或重跑测试。
'''
    if task_id=='credit_11':
        return f'''### 失败分析：最后提交 T19 与 Priority Ground Truth

**结论：最终SQL最明确的偏差是将GT的0–1比例乘100；此外，CES封顶、缺失JSON过滤和多余关联也与GT不同。** 最后提交是 {ref('T',19)}，仍处于Priority；Follow-up未进入。

|比较项|Ground Truth|Agent最后提交|影响及确定性|
|---|---|---|---|
|两个高参与率的单位|`COUNT(...)::float / COUNT(...)`，不乘100|两列均为`100.0 * SUM(...)/...`|明确100倍量纲差异；相同计数下GT返回0.13，Agent返回13.00|
|CES公式|直接使用原始produsescore、chanusescore、bankrelscore及custservint/10|每项加`LEAST(...,1)`|明确表达式差异；超1分量会改变CES、平均分及是否>0.7，实际改变量需原始数据|
|人群过滤|`WHERE bt.chaninvdatablock IS NOT NULL`|没有对应WHERE|可额外纳入JSON为空的客户；是否存在这些行不能从现有计数确定|
|关联范围|core_record→credit_accounts_and_history→bank_and_transactions|还串联employment_and_income、expenses_and_assets、credit_and_compliance|可能改变保留行或重复倍数；{ref('T',17)}仅统计各表各1000行，并不验证连接后是一对一且全覆盖|
|季度|`DATE_TRUNC('quarter', scoredate-tenureyrs*INTERVAL '1 year')`|`DATE_TRUNC(... (tenureyrs || ' years')::interval)::date`|最终已保留年份和季度起点；常规整数年下主要是写法/类型差异，不应继续把“只取季度号”当最终错误|
|平均与比例舍入|AVG和两个比率不写ROUND|平均4位、比例2位|SQL文本不同；当前默认评测会先去掉ROUND，不宜单独据此解释失败|
|第二个比率的分母|当前季度+digital-first分组内的digital-first人数|最终也是当前组内的digital_native人数|这一部分最终与GT相符；非digital组分母0经NULLIF返回NULL，不是漏写窗口函数|
|排序/别名|布尔值DESC，别名为is_digital_first等|布尔值默认ASC，别名不同|该任务conditions未要求顺序；默认评测比较行值集合，普通别名及组间排序差异不作为本次主要原因|

**比例差异有可观察背景：** {ref('T',13)}的试执行已出现`13.01`、`12.63`等百分数，说明Agent确实沿用0–100呈现思路；最终{ref('T',19)}仍保留两处`100.0*`。这些不是GT在相同客户集下已实际执行出的值；CES与筛选也不同，不能把它们直接除100就当成本批GT结果。

**CES存在知识定义与参考SQL不一致：** {ref('T',2)}的知识定义明确写了“each component is capped at 1.0”；{ref('T',11)}用户回复给出权重但没有重述封顶。Agent的LEAST有已读知识依据，而GT未封顶。因此这是“与GT计算不同且知识/GT口径存在冲突”，不能简单定性为Agent凭空篡改公式。比例单位错误则可独立识别，不依赖这一冲突。

**推理文本与最后行动也要分开：** A25最后考虑按整个cohort做窗口汇总，但T19实际上没有窗口函数；与GT对照后，最终组内分母反而符合GT。因此“没有执行先前窗口计划”不是本题SQL错误的充分证据。

**评测边界：** [默认比较实现][gt-evaluator]会移除ROUND、将数值归一处理后比较结果；它不会把0.13与13自动视为同一个比例。现有反馈未给逐项差异，没有离线执行GT来量化每一项造成的行数/数值变化，也不声称修正某一项即可通过。
'''
    if task_id=='disaster_3':
        return f'''### 失败分析：最后提交 T15 与 Priority Ground Truth

**结论：最后SQL漏掉了输出列`d.distregistry`（灾害ID）；这是明确的结果结构错误。** 最后提交是 {ref('T',15)}。Priority未通过，Follow-up没有进入。

|比较项|Ground Truth|Agent最后提交|判断|
|---|---|---|---|
|输出列|6列：环境ID、灾害ID、地区、灾害类型、EIF、分类|5列：环境ID、地区、灾害类型、EIF、分类|漏掉第二列`d.distregistry`；非空结果的5列行不能与6列GT行相等|
|关联粒度|environmentandhealth JOIN disasterevents|同一关联与条件|最终没有额外operations关联，与GT一致；不能把“没关联operations”当最终错误|
|EIF公式与显示|碳排放可再生调整项+回收惩罚，ROUND到2位|相同表达式与2位舍入|已采用正确的用户公式；不是EIF主体公式错误|
|分类比较|用未ROUND的EIF比较50、100|用ROUND(EIF,2)比较50、100|SQL语义有边界差异；但默认评测先移除ROUND，该差异不能直接解释记录中的判错|
|排序|EIF升序|EIF升序|一致|
|结果别名|environmental_impact_factor、sustainability_assessment|environmental_footprint_factor、category|普通别名不同；默认比较行值，不按别名判错|

**列数错误可直接复核：** GT的第二个SELECT表达式是`d.distregistry`；T15从`e.envhealthregistry`直接跳到`d.affectedarea`。{ref('T',14)}的最小版本试执行已返回5列表头，最终提交仍沿用这一输出结构。中间{ref('T',13)}虽加了`o.opsregistry`，那是行动/operation ID，并不是GT要求的灾害ID，不能替代`d.distregistry`。

**为什么Agent会围绕别处反复修改：** 对Agent可见的初始歧义问题没有明确列出灾害ID；{ref('T',7)}仅询问EIF公式，回复也没有补充完整输出列要求。失败后的公开说明主要猜粒度、别名和排序，没有拿到具体的缺列反馈。这解释了它为何仍有输出规格缺口，但不能据此断言某个单一策略必然导致失败。

**分类边界的静态差异举例：** 若原始EIF为49.996，GT按未舍入值分类为Sustainable，而原样执行Agent SQL会先舍入到50.00，分类为Moderate Impact。这只是数学反例，不表示本批数据确有该行；且[默认评测][gt-evaluator]对两边SQL移除ROUND后再比较，因此不将它列为此次确定的判错原因。

当前证据足以确认缺列是结果不等价的直接原因；没有重新执行GT，也没有验证“仅补灾害ID”后是否还存在其他数据相关差异。
'''
    raise KeyError(task_id)
