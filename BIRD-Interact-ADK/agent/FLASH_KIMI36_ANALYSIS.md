# Flash 36条结果与历史Kimi 3对照分析

> 交接文档更新：2026-10-09。运行与原分析日期：2026-10-04；本次仅整理文档，没有重新运行模型、SQL或服务。
> 用户已决定后续使用Flash；`.env`已切回`deepseek/deepseek-flash`。运行中的服务是否已加载该配置须检查6000 health，不能由`.env`推断。原Moonshot配置与密钥保留为注释。
> 本文件保留完整诊断结论和36条任务标注；原始统计与问答附件仍在`results/analysis_flash_vs_kimi36_20261004/`。


结论：两者有稳定重现的任务难点，尤其是指标/统计粒度选择、澄清后约束未完整落实、输出契约不完整，以及粗粒度失败反馈下的无依据修订。Flash的主要运行问题是过度知识探索后耗尽预算；历史Kimi的另一突出问题是仍有预算却没有继续提交。Qwen simulator调用链正常，但存在公式回答不完整和至少一条明确公式错误，不能按“无API错误”认定语义质量合格。另发现空结果评测缺陷及若干文字/参考SQL冲突，应从模型失败中区分出来。

本报告静态检查了Flash全部36条、47次ask_user尝试（46条真实回复），以及Kimi保存完整轨迹的32条；未调用付费API、未重跑SQL、未改动agent/simulator/评分逻辑。原始工具结果本身有2000字符截断；没有模型finish_reason、完整token用量或账单数据。下文将静态SQL差异、明确代码缺陷和未复测候选原因分开表述，不将每个差异都声称为唯一失败原因。

## 1. 范围、成绩与可比性

两轮任务清单、顺序相同。历史Kimi最初4条alien_11、alien_7、archeology_1、archeology_9只有零分日志，没有完整P1/P2字段和轨迹；不能用Flash轨迹回填。全36条Kimi的12/36、9/36是依据四条reward=0推断其未通过，下面另给可严格核对的共同32条。

| 范围 | Kimi 3 P1 | Flash P1 | Kimi 3 P2 | Flash P2 | Kimi / Flash平均reward |
| --- | ---: | ---: | ---: | ---: | ---: |
| 全36条（Kimi4条由零分推断） | 12/36（33.33%） | 11/36（30.56%） | 9/36（25%） | 6/36（16.67%） | 0.3083 / 0.2639 |
| 共同32条完整轨迹 | 12/32（37.50%） | 10/32（31.25%） | 9/32（28.13%） | 6/32（18.75%） | 0.3469 / 0.2750 |

Flash36条为6条两阶段通过、5条仅P1通过、25条P1未通过。P1成功后P2通过率为6/11（54.55%）；共同32条是6/10（60%），Kimi是9/12（75%）。P2差距既包含进入P2的任务差异，也包含剩余预算、follow-up语义和数据问题，不能只解释成“Flash多轮记忆更差”。

历史system agent为moonshot/kimi-k3，使用当时默认推理配置，不能标成后来加的K3-low；simulator为Kimi K2.6。Flash为deepseek/deepseek-flash、显式非思考模式，simulator为Qwen 3.7 Plus单阶段非思考。两者均concurrency=1、patience=3，但日期为2026-09-29/2026-10-04，CURRENT_DATE任务会受时间影响，代码/依赖也不能假设完全一致。因此，这是同任务的行为诊断对照，不是只更换system model的消融，也不是模型总体能力排名。

## 2. Flash主要在哪些地方出错

### 2.1 已获得部分正确信息，却没有完整落实

