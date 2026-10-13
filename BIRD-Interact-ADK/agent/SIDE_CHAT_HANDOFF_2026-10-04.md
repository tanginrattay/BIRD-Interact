# 侧边对话接手记录：模型选型、成本、simulator 网页校准及 Qwen 接入

整理日期：2026-10-04。本文是侧边对话的实质内容与状态摘要，不是逐字聊天记录。供正式对话继续工作时阅读；不含任何 API Key。动态价格和平台规则仅代表本次查询结果。

## 最新主对话补充：下个对话的起点

2026-10-04用户要求本session结束前只更新README和handoff，不在本session执行下一步。主对话内容已并入 [agent/README.md](README.md)，包含36条最终进度、机制证据、对照设计及可比性讨论。

- 用户认为Kimi3/Kimi2.6过贵，已选择Qwen Plus作为simulator，下一步优先想用**DeepSeek Flash（用户称Flash4.1）作为system agent**，Pro备选。本文旧第8节的“Qwen/GLM system agent比较建议”已被这个新偏好取代；不应主动再扩展选模列表。
- DeepSeek尚未接入，确切model ID、供应渠道、工具调用和思考参数待核查。本轮没有做价格/型号新查询，也没有把用户提到的Flash4.1当作已验证可用的API名称。
- Qwen代码接入/mock测试状态沿用侧边记录；用户说已换用，不等于已经存在真实API验收结果。检查配置是否存在即可，不打印Key。本轮未检查服务进程、未重启服务、未发模型请求。
- **历史36条pilot全部跑完，无需恢复旧remaining_tasks列表。** 最后virtual_M_4已于9月29日20:13:59完成；旧pause_checkpoint/remaining_tasks仍可能显示1条待跑，它们不是最终状态。
- 下个对话应根据用户新指令推进DeepSeek Flash接入和最小验收，并确认Qwen simulator实际可用，再冻结新环境做小baseline。不能只改型号就称切换完成；也不要立即启动全量300条或把模型迁移和新架构混成一次实验。

## 主对话研究结论与实验档案

历史pilot：18库各2题、seed42，排除alien_1–5，system agent Kimi3、simulator Kimi2.6单阶段，串行。32条完整结果：P1=12/32、P2=9/32、reward=0.346875；另4条只有日志摘要、reward均0。全36条reward=0.308333，按正常奖励协议推断P1=33.33%、P2=25%；不能编造四条缺失轨迹。历史K3没有后来新增的显式low配置，更不是Qwen/DeepSeek实验。

来源导航：

- `results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume1.json`：31条完整结果。
- `results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume2.json`：最后1条virtual_M_4。
- `baseline_run1.log`：最初alien_11、alien_7、archeology_1、archeology_9的摘要。
- [人读Markdown总览](../results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/markdown/README.md)：36任务索引、完整字段、原始文件全文及SHA256校验；源中已有截断无法恢复。
- [本地改动与协议可比性](LOCAL_CHANGES_AND_COMPARABILITY.md)：相对Git基点的主对话改动说明。其Kimi函数名/路由描述是迁移前历史快照；当前`_ask_direct`和显式pipeline以本handoff第6节为准，shared/llm中的K3-low也是后来侧边加入。

最有证据的机制候选是**有来源的意图状态＋保持已确认约束的局部修复**，尚未实现、未消融：

| 案例 | 证据 | 注意 |
| --- | --- | --- |
| credit_8 | 用户说明TDSR自有/租房两分支，提交漏Rent | 澄清未完整落实，同SQL还有其他错 |
| polar_5 | 首提交按澄清公式，失败后额外将waterlevelpercent除100 | 无新证据的语义回退 |
| vaccine_7 | 明确CURRENT_DATE，修复时改固定2025-02-19 | 违背明确时间约束 |
| mental_9 | 初始SRP High/Severe，修复无新澄清却增加抑郁/焦虑人群 | 不称全部定义已被用户确认 |

建议先baseline、简单“不要违背已确认要求”提示、显式状态/修改检查三组；衡量正确澄清落实率和无证据回退次数，成本也要报告。状态记录来源和范围，可在有新证据/冲突时修订，不能盲目锁死simulator所有答案。GT仅用于研究者离线分析，不能输入system agent。

第二候选是语义覆盖/澄清优先级：cross_db_4有9次SQL执行却未澄清且定义/JSON仍错；polar_7把数值指标换成分类；vaccine_2只澄清状态没落实其他计算；crypto_3排名字段澄清后仍错方向和全局最新波动率范围。不是鼓励所有槽位无差别问用户。