- credit_8：Qwen拒绝错误候选，明确TDSR需要DTI加住房成本并区分Own/Rent。Flash最终使用mthexp，且总计用分组均值/中位数再平均，排序、总计名称和连接类型也偏离。实际首先报enum转换错误，因此这是SQL执行错误和语义错误并存，不应只算其中一项。
- fake_8：Qwen明确“network influence score，不是NIC”，最终显示的是该分数，但influence_rank仍按NIC。即展示列修正了，排序/排名计算没有同步修正。
- alien_7：P1已经正确实现OOW；P2只添加新AOI阈值、Quiet和SDS排除，却丢掉原有月相、月距、太阳状态条件。这是已完成查询在局部变更时丢旧约束的直接案例。
- cross_db_5：修复时曾切到compliancetrace，最后又把输出ID改回recordregistry。disaster_3首版EIF公式和升序基本正确，后续无证据扩大连接、反转排序；vaccine_2最后连续两次提交相同SQL。

这些支持研究“带来源的意图状态、提交前覆盖检查、限制无依据语义变化”，而不是简单增加思考长度。并非所有simulator回复都可信，因此状态应保留来源及冲突，不能把每条用户回复永久当真理。

### 2.2 只澄清一个槽位，查询的其他要求仍是猜测

- crypto_3：两者都能获得PVaR乘0.01的正确公式，但都用orders/marketdata取多条关联波动率，GT是全局最新单条波动率；排序范围也不符。公式正确并不等于人口/范围正确。
- cybermarket_2：Qwen这次完整给出四个Trusted Vendor过滤条件，Flash全部落实；但三次提交仍SELECT大量列或SELECT *，缺要求的市场名称及连接。失败从“过滤+输出”转为“输出”，问得正确仍未解题。
- vaccine_2：两者几乎只澄清sensor data status，然后都用原始tempstabidx代替复合TSS，漏critical筛选和一年窗口。得到一次好回复不等于查询已确认完整。
- polar_5：Qwen给出的WRMI正确，Flash保持了公式；但两次都按station/location排序，没问排序。缺ROUND不是独立评分原因，因为当前评分预先移除ROUND。

### 2.3 指标缺失后，穷举知识、猜公式

Flash单项知识查询345次；有6条各查至少20次：archeology_9、fake_8、gaming_7、insider_8、mental_9、mental_1。任务会故意删去知识定义，这不是必然能靠更多lookup解决的问题。

- mental_9：32次单项查询消耗16 coins，到0.5 coins才ask，callback阻断，simulator根本没收到；最后猜出RDD复合比值，而GT是PFIS−FRAI。
- gaming_7：28次查询、一次ask都没有，最终DS用usbconndur/1000而非drop/bend/twist/usb组合。
- insider_8：23次查询，已经查OMI返回not found，却只问群体定义，没有问OMI；最后AVG(modfreq)。Kimi问了OMI公式和统计范围，此题两阶段通过。
- archeology_1：agent确实问了SQS公式，但Qwen没有给计算表达，只让用standard definition，Flash随后编造公式。这里simulator与agent都参与了失败链。

### 2.4 聚合、输出与管理操作契约

news_9：首版INNER JOIN忽略无交互推荐；Flash修成LEFT JOIN后又改成DISTINCT推荐/交互计数，统计分母仍不同于参考连接行计数。fake_1/fake_8把platform ID当cluster，也有粒度问题；GT按clustsize统计是否符合实际cluster本身也值得审查。

museum_M_4：CHECK范围正确但四次约束名不对。实际test_case硬检查hist_sign_rating_check，模糊请求不提供名字，Qwen只答范围；历史Kimi回复额外给了名字。普通查询列alias不是主要解释，但DDL对象名确实是硬契约。

robot_M_3：多轮才问清table/columns；最终仍缺UPSERT且采用real。test_case更新原始fault数据后再次执行pred SQL，验证可重复更新，纯INSERT遇现有主键必失败。real精度与1e-9容差也存在潜在冲突。只是generic fail，不能仅由日志确定每次到底先在哪个assert失败。

gaming_M_4/virtual_M_4：删除遇外键约束。GT使用session_replication_role=replica关闭触发器，Flash不断扩大级联删除范围或直接失败；这是管理操作环境协议与语义问题共同作用，不能全归因于“模型不会DELETE”。

### 2.5 不是Flash没有执行到最后，而是把预算花在不合适的地方

Flash36条全都有submit_sql；未完成的30条最终全部是Budget exhausted，0条“未完成且剩余至少3 coins”。71次提交中，17次通过、49次generic结果不正确、5次明确SQL执行错误（credit_8一次、gaming_M_4三次、virtual_M_4一次）。失败多数不是语法崩溃，而是SQL运行后输出/状态不符；generic错误也可能包含评分异常，不能把49次一概视作纯模型语义错。

P1成功但P2失败的5条：alien_7剩4.5、polar_7剩1、robot_6剩2.5、solar_4剩7.5、solar_3剩10.5 coins。后两条起初还有较多预算，P2失败不能一律称为“没留够提交预算”。代码允许预算不足时一次免费退出提交，因此0预算结束不是“根本没有尝试P2”。

## 3. Qwen simulator是否正常工作

### 3.1 运行链路正常，语义只能评为部分合格

47次ask_user尝试中，mental_9的一次被预算拦截；实际46次调用都有非空回复及对话记录，没有固定fallback、401/500/超时或“无法连接”的回复。46条真实回复均在P1，Flash没有P2 ask；当前phase_transition只换reference_sql、保留P1 clear_query的风险存在，但本轮Flash没有触发这条回答路径，不能据此解释其P2失败。

逐条定性审查：37条按所问问题基本有效、2条明确要求公式却回答不足、4条不完整、1条top10/GT并列边界待审查、1条明确错误、1条误导/不完整。该标注是人工诊断口径，不是盲评得出的simulator准确率；“37有效”不意味着37条覆盖了全部隐藏意图。

### 3.2 正常工作的证据

- archeology_9：拒绝错误PCDR/FEE候选并给出正确公式。
- credit_8：拒绝把TDSR当DTI或一般支出比，纠正房主/租客。
- cybermarket_2：完整说明四个Trusted Vendor条件，优于历史Kimi simulator漏争议率和运营天数的回复。
- mental_1：拒绝RDD/attrition和TES<1.5的错误前提，正确改成Severe Environmental Stress或Severe Life Impact、平均TES<2。
- polar_7：明确拒绝分类标签，要求数值ESI，随后给正确乘数，P1通过。

这些表明它不是只顺从agent选项，且能提供实质澄清。

### 3.3 需要关注的真实语义问题

1. **virtual_6公式错误**：GT为2*(1−intconsist)，Qwen说“两倍交互一致性的倒数”，Flash写2/intconsist并除零，随后加NULLIF保持了错误公式。这是明确的simulator→错误SQL链，不应全部归因于agent。
2. **archeology_1公式不回答**：SQS定义被删除，仍要求用standard definition。cybermarket_1第二次问TCR公式也只得到成分，第三次才给权重。配方缺失会增加交互成本并诱发猜测。
3. **fake_1等不完整回答**：仅说BBI包含哪些成分，未给权重/反向项；crypto_3没有纠正按notional排序的提问前提；credit_8说monthly mortgage payment，没有讲GT的mortgage balance/12，存在概念与具体实现的不一致。
4. **virtual_M_4回答误导**：最后称“原请求给过公式”、复合分数包含engagement；明晰原请求没有给公式，GT中engagement是另一个筛选条件。它没有帮助消除agent对RRF/复合得分尺度的混淆。

原prompt同时要求“能给概念公式”与“拒绝SQL/实现细节”。混合提问把列名、公式、需求一起问时，很容易得到不完整回复，应明确区分业务指标定义与SQL实现。新建列/表/约束名以及用户输出JSON键，属于任务输出契约；不应和泄露既有数据库schema机械混为一谈。是否允许讲内部对象名也需固定统一口径，避免一个simulator多说便产生不公平优势。

## 4. 共同失败中还存在评测/数据问题

### 4.1 空结果会无条件失败，是已确认的代码问题