运行诊断：11条未完成全部阶段但余>=3coins，fake_1/gaming_M_4从未submit。现有结果不能证明全部是token截断；区分模型结束、工具未形成和runtime后再归因。基础修复所有组共享，不包装为机制贡献。

混杂案例需标记：gaming_7 simulator把DS求和说成平均；cybermarket_2漏Trusted Vendor两条件；solar_4 follow-up文字仅加过滤而GT改变分组；gaming_M_4/virtual_M_4 GT涉及关闭FK触发器。不能把这些都算agent规划失败，也不能悄悄删除。solar_3澄清后P1成功是正例，无配对实验不能量化收益。

研究路线已讨论：不要无限修benchmark，当前可以开发最小机制；官方baseline可比性需要同协议、同任务重跑baseline和方法，不能直接与发布分数相减。“较低成本模型缩小强模型差距”可作课题目标，但强弱须同环境建立，不预称Kimi3弱、不保证追平；固定bird-coins不等于token/实际成本相同。pilot是已看过的开发集，最终要独立保留集。

## 0. 接手先看：现在完成到哪里

- 用户已在阿里云百炼充值、生成 API Key，并明确要求 simulator 换为 Qwen 3.7 Plus，Key 留空由用户自行填写。
- **代码接入和 `.env` 修改已完成；12 项离线测试通过。没有进行真实百炼 API 调用，没有验证真实连通性或 Qwen API 的语义质量。**
- 上次检查时 `.env` 的 `USER_SIM_API_KEY` 为空；接手时用户可能已自行填写，只检查是否配置，不打印值。
- **没有启动、停止或重启任何服务，没有运行新的完整 benchmark，没有修改数据库，没有产生本轮模型 API 费用。** 已运行服务可能仍在使用旧配置，不能仅看 `.env` 就认为线上切换成功。
- system agent 仍是 `moonshot/kimi-k3`。本侧边对话较早已将其 API 默认推理强度改为 `low`；现有服务同样须重建实例才会生效。
- Qwen simulator 当前是 **非思考模式 `enable_thinking=false`，不是所谓官方 low 档**。用户此前提过 Qwen low，但查文档后明确解释了参数差异。
- simulator 保留此前本地单阶段协议，未修改角色提示、隐藏上下文内容、bird-coin 或 system agent policy。
- 详尽接入说明：[QWEN_SIMULATOR_SETUP.md](QWEN_SIMULATOR_SETUP.md)。

## 1. 用户研究背景与侧边对话边界

用户做本科科研：Agent for multi-turn Text-to-SQL，以 BIRD-INTERACT a-Interact 为主，研究 inference-time agent 机制，而不是训练基础模型。外国模型有报销障碍，用户希望使用可开国内发票且低成本的模型。

正式对话已经进行了 benchmark 调试、36条 pilot、失败分析等。侧边对话没有继续执行那些历史任务，只对模型/成本问题做只读分析，并在用户明确要求后进行了以下局部代码和文档修改。

**不要把工作树全部 diff 都算成本侧边对话修改。** 原本已有未提交修改和未跟踪文件；未 commit、未 reset，原有改动保留。尤其 `orchestrator/runner.py`、`shared/models.py`、`system_agent/tools.py` 的既有改动不是这里新增。

## 2. 成本讨论与已经采取的行动

用户最初报告累计消费约109元；随后补充账单 Kimi 3约95元、Kimi 2.6约13元，二者合计108元，1元差异未核销。K3约占两者总和的88%。不能断言全部成本都由推理强度造成。

只读统计：pilot36中32条完整结果含370条模型事件、471条工具记录、31次ask_user。模型事件数不严格等于API请求数。用户还跑过5题、10题、早期诊断、失败重试等，不能把51题当精确计费分母。现有完整结果没有逐请求usage，不能准确还原每个模型的输入/输出/缓存/思考消费。

当时查到K3官方默认推理强度为max。用户要求降低成本，因此修改了：

- `shared/llm.py::build_adk_model`：最终模型名恰为 `kimi-k3` 时传 `reasoning_effort="low"`，保持 `max_tokens=4096`。
- `shared/llm.py::call_llm`：K3未显式指定effort时默认low；显式指定则保留；其他模型默认行为不变。
- 新增 `shared/test_llm.py`，mock验证上述参数传递；也检查过实际ADK对象 `_additional_args` 中包含low。