shared/db_utils.py::ex_base包含 `if not pred_res or not gt_res: return 0`。因此预测与GT同时合法为空也不可能通过；default evaluator还先移除ROUND和DISTINCT、按默认2位小数预处理，不能单凭ROUND/DISTINCT文本差异解释失败。

- vaccine_7：历史记录显示900条容器的RefillLatest均在2025-02-09到2025-02-19，CURRENT_DATE是2026-09-29；本轮是2026-10-04。所有CDR均低于1，参考critical查询应为空；两者自己的CURRENT_DATE查询也实际为空。Kimi提交此版本仍被判错，然后改固定日期。空GT使该任务在当前评分代码下不可通过。
- solar_3 P2：Flash轨迹直接记录today=2026-10-04、cnt_current=0、cnt_max=11。按GT“近三个月”参考查询为空，评分同样必失败。两者随后用MAX历史日期替now并有其他粒度变化，确实偏离意图，但其初始挫败来自不支持空结果的环境。

这里无需重跑模型即可确认代码与轨迹证据。没有修改历史分数，也没有为了提高分数删除样本；应在后续实验中记录问题并统一决定修复或协议，不能把这些共同失败当作模型能力上限。

### 4.2 文字/参考SQL冲突

- solar_4 P2只说MCE>100，GT却从plant级改为panel type级。这是两者P1成功/P2失败的共同干扰。
- polar_7 P2只要求ESI/WRMI并列显示，GT却把已确认ESI和另一个WRMI各归一化缩小100倍；不能要求模型默默推断。
- robot_6的latest estimated fault type对应GT先过滤非NULL，再按upkeepduedays选；Flash没过滤NULL，是候选差异，未重跑确认唯一根因。
- fake_8的top10 accounts与GT dense-rank<=10/limit100并列边界、fake_1按clustsize定义cluster、archeology_9的all sites文字与后续INNER JOIN，都不适合直接当作清晰无歧义标准任务。

## 5. Kimi 3与Flash是否有共同趋势

共同32条的P1交叉结果：8条都成功，18条都失败，4条只有Kimi成功（crypto_M_4、insider_8、museum_M_4、robot_M_3），2条只有Flash成功（polar_7、robot_6）。P1成功/失败一致率26/32=81.25%；这不等于失败原因一致，需读轨迹。

Flash的6条P2成功全部也是Kimi成功任务：credit_M_6、cybermarket_1、disaster_7、insider_M_5、museum_6、news_M_1。共同成功多为能从有效澄清获得明确公式/对象，且后续改动直接的任务。

共同失败的具体机制：

| 共同任务 | Kimi表现 | Flash表现 | 支持的共性 |
| --- | --- | --- | --- |
| credit_8 | 已知Own/Rent，但只实现mortgage分支 | 已知Own/Rent，却用mthexp | 正确澄清未完整落实 |
| crypto_3 | pivot升序+多条market volatility | notional降序+多条market volatility | 公式对了，范围与排名不完整 |
| cybermarket_2 | simulator漏条件，SQL输出也不对 | simulator条件完整，SQL仍输出不对 | 查询投影/输出契约是独立难点 |
| disaster_3 | 正确EIF仍漏disaster ID | 相同缺列，后续反转排序 | 失败修复不检查全体输出要求 |
| fake_8 | 正确network score，但cluster/rank不符 | 还保留已被否定NIC排名 | 指标与统计粒度/排名没有同步 |
| news_9 | INNER JOIN漏未交互推荐 | 修LEFT后改DISTINCT分母 | 连接与计数粒度失配 |
| polar_5 | 排序错，后续违背公式加入/100 | 公式保住但排序仍错 | 无证据修订/未针对根因 |
| vaccine_2 | 只问sensor status，用原始tempstabidx | 几乎同样行为，重复同SQL | 澄清覆盖不足 |
| solar_4/P2、vaccine_7 | 数据/评测干扰+猜修 | 同类干扰+猜修 | 共同失败含环境原因 |

相同结果并非相同根因：gaming_7中Kimi simulator错误把求和说成平均，Flash则未问DS而猜指标；virtual_6中Kimi用churn等级平均，Flash被Qwen错误倒数公式带偏；mental_9中Kimi无依据扩大高风险人口，Flash缺RDD公式且ask被预算阻断。研究时应保留这种差别。

### 行为趋势差异比小幅成绩差异更清楚

| 同一32条完整轨迹 | Kimi 3 | Flash |
| --- | ---: | ---: |
| 单项知识查询 | 114（每任务3.56） | 304（每任务9.50） |
| SQL探索调用 | 165 | 118 |
| ask_user尝试 / 实际回复 | 31 / 31 | 40 / 39 |
| 使用ask_user的任务 | 22/32 | 28/32 |
| submit_sql调用 | 52 | 63 |
| 未完成且剩至少3 coins | 11/32 | 0/32 |
| 从未提交SQL | 2/32 | 0/32 |
| 每任务平均耗时 | 313.21秒 | 19.10秒 |

Flash问得更多、提交更多，也不保证更高正确率；它的问题偏向过度知识查询、迟问关键问题和预算耗尽。Kimi的问题偏向长分析后停在文本、未将剩余预算转为有效动作。旧Kimi的最终文本有截断外观，但记录不足以证明一定由4096 token上限造成。两者速度相差约16.4倍，仅为观察到的墙钟耗时，不能替代token/实际费用比较。

## 6. 对后续Flash研究的建议

先将simulator的“(1−x)与倒数”及缺失业务公式的回答口径固定；将空GT无法通过和日期/文字冲突作为明确环境问题限时处理。如果改变协议或评分，baseline和方法须在同一新环境重跑，保留本次原分数，不混合比较。

agent机制优先聚焦“有证据的完整意图状态+局部修复检查”：记录指标公式、对象/统计粒度、保留范围、排序/limit、输出结构、当前日期语义、DDL名称/重复执行要求；区分用户确认、KB、推测和冲突。提交失败后优先查未确认槽位及实现差异，不能随意反转已确认公式/范围。

同时加一个有界探索策略作为对照：not found或批量知识已取后不再穷举相关名称；尽早问缺失定义，并给P2留下一次查询+提交的预算。先比较提示版与结构化状态版，避免把复杂框架收益和简单提示/更多调用混在一起。不要用oracle GT驱动被评测agent，也不要把人工审阅过的这36条当独立最终测试集。

## 7. 来源与完整逐条标注

- [Flash原始结果](../results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/pilot36_seed42_20261004_retry1/eval_a_interact.json)
- [历史Kimi31条结果](../results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume1.json)、[最后1条结果](../results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume2.json)
- [相同36条任务及隐藏参考信息](../results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/tasks.jsonl)
- [36条任务对照CSV](../results/analysis_flash_vs_kimi36_20261004/task_comparison.csv)、[完整任务标注JSON](../results/analysis_flash_vs_kimi36_20261004/task_annotations.json)
- [47次澄清尝试审查CSV](../results/analysis_flash_vs_kimi36_20261004/simulator_audit.csv)、[完整问答与审查JSON](../results/analysis_flash_vs_kimi36_20261004/simulator_audit.json)
- [可重算统计JSON](../results/analysis_flash_vs_kimi36_20261004/statistics.json)

CSV/JSON及下方分析包含隐藏参考信息，仅供研究者诊断，不允许直接输入被评测agent。