未实测降价或提速比例。新实验必须标记K3-low，不能把它与之前默认推理配置当同一个baseline。

依据：[Kimi推理强度文档](https://platform.kimi.com/docs/guide/use-reasoning-effort)。

## 3. 固定网页测试材料与原始回答

用户要求准备可复制的固定上下文，手动用网页版比较模型。建立目录：[simulator_web_comparison](simulator_web_comparison/README.md)。

- `01_COPYABLE_CASES.md`：10个完整、独立可复制的text块。
- `02_KIMI26_HISTORICAL_RESULTS.md`：已有K2.6真实回答，逐字摘录，不是标准答案；附更早prompt版本的部分回答。
- `03_REVIEW_GUIDE.md`：人工核查要点和数据冲突提醒，不给被测模型看。
- 最初创建 `04_RESULT_TEMPLATE.md`；目前文件列表中已无此文件，用户保存的各模型结果沿用该模板。不要声称它现在仍存在。
- README含来源SHA256、复制方法、协议及版本限制。

题目来源与范围：

| 编号 | 任务 | 检查点 | 原回答来源 |
| --- | --- | --- | --- |
| C01 | alien_5 | 错误二选一、聚合与JSON结构 | usersim_calibration_v3.json cases[0] |
| C02 | alien_5 | encoding与modulation分组纠错 | 同上cases[1] |
| C03 | alien_5 | 分组、ECI/MCS、SNQI/SNR同时纠错 | 同上cases[2] |
| C04 | alien_5 | 指标名称澄清 | 同上cases[3] |
| C05 | alien_5 | 纠正历史中错误用户回复 | 同上cases[4] |
| C06 | alien_1 | weather及SNQI>0，不是SNR>0 | 同上cases[5] |
| C07 | alien_3 | LIF>0.5，不是High类别标签 | 同上cases[6] |
| C08 | alien_5 | 拒绝提供SQL及数据库实现 | 同上cases[7] |
| C09 | gaming_7 | DS求和不能变平均，PER>9与IP映射 | pilot36_seed42/baseline_resume1.json |
| C10 | cybermarket_2 | Trusted Vendor四项条件完整性 | 同上 |

C01–C08是历史真实HTTP校准，但包含人工构造问题，不全是benchmark自然提问；C09–C10是实际pilot自然提问。共5任务，均为Phase1。C09/C10上下文从任务快照和对话重建，不是原始HTTP抓包。

创建时验证过10个块与当时 `_ask_kimi` 的真实上下文构造完全一致、10条历史回答逐字保留。API的system/user两条消息在网页上合成一条，因此网页对照不是严格API对照。历史请求没有完整存档system prompt，不能宣称与历史K2.6完全同条件复现。

每题应新会话，只贴一个完整text块；不贴答案或评分。结果保留界面型号、思考开关、是否联网；未知后端不推断具体基础模型。用户手动执行并保存结果，**不是本助手调用这些模型得到的**。

## 4. 网页结果分析（8种模式，各10问）

原始文件均在上述目录，文件名日期2026-10-04：

| 文件中的模式 | 用户记录设置 | 主要观察 |
| --- | --- | --- |
| DeepSeek，具体模型未知 | 思考关、联网关 | C03仅答Yes，接受错误前提；C07缺0.5，C09未说明公式；C10四条件完整 |
| GLM5.3 | 思考low，无法关闭 | C10把>90说成至少90；C09未解释公式；C03把至少5与超过5等同 |
| GLM5.3Flash | 思考low，无法关闭 | C09正确自然语言解释求和公式；C07不说阈值；C10用低争议率/经营一段时间代替精确条件 |
| Kimi3 | 标准思考 | 多数概念正确；C09拒绝提供公式；C10把<5%说成under about 5%，不够精确 |
| Qwen3.5Plus | 快速 | C09公式正确；C10漏争议率和活跃天数；若干回答展开过多 |
| Qwen3.6Plus | 快速 | 概念、错误历史纠正和C10完整性较稳；C09仅说有公式 |
| Qwen3.7Plus | 快速 | 与3.6接近；C10四项条件和严格阈值正确；C09仍没说明公式；C03主动提争议阈值 |
| Gemini3.8Flash | low、无联网 | 概念澄清正确，C09准确给求和/缩放公式，C10四条件精确；C03仍主动提至少5，C10主动补输出字段 |

最后对比结论：**Gemini在C09完整性上明确优于Qwen3.7，但没有全面碾压；Qwen3.7足够成为低成本simulator的优先候选，尚需同协议API小规模验收。** 不给这组有意挑选的10问包装成总体正确率或基础模型排行榜。

历史K2.6关键问题：C09把DS三项之和误说成平均；C10遗漏争议率<5%、活跃时长>90天。早期统一fallback/空响应有明确工程原因：小输出预算被reasoning耗尽、异常/解析被转成fallback，不是模型智力不足的证据。

### 测试设计问题：务必保留这些限定

1. **C09提示边界不清。** 当前指令一方面允许被问到时提供公式，一方面禁止数据库实现细节和字段实现说明；问题又问公式或哪一列。Qwen/Kimi不给公式可能是过度拒绝，不应直接算不会计算。本助手已承认此前公共提示过于宽泛。此次迁移不修改该prompt，以免混淆模型和prompt因素。
2. `alien_5`文字at least 5与SQL COUNT(*)>5冲突。C01–C05没有直接问阈值，模型主动补充会引入冲突；Gemini也未消除这个问题。
3. `gaming_7`标注里的LENGTH/30与实际SQL的IP映射/6不一致；DS求和在SQL和knowledge标注里一致，是无争议核查点。
4. C10真值四项：Advanced或Premium、争议比例<0.05、活跃时长>90、VTI>80；VTI降序。不能用近似阈值或把条件漏掉。
5. 这组只测simulator，不测system agent的SQL、工具调用、错误恢复能力；不能用网页simulator结果直接选最佳system agent。

## 5. 价格、采购和原论文核查

### 价格讨论

为统一口径，当时采用百炼北京普通API公开原价，单位元/百万token，未缓存、非促销；Qwen用输入<=256K档。不把渠道价格当成历史Moonshot账单费率。

| 模型/渠道 | 输入 | 输出 |
| --- | ---: | ---: |
| Kimi K3，月之暗面直供 | 20 | 100 |
| Kimi K2.6，月之暗面直供 | 6.5 | 27 |
| Qwen3.5/3.6 Plus | 2 | 12 |
| Qwen3.7 Plus | 2 | 8 |
| GLM5.3，智谱直供 | 8 | 28 |
| GLM5.3Flash，智谱直供 | 0.8 | 2.8 |
| DeepSeek V4.1Flash，百炼部署 | 忙时2/闲时1 | 忙时8/闲时4 |

来源：[总价格表](https://help.aliyun.com/zh/model-studio/model-pricing)、[Qwen3.7](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)、[GLM5.3Flash](https://help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu)。价格以后需重查，DeepSeek网页未知型号不能与表中API型号直接对应。实际任务成本还取决于思考、缓存、轮数、重试。

建议（仅建议，未执行）：simulator优先Qwen3.7；system agent以后小样本对比Qwen3.7与GLM5.3Flash，K3只作少量对照。**此次没有切换system agent。**

### 采购与发票

建议百炼普通按量付费API，不是千问网页会员。用户现已开通充值。个人账号可申请学校抬头，需审核，不应无授权把个人账号改成学校企业账号。未消费充值余额不能直接开票；后付费一般次月3日后可开；报销仍以学校财务要求为准。

来源：[发票FAQ](https://help.aliyun.com/zh/user-center/support/faq-about-invoice-requests)、[开票流程](https://help.aliyun.com/zh/user-center/get-invoice/)、[高校计划](https://help.aliyun.com/zh/model-studio/introduction-to-yungongkaiwu)。未替用户操作账号、充值或申请发票。

### 原论文的simulator

- 官方原版 `bird_interact_agent` README声明使用 `gemini-2.0-flash-001`，Vertex AI；Lite提示v1、Full提示v2。
- 论文simulator专项实验比较Gemini2.0Flash和GPT-4o，不能与ADK README的Sonnet4.5 + Haiku4.5混淆。
- arXiv v2附录N的UserSim-Guard有1989题，双LLM裁判。AMB/LOC/UNA：Gemini直接回答93.57/95.52/66.93%，function-driven94.76/96.75/93.80%；GPT-4o直接90.72/96.30/63.45%，function-driven98.81/98.88/94.08%。不是全部真实任务的人类标注正确率。
- 与真人交互所得系统成功率的相关性：function-driven GPT-4o 0.84、Gemini0.79；不是回答正确率。
- Google文档当时列Gemini2.0Flash于2026-06-01关停，因此用户用Gemini3.8Flash作新参考，不是论文旧型号复现。
- 不能从这些数据推断“国外模型必然更强”；论文强调模拟机制作用。本地单阶段网页测试不是论文两阶段复现。

来源：[原实现README](https://github.com/bird-bench/BIRD-Interact/blob/main/bird_interact_agent/README.md)、[论文v2](https://arxiv.org/html/2510.05318v2)、[Google关停文档](https://ai.google.dev/gemini-api/docs/deprecations)。

## 6. 本次Qwen接入的实际代码改动

### `.env` 当前配置方向（不含密钥）

```dotenv
SYSTEM_AGENT_MODEL=moonshot/kimi-k3
USER_SIM_MODEL=qwen3.7-plus
USER_SIM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
USER_SIM_API_KEY=
USER_SIM_PIPELINE=single_stage
USER_SIM_ENABLE_THINKING=false
USER_SIM_THINKING_BUDGET=2048
```

Key留空是用户要求；原Moonshot Key未改动。默认百炼北京域名目前仍可用，文档也推荐业务空间专属域名，可按控制台实际地域修改。环境变量优先于.env。

### 修改清单与语义

| 文件 | 本侧边对话改动 |
| --- | --- |
| `.env` | 切Qwen simulator、独立百炼地址/空Key、单阶段/非思考配置；保持system agent |
| `.env.example` | 添加注释形式的Qwen示例，保留原默认示例 |
| `shared/config.py` | 新增user_sim_api_base/key、pipeline枚举、enable_thinking、thinking_budget；Key字段repr=False |
| `user_simulator/bailian.py`（新） | 独立httpx百炼HTTP客户端；不依赖LiteLLM或新增SDK |
| `user_simulator/server.py` | Qwen调用独立客户端；协议显式选择；`_ask_kimi`改名`_ask_direct`，角色提示与上下文保持不变 |
| `user_simulator/test_bailian.py`（新） | mock HTTP、凭证隔离、路由、空答/截断/HTTP错误、本地真实task上下文测试 |
| `user_simulator/test_server.py`（既有未跟踪） | 适配函数改名和新增设置；保留旧Kimi/两阶段测试 |
| `scripts/check_user_simulator.py`（既有未跟踪） | 校准结果记录pipeline、Qwen思考配置；说明来源是本地设置，不是服务器抓包 |
| `scripts/prepare_pilot.py`（既有未跟踪） | 修复所有非Kimi都被误标two_stage；记录Qwen思考配置；没运行脚本 |
| `agent/QWEN_SIMULATOR_SETUP.md`（新） | 配置、验证、生效、费用和协议边界说明 |

### 请求与错误处理

- `is_qwen_simulator`识别最终型号 `qwen3.7-plus` 及带日期后缀的快照；请求时去掉可能的provider前缀。
- Qwen走独立 `USER_SIM_API_KEY`，空值发请求前报错；不读取共享LiteLLM、Moonshot或OpenAI密钥做回退。
- HTTP POST `{USER_SIM_API_BASE}/chat/completions`；system/user消息与现有单阶段一致。
- `temperature=0`、`stream=false`、HTTP body顶层 `enable_thinking`，不把`extra_body`作为嵌套JSON发送。
- 非思考模式 `max_completion_tokens=1024`。若手动启用思考，则发送`thinking_budget=2048`、总输出上限3072（预算+1024）；2048只是配置值，不称官方low。
- 不向Qwen发送Kimi的`reasoning_effort=none`，不假定Qwen3.7在Chat API支持`reasoning_effort=low`。文档明确支持enable_thinking/thinking_budget；Responses等其他端点须另核查。
- 客户端超时90秒；不自动重试，不静默fallback。401等HTTP错误、无choices、finish_reason不是stop（包括length）、空content都显式失败。
- 只用最终content，不把reasoning_content当用户回复。现有上层tool如何转错误沿用原逻辑，未改变coin扣费或evaluator。
- 日志记模型/finish_reason/prompt_tokens/completion_tokens；尚未把完整usage写入benchmark JSON，不算完成全项目成本遥测。

文档依据：[百炼Chat接口](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)、[Qwen3.7Plus](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)。没有真实API证明参数最终被服务端接受。

## 7. 验证结果与未覆盖范围

在 `/home/nimir/miniconda3/envs/bird-interact/bin/python` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 LITELLM_LOCAL_MODEL_COST_MAP=True \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest \
  user_simulator.test_server user_simulator.test_bailian shared.test_llm -v
```

结果：12 tests，OK；最近一次耗时2.255秒。`git diff --check`无错误，两个脚本AST语法检查通过。

已检验：

- Qwen模型名、北京兼容端点路径、system/user角色、非思考参数序列化。
- 独立假密钥在HTTP Authorization正确使用，未使用假system key。
- 可选思考预算2048、总输出3072正确。
- 缺Key零请求；401、截断、空答不变成正常用户回答。
- alien_1、gaming_7、cybermarket_2真实Lite记录的隐藏意图、SQL、历史、当前问题进入单阶段请求。
- Kimi旧路径与显式two_stage仍可调用；K3-low参数测试仍通过。
- 当前`_ask_direct`的instructions与已冻结网页输入开头一致，未改prompt。

**mock回答不证明模型能答对！** 未覆盖真实鉴权、地区/账户开通、服务端参数兼容、响应时延、真实消耗、simulator语义正确率，以及新配置下完整a-Interact。

最初K3测试导入LiteLLM曾尝试下载公开价格表，受网络限制回退；后续测试设置LITELLM_LOCAL_MODEL_COST_MAP=True。没有付费模型调用。

## 8. 侧边对话当时建议的下一步（历史建议，优先遵循本文顶部最新用户方向）

1. 确认用户已填Key，只报告有/无，不输出值；核对Key与北京地域匹配。
2. 先确认是否有主线程benchmark在跑。不要中途切simulator。`scripts/start_services.sh`包含广泛`pkill -f uvicorn`且重启三个服务，不能无检查地执行。
3. 安全重启user simulator，确保服务环境和本地.env一致；不要仅凭文件状态声称服务已更新。
4. 做最小真实API/ask_user校准，记录失败和用量。可以复用：

   ```bash
   python -m scripts.check_user_simulator --output results/usersim_qwen37_first.json
   ```

   会产生费用，且需服务已启动。该脚本仍是原有8问，不含网页C09/C10；若要验收关键失败模式，应另补gaming_7与cybermarket_2固定问题。输出文件存在时脚本拒绝覆盖。
5. C09过度拒绝问题如需改prompt，先保留旧测试，另立prompt版本，并对比必要案例；不要一边换模型一边悄悄改真值或提示。
6. 校准达到可用后冻结simulator，回研究主线。此前建议只比较两个候选system agent、6–10题小开发集，避免无限选模；这只是研究建议，用户尚未在本侧边对话授权执行。

## 9. 快速导航

- [接入操作文档](QWEN_SIMULATOR_SETUP.md)
- [原本地改动与论文可比性](LOCAL_CHANGES_AND_COMPARABILITY.md)
- [网页对照包说明](simulator_web_comparison/README.md)
- [固定10问](simulator_web_comparison/01_COPYABLE_CASES.md)
- [K2.6真实历史回答](simulator_web_comparison/02_KIMI26_HISTORICAL_RESULTS.md)
- [人工判据与冲突](simulator_web_comparison/03_REVIEW_GUIDE.md)
- [Qwen3.7原始结果](simulator_web_comparison/result_qwen3.7plus_web_2026-10-04.md)
- [Gemini3.8Flash原始结果](simulator_web_comparison/result_gemini3.8flash_web_2026-10-04.md)

接手原则：这是带明确局限的本地评测设置，不冒充官方baseline复现；不要因已写接入代码就宣称Qwen已在线运行或质量验收通过。
# 结果归档补充（2026-10-04）

历史 results 已按 agent/simulator 分组，入口：[results/README.md](../results/README.md)。原始63个文件逐一验证迁移前后 SHA-256 一致；包括 pilot 的完整日志、JSON、Markdown 和源文本。迁移映射见 `results/archive_manifest_2026-10-04.json`。文件内旧历史路径不改写，使用映射定位。

初始默认5条缺少完整模型元数据，归入 unknown；早期 kimi3/kimi26 文件只凭原文件名识别 agent，simulator 标为 unknown。不得用新 DeepSeek/Qwen 配置解释这些旧结果。

runner 默认输出改为模型分组下的 UTC 时间加随机ID目录，保存无密钥 run_metadata，显式指定已存在的 --output 会报错而不覆盖。元数据是 runner 配置，服务重启后才可认为与实际模型一致。本次只归档、更新引用和输出路径逻辑，没有跑新实验或修改 agent 策略。