| Task | Flash P1/P2 | Kimi P1/P2 | 主要问题/观察 |
| --- | --- | --- | --- |
| alien_11 | 0/0 | 仅零分日志 | 输出契约；局部修复：AOI/OOW基本正确；JSON使用station_name/solar_condition而非station/solar_status，并trim固定长度站名。澄清只修正lunar_factors及内部键；最后仅改布尔别名。ROUND缺失不单独归因，因为评测移除ROUND。 |
| alien_7 | 1/0 | 仅零分日志 | P2旧约束丢失：P1澄清JSON后通过；P2添加Quiet/SDS和AOI新阈值，却漏掉P1的月相、月距和太阳状态约束。P1完成时剩4.5 coins。 |
| archeology_1 | 0/0 | 仅零分日志 | 缺失公式；simulator未充分回答：SQS被任务删除，查询未找到；simulator被明确问公式仍只列成分并要求用standard definition，agent最后编造比例式并多输出rank列。 |
| archeology_9 | 0/0 | 仅零分日志 | 澄清覆盖；连接与排序：已获得正确PCDR/FEE公式，但仍INNER JOIN而非参考的保留站点连接链、按site_code而非FEE降序，未覆盖空值和输出格式。参考SQL末尾JOIN scanfeatures也限制完全无数据站点，文字all sites并非严格实现。 |
| credit_8 | 0/0 | 0/0 | 已确认语义未落实；SQL执行错误：simulator明确要求住房成本区分Own/Rent，提交改用mthexp；使用INNER JOIN、分组均值再平均/中位数再平均、Grand Total命名及按segment排序也偏离。UNION将Grand Total强转enum而执行失败。住房成本回复未明确mortbalance/12，仅说monthly mortgage payment，细节仍不完整。 |
| credit_M_6 | 1/1 | 1/1 | 成功：FSI公式和新列名得到有效澄清，两阶段通过。新建列名fsi是用户指定对象名称，不能将其自动视为底层schema泄露。 |
| cross_db_5 | 0/0 | 0/0 | 范围与输出；修复回退：与Kimi同样先选recordregistry而非compliancetrace，漏LIMIT10；行级跨国过滤与参考记录级EXISTS语义不同。Flash一度输出正确ID却加多余列，末次再次回到错误ID。 |
| cross_db_4 | 0/0 | 0/0 | 输出结构；连接：SRS公式澄清正确并采用，但JSON键仍是profile_id等而非指定CamelCase，INNER替LEFT；失败后转单个json_agg数组而非逐行对象。不是只改列alias的问题。 |
| crypto_3 | 0/0 | 0/0 | 统计范围；simulator澄清不完整：PVaR公式修正正确；simulator未纠正提问中top按notional value的前提，只回答top5。最终按notional排序，并经orders/marketdata逐条取vol，而非pivot降序5条加全局最新单条vol。 |
| crypto_M_4 | 0/0 | 1/0 | 额外假设；管理操作工具：按买卖方向选bid/ask并加exchange连接，偏离参考bid优先缺失才ask的定义；未澄清large orders的完整实现。尝试execute_sql建视图被SELECT-only拒绝；主要失败不是此一次工具误用。 |
| cybermarket_2 | 0/0 | 0/0 | 输出投影未确认：Qwen完整给出认证、争议率、运营天数、VTI四条件且SQL均落实，但三次提交仍SELECT大量vendor列/SELECT *，漏关联市场名。历史Kimi simulator还漏两个过滤条件，本轮该部分改善却仍失败。 |
| cybermarket_1 | 1/1 | 1/1 | 成功；一次多余澄清：TCR第二次问公式只得到成分，第三次才获得权重；随后两阶段通过，显示可回答与单轮完整回答有差别。 |
| disaster_3 | 0/0 | 0/0 | 输出列缺失；无证据回退：两者都漏disaster registry列；Flash首版EIF公式正确，失败后添加operations连接，末版去掉ROUND并反转DESC，核心缺失列未修。ROUND去除不是独立失败解释。 |
| disaster_7 | 1/1 | 1/1 | 成功：CEE公式澄清后两阶段通过。SQL只按disaster关联coordination，参考另有operation键；现有数据通过不保证任意数据同义。 |
| fake_8 | 0/0 | 0/0 | 已确认指标未落实；聚合粒度：明确否定NIC，最终仍用NIC算influence_rank；把platform identifier当cluster、COUNT(DISTINCT account)与参考按clustsize窗口COUNT不同。参考DENSE_RANK<=10/LIMIT100与文字top10 accounts也有边界张力。 |
| fake_1 | 0/0 | 0/0 | 缺失公式；聚合粒度：simulator只说明BBI成分，未给0.4/0.3/0.3及1-convnatval；agent用平均/3、正向convnatval，按platident分组并limit10而非参考clustsize与100。参考按cluster size分组是否符合真正cluster也值得审查。 |
| gaming_7 | 0/0 | 0/0 | 过度知识查询；编造指标：查询28次单项知识，缺失DS后未ask；以usbconndur/1000替代由drop/bend/twist/usb组合的DS，多连接并输出device ID/原IPX字符串而非physical registry/数字等级。历史simulator把求和说成平均也影响Kimi。 |
| gaming_M_4 | 0/0 | 0/0 | 外键/评测协议；范围扩张：AQI公式最终澄清正确，但DELETE遇FK，三轮扩大删除RGB/physicaldurability仍遇更深FK。GT关闭外键触发器；模型还有频响解析和RETURNING *问题，不能全归因于规划。 |
| insider_8 | 0/0 | 1/1 | 过度查询；缺失公式未澄清：23次知识查询后只确认群体定义；已知道OMI未找到，却未问OMI公式，最终AVG(modfreq)代替modfreq/(1-cancelpct)。Kimi询问公式和统计范围并两阶段通过。 |
| insider_M_5 | 1/1 | 1/1 | 成功：更新归一化及分布统计两阶段通过；成功不意味着所有NULL处理均和GT同义。 |
| mental_9 | 0/0 | 0/0 | 过度查询；预算阻断：32次知识查询耗掉16 coins，ask在0.5 coins被callback阻断，未调用simulator；之后编造RDD复合比值而非PFIS-FRAI。不能将其记为simulator拒答。 |
| mental_1 | 0/0 | 0/0 | 澄清覆盖；范围与输出：Qwen纠正高压力和TES阈值，SQL采用，但仍只输出envstress缺lifeimpact、TES优先排序/LIMIT10而非日期降序/50；latest筛选先后和平均TES过滤位置也与参考不同。 |
| museum_6 | 1/1 | 1/1 | 成功：澄清A/B后两阶段通过；Flash无P2 ask。 |
| museum_M_4 | 0/0 | 1/1 | DDL对象契约；反馈不明确：四次CHECK范围正确但名字不对。实际test_case要求hist_sign_rating_check；模糊请求未给name，Qwen只回答被问的范围，Kimi当时额外给了name。不能把Flash四次换名字当普通SQL语法失败。 |
| news_M_1 | 1/1 | 1/1 | 成功；工具限制：execute_sql尝试ALTER被拒后正常submit，两阶段通过。 |
| news_9 | 0/0 | 0/0 | 统计分母；连接：两者首版从interactions INNER JOIN，漏未交互推荐；Flash改LEFT后用COUNT(DISTINCT recommendation)与COUNT(DISTINCT interaction)而非参考连接行COUNT(*)，变换统计粒度。 |
| polar_5 | 0/0 | 0/0 | 排序契约；修复未针对根因：Qwen公式正确并保留，两次按station/location排序而非WRMI/WQI降序；Kimi同样排序错误，失败后另无依据将waterlevelpercent除100。Flash没有复现这次公式回退，但仍未修排序。 |
| polar_7 | 1/0 | 0/0 | P1成功；P2参考语义漂移：两次澄清拒绝分类标签并确认数值ESI，P1通过；P2继续使用已确认百分值尺度，但GT暗中将ESI和WRMI各缩小100倍，follow-up文字仅说side by side，未声明归一化。该P2不能简单计为遗忘/能力错误。 |
| robot_M_3 | 0/0 | 1/1 | 对象契约；可重复更新：多轮才确认table/column名，最后仍用real而非numeric；test_case以1e-9容差验证WFPS并修改原表后再次执行pred SQL，Flash缺ON CONFLICT DO UPDATE，重复INSERT会失败。缺UPSERT为已证明的静态契约差异，具体首次失败时点仅generic fail无法确定。 |
| robot_6 | 1/0 | 0/0 | P1成功；P2 NULL候选差异：P1分别聚合wear/operation后通过；P2 latest_fault未排除NULL faulttypeestimation，而GT先过滤NOT NULL，再按upkeepduedays选。该差异是静态候选，不将其宣称为经重跑确认的唯一原因。剩2.5 coins仅一次免费退出提交。 |
| solar_4 | 1/0 | 1/0 | P2文字/参考冲突；修复回退：两者P1通过，P2按plant加MCE>100仍失败，GT却改按panel type聚合。Flash末版把MCE条件改为原始cost>100，无新证据；首先应标记GT与文字冲突。 |
| solar_3 | 1/0 | 1/0 | P2时间窗口；空结果评测缺陷：两者P1通过，P2把now改为MAX(alertmoment)，且过滤/连接粒度也偏离。Flash记录当前日期窗口alert数0，GT必为空；ex_base拒绝空结果，正确空结果也无法通过。 |
| vaccine_7 | 0/0 | 0/0 | 当前日期漂移；空结果评测缺陷：两者执行CURRENT_DATE版本均为空，数据refill在2025-02，系统日期2026-09/10；GT按当前日期也为空。ex_base无条件拒空。随后两者都改用2025-02-19，偏离意图，但失败不能仅归咎于日期猜测；排名过滤先后/RANK与DENSE_RANK另有差异。 |
| vaccine_2 | 0/0 | 0/0 | 指标和条件覆盖不足；重复提交：两者只澄清sensor状态，未问TSS/critical；都以tempstabidx替复合TSS，漏一年窗口、CRI>0.6 OR TSS<0.4、默认值处理不同。Flash最后两次SQL完全相同，未产生有针对性的修复。 |
| virtual_6 | 0/0 | 0/0 | simulator错误；统计粒度：Qwen把(1-intconsist)说成inverse of interaction consistency，Flash实现1/intconsist并触发除零，然后NULLIF保留错误公式。COUNT(DISTINCT fan)也不同于参考连接行COUNT(*)。Kimi则未澄清risk score，直接平均churn等级。 |
| virtual_M_4 | 0/0 | 0/0 | simulator澄清不完整；FK/协议：Qwen确认3.5阈值但没有澄清完整公式，最后称风险公式包含engagement且原请求给过，GT却将engagement作为单独过滤。Flash对churn严重度自行除3；提交FK失败。Kimi只删High churn，也FK失败。GT关闭触发器，须区分语义与环境。 |

## 8. 后续对话接手顺序与未完成事项

1. 先读本文件与[项目README](README.md)，再根据具体问题打开任务CSV或simulator完整问答。有效DeepSeek结果必须使用`retry1`目录；首次TLS失败结果不能混入成绩。
2. 本轮只完成baseline运行和静态诊断，未实现新的意图状态、局部修复或预算策略；未修复simulator公式、空结果评分、日期数据和参考SQL冲突；未详细诊断Pro全部轨迹。建议不等于已经实现或已获用户要求实施。
3. 下一步先与用户确定研究机制或明确环境修复范围。若修改simulator/评分协议，保留历史结果，baseline与方法在同一新配置重跑；不能沿用旧成绩声称机制提升。
4. 运行步骤见项目README：`conda activate bird-interact`、`docker compose up -d postgresql`、`bash scripts/start_services.sh`，随后检查6000–6002 health及实际型号。密钥不写进交接文档或日志。
5. 36条已经用于开发诊断，后续正式验证应使用未参与人工分析的样本。没有实际账单/token数据，不能将墙钟速度差直接写成费用降低比例。
