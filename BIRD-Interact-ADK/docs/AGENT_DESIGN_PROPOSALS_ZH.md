# 基于已有失败轨迹的 agent 架构设计候选

日期：2026-10-22。建议先读 [默认框架代码讲解](AGENT_FRAMEWORK_GUIDE_ZH.md)，再读本文。

**本文提出四套可分别实现的设计：探索预算控制、依赖驱动的意图修订、澄清回复验收、假设驱动的失败诊断。建议先做第一套的小版本，再以第二套作为主要研究候选。** 第三套适合研究交互可靠性；第四套实现和验证成本更高，与已有 SQL 修复方法的重合也更多。

这里只新增设计文档，没有修改任何 Python、配置、原文档或实验结果，没有运行模型、数据库或测评。下文新增文件名、函数名、状态字段、阈值都是**拟议接口**，不是仓库已有功能。所有收益都是待验证假设。

## 1. 从已有结果出发，而不是先选一个流行架构

证据来自 [Flash/Kimi 逐题分析](../agent/FLASH_KIMI36_ANALYSIS.md)、[可重算统计](../results/analysis_flash_vs_kimi36_20261004/statistics.json) 及 [Flash 原始轨迹](../results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/pilot36_seed42_20261004_retry1/eval_a_interact.json)。本次重新抽查了 `mental_9`、`alien_7`、`fake_8`、`vaccine_2`、`cybermarket_1` 的实际工具记录。

| 已观察到的现象 | 具体证据 | 支持什么设计假设 |
| --- | --- | --- |
| 信息缺失后不断探索，关键澄清来得太晚 | Flash 36 题共 345 次单项知识查询；`mental_9` 查 32 次，剩 0.5 coins 时的 ask 被拦截 | 应判断某种信息源是否还有希望，并保留问用户的能力 |
| 问对了，但 SQL 只修了一部分 | `fake_8` 已被告知指标不是 NIC，展示值改了，排名仍按 NIC | 要维护“需求—派生指标—SQL 使用位置”的依赖 |
| P2 局部修改导致旧条件丢失 | `alien_7` P1 通过，P2 改阈值、加条件后丢掉月相、月距、太阳状态要求 | 需要显式区分新增、替换、保留和撤销的条件 |
| 收到回复不代表获得完整答案 | `cybermarket_1` 一次回复只列公式成分，继续问权重后才得到完整公式；`archeology_1` 仍未获完整公式 | 要检查本次提问目标是否真正被满足 |
| 通用失败反馈诱发随意改 SQL | `disaster_3` 修改连接、反转排序却没有解决输出问题；`vaccine_2` 重复提交相同 SQL | 修复前应列假设、查证据，并限制无依据变化 |
| 部分运行提前结束 | 历史 Kimi 的共同 32 题中，11 题未完成但仍剩至少 3 coins | 可以加有界继续运行作为工程对照，但不是 Flash 最突出问题 |

三个解释边界决定后面的实验如何设计：

1. **这些是故障线索，不是干净的模型对照实验。** 历史 Kimi 与 Flash 的 simulator、推理参数和运行日期不同。Flash 原 36 题 P1 为 11/36、P2 为 6/36；这些分数不能直接作为当前代码和 simulator 配置下的 baseline。
2. **已有环境缺陷不能用 agent 硬猜补偿。** 分析记录了空结果判分问题、日期变化、部分文字/参考 SQL 冲突。不要把“空结果一定要改成非空”“失败就试除以 100”写成策略。
3. **simulator 已经历协议恢复。** 历史单阶段 Qwen 的行为与当前两阶段路径不同。[最新筛选记录](../agent/SIMULATOR_MATRIX_BAILIAN_2026-10-13.md) 还显示格式和回答质量问题。四问筛选不等于 simulator 整体可靠；改进应在同一冻结配置下重新比较。

这 36 题已经被用于分析和提出方法，应作为开发材料；最终效果需要没有参与设计的题目支持。

## 2. 文献查重结果：哪些方向不能直接作为新贡献

本次检索覆盖 Text-to-SQL agent、交互澄清、SQL 修复、记忆，以及通用 agent 的预算规划、诊断和信念维护。参考原论文/作者来源；这是一轮针对性检索，不是穷尽性的新颖性证明。

### 2.1 有两篇相关论文都叫 MERIT

| 方法与论文 | 已有机制 | 本文如何避开直接重做 |
| --- | --- | --- |
| MERIT：*Learning to Retrieve: Dual-Level Long-Term Memory for Text-to-SQL Agents*，2026 | episode / turn 两级长期记忆，学习检索策略，使用终局奖励和 PRM 信号；在 BIRD-Interact 上实验 | 不建立跨题轨迹记忆库，不训练两级检索器，不把“有记忆”作为贡献。[论文 v2](https://arxiv.org/html/2606.00547v2) |
| MERIT：*Causal Episodic Memory for Feedback-Driven Agent Repair*，2026 | 从已结束题目积累正负修复经验，按错误类型检索；oracle 成功状态参与记忆定性 | 不积累跨题正负修复案例；使用当前题目内的可见证据。这里 causal 主要指记忆时间可用性，不能误解为通用因果推断。[论文 v2](https://arxiv.org/html/2608.05906v2) |
| MIRA：*Evidence-Verified Repair Memory for Text-to-SQL Correction*，2026 | 检索修复记忆，验证当前任务确实需要该行为且 SQL 确有对应违例，再做局部适配 | “证据检查 + 局部修复”本身也已存在。第二套设计需要突出当前交互中的依赖失效和跨阶段作用域；仍需直接比较。[论文](https://arxiv.org/html/2608.06950v1) |
| AgentSM，2026 | 将历史或合成执行路径表示成可复用的结构化程序 | 不做跨题路径复用；本题状态在题目结束后不作为其他题目的知识。[论文](https://arxiv.org/abs/2601.15709) |

用户提到的 MERIT 未指定标题，因此这里同时对照两篇，不假定只指其中一篇。

### 2.2 另外几条很容易“看似新颖，实际上已有”的路线

| 宽泛想法 | 直接相关工作 | 对选题的影响 |
| --- | --- | --- |
| 生成者、检索者、修复者分工 | MAC-SQL；CHESS 还包括自然语言单元测试 | 只拆成多个 agent，不足以形成清楚差异。[MAC-SQL](https://arxiv.org/abs/2312.11242)、[CHESS](https://arxiv.org/abs/2405.16755) |
| 分析 AST、定位语义错误，再逐步修复 | SQLens 使用数据库与 LLM 的细粒度错误信号 | 第四套必须比较“静态检查后修复”和“先主动查证后修复”。[SQLens](https://arxiv.org/abs/2506.04494) |
| 维护多个 SQL 解释，挑最有信息量的问题问用户 | 已有 Expected Information Gain 的交互 Text-to-SQL 方法 | 第一套不把“信息增益提问”作为创新声明；关注不同信息源之间的预算与可获取性。[论文](https://arxiv.org/abs/2507.06467) |
| 用能区分候选程序的小例子请用户选择 | APEL 已用于 Text-to-SQL 标注 | 第四套不宣称“区分性样例”首次用于 SQL。[APEL](https://aclanthology.org/2023.emnlp-main.312/) |
| 对上一轮 SQL 做编辑 | EditSQL 已研究通过编辑上一轮预测处理上下文依赖问题 | 第二套差异不能只写“P2 修改 P1 SQL”。[EditSQL](https://arxiv.org/abs/1909.00786) |
| 变形测试、无标准答案的 SQL 验证 | MT-Teql、SQLHD 等已有相关机制 | 不把“给 SQL 加 metamorphic test”列成主要新方案。[MT-Teql](https://arxiv.org/abs/2012.11163)、[SQLHD](https://arxiv.org/abs/2512.22250) |

**更值得研究的是一个可测量的机制差异。** 例如：“新的用户证据只使依赖它的旧 SQL 决策失效，其他已确认语义继续保留”，比“加入记忆和反思”更明确。但明确不等于已经证明新颖。

## 3. 四套方案的选择表

| 方案 | 一句话说明 | 主要目标 | 最小实现复杂度 | 与已有 SQL 工作重合风险 |
| --- | --- | --- | --- | --- |
| A：有界的信息获取控制器 | 某个信息源连续无效时及时换渠道，保护关键交互预算 | 减少无效 KB 查询，避免太晚 ask | 低到中 | 中；预算规划和信息增益都有先例 |
| B：带来源和依赖的意图状态 | 证据变化时只撤销受影响的派生决策，保留其他要求 | 防止指标修一半、P2 丢旧约束、修复倒退 | 中到高 | 中到高；需对照 MIRA、SQLens、EditSQL |
| C：澄清回复的语义验收 | 分开判断“用户回复了”和“本次信息缺口补齐了” | 应对公式不完整、答非所问、含混回答 | 中 | 中；对话 grounding 不是新概念 |
| D：有预算的主动失败诊断 | 改 SQL 前先区分两三个候选原因，能验证才验证 | 减少 generic fail 后的盲改与重复提交 | 高 | 高；与 SQLens、测试/修复方法最接近 |

A 首先面向 a-interact。B、C 可以适配两种模式。D 的数据库探测版本只适用于 a-interact；不能为了实现 D 给 c-interact 偷加 `execute_sql`。

以下设计优先采用**一个执行 agent + Python 控制模块**。必要的抽取器/检查器可以调用同一个基础模型，但不必给每个模块都创建一个完整 ADK agent。

## 4. 共同实现边界：先把新模块接在正确位置

### 4.1 可以复用的两个小文件

建议按实际需要逐步创建，而不是第一天搭一套大型框架：

| 拟新增文件 | 功能与接口 |
| --- | --- |
| `system_agent/research_state.py` | `init_research_state()` 返回本题状态；`normalize_observation(tool, args, response)` 区分正常结果、not found、预算拒绝、传输错误、通用评分失败；只使用 agent 已可见信息 |
| `system_agent/research_hooks.py` | 集中接入选中的策略；`before_model()` 生成下一步提示，`before_tool()` 做可选内部检查，`after_tool()` 消费实际反馈；不要把所有方案散写进预算回调 |

[system_agent/agent.py](../system_agent/agent.py) 的 `build_agent()` 按实验开关选择 baseline 或研究回调；[shared/config.py](../shared/config.py) 可增加 `agent_variant`（默认 `baseline`）。不要改变同一进程中的全局 agent 来服务不同任务；当前 runtime 按 mode 缓存 Runner，第一版每次实验使用一个固定 variant、重启服务即可。若以后同进程跑多个 variant，需要同时改 Runner 缓存键和 session 隔离。

[orchestrator/ainteract.py](../orchestrator/ainteract.py) 的 `init_agent_session()` 和 [orchestrator/cinteract.py](../orchestrator/cinteract.py) 的 session 初始化处，只初始化研究字段。这里不能把隐藏歧义清单、正确 SQL、参考结果或 test cases 传给新模块。

### 4.2 所有方案都需要遵守的执行顺序

```text
模型前：原终止检查 → 注入本题研究状态/动作建议 → 调用模型
工具前：研究策略的内部检查 → 原版计费/预算规则 → 原工具 HTTP 请求
工具后：原版轨迹与反馈处理 + 研究状态更新
下一次模型调用：看到工具结果和更新后的状态
```

这只是逻辑顺序，接入时要保留 callback 返回值语义。几个容易影响实验有效性的点：

- 普通工具 HTTP 失败仍按原版扣费；研究模块不能自动退款。原版预算不足时的最终免费提交也要保留。
- 阻止一次内部动作和真正向环境发请求是两回事。记录 `attempted`、`executed`、`charged`、`policy_rejected`，不要用 `tool_trajectory.cost` 简单求和。
- 本地 ADK 2.9.2 在 `before_tool` 返回替代结果后仍可执行 `after_tool`。**研究层拒绝 submit 后不能让 c-interact 误设 `_submitted_this_phase=True`，也不能记成一次真实提交。** 这一点必须在研究版回调中显式处理；baseline 不改变。
- 不要给普通工具增加模型必须填写的 `task_id`。仍由 `ToolContext` 注入。
- 新的内部审查不另送一次隐藏的 `submit` 或 `execute`。所有环境动作走原工具与原费用。
- 第一版以顺序动作执行为目标。硬拦截版若不支持一轮多个工具调用，应在发起任何环境动作前识别批量响应并要求单步重试；不能先执行半批，再当作未发生。计入额外模型成本并限制重试。
- 原有 60 次回调上限、预算终止、c-interact 的阶段重试规则继续生效。内部审查也须有单独次数/token 上限，不能形成免费无限推理。

### 4.3 不必先改 ADK 源码

A/C 可以通过现有模型前、工具后回调完成；B/D 的检查也可通过工具前回调、独立 Python 模块接入。大部分设计不需要改 `system_agent/adk_runtime.py`。只有需要捕获最终文本、统计真实模型 usage、记录消息来源或做有界继续运行时，才扩展 runtime。

`state` 不会自动进入模型上下文；新增字段后须在模型前回调或 instruction 中显式展示。状态更新应使用 ADK 的 state/event 机制；不要把模块级全局变量当作每题记忆。

## 5. 方案 A：有界的信息获取控制器

### A1. 要解决的问题

Flash 已经能看见剩余预算，仍会花大量预算查知识。所以“把剩余预算打印得更醒目”不足以针对当前失败。

真正缺少的是：**我当前缺什么？它可能在哪个渠道获得？继续在同一渠道查，还有没有价值？**

`mental_9` 的 32 次查找和 `insider_8` 明知 OMI 不存在却没有问公式，都是这类问题。控制器应面向当前题目的信息缺口，不写死这些题号或指标答案。

### A2. 借鉴与差异

跨领域参考 BATS 的预算条件化规划，以及 INTENT 的面向昂贵工具调用的前瞻成本规划。我们借鉴资源分配的思想，不复现其全部搜索/学习系统。[BATS](https://arxiv.org/html/2511.17006v2)、[INTENT](https://arxiv.org/html/2602.11541v1)

拟议差异是针对 BIRD 的三种信息渠道——知识库、数据库探测、用户澄清——维护不同的可获取性状态，并把“关键缺口仍未解决”与预算关联。是否构成研究贡献还要与简单规则、BATS 风格提示和已有交互 SQL 方法比较。

### A3. 新状态

```python
# 拟议结构：每题初始化，不跨题复用
research_state["acquisition"] = {
    "gaps": {
        "metric_formula": {
            "importance": "blocking",  # 或 useful / optional
            "status": "unresolved",   # partial / resolved
            "kb_state": "not_tried",  # found / not_found / transport_error
            "attempt_signatures": [],
            "evidence_ids": [],
        }
    },
    "consecutive_no_progress": 0,
    "policy_notes": [],
}
```

`not_found` 表示这次具体检索没有结果，不表示世界上不存在定义。网络错误不应记成知识缺失。知识名称存在但定义被删，也不能靠名称自动推导公式。

第一版只区分四类缺口：指标定义、对象/统计粒度、筛选范围、输出要求；由主模型在开始时列出、后续回调更新。不要先写十几种细粒度类别。

### A4. 决策规则：先做能解释的启发式

1. 用已取得的知识名称和问题找相关条目，不按全部名称穷举。
2. 对同一缺口，一次明确 not found 后，允许一次有依据的替代名称查询；再次无结果，建议转为业务澄清。
3. 若已经付费取得完整知识集合，优先在已取得内容中定位；不能从磁盘补读被过滤掉的定义。首次取回内容可以作为本题内部观察，但不能给原工具提供免计费的重复外部请求。
4. 存在 blocking 缺口时，优先保护至少一次 `ask_user` 的 2 coins 和一次正常提交的 3 coins。先用 `reserve=5` 做开发初值；这不是论文证明的最优值。
5. 余额已经低于 5 时仍根据现有可用操作选择，**不能因 reserve 而禁止原版允许的最终免费提交**。
6. P1 未完成前不偷看隐藏 follow-up 内容或是否存在；可对所有任务设置统一的软保留策略，但要单独消融。P1 成功收到 follow-up 后再按实际新要求重新规划。

第一版在 `before_model` 中给出建议与原因，不硬禁用工具。之后若要硬控制，先只阻止“同 phase、同信息版本、相同参数、已得到相同 not found”的无意义重复；给一次纠偏机会，防止无限拒绝—重试。

### A5. 具体改哪些文件

| 文件 | 拟添加功能 | 输入 / 输出 |
| --- | --- | --- |
| **新建** `system_agent/acquisition_policy.py` | `observe_lookup()`、`update_gap_status()`、`recommend_next_action()` | 已有工具反馈与缺口状态 → 建议行动类别、理由、预算保留 |
| `system_agent/research_state.py` | 初始化 acquisition；规范化 not found / 错误 | 原始可见反馈 → 结构化观察 |
| `system_agent/research_hooks.py` | 工具后更新查找历史；模型前注入未解决缺口和行动建议 | 不直接发 HTTP |
| `system_agent/agent.py` | 研究版 instruction 要求每次探索对应一个缺口；选择研究回调 | 保持九个环境工具不变 |
| `orchestrator/ainteract.py` | 初始化状态、结果输出增加 `acquisition_trace` | 用于分析何时从查找切到澄清 |
| `shared/config.py` | 配置 variant、重复阈值、软保留值 | 默认 baseline 不启用 |

**最小版只做三件事：同一缺口查找去重提示、连续无效后转问用户、保护一次问答预算。** 暂不增加 LLM 调用；缺口抽取不可靠时先按检索名称跟踪，标记这是更简单的对照。

### A6. 如何判断有效

比较：原版 → 仅预算提示 → 固定“最多两次无效查找”规则 → A 完整版本。原版已有预算提示，因此第二项应明确只是更强提示，不把已有功能算成新增贡献。

看 P1/P2/reward，也看关键缺口首次被问及时的余额、同一缺口重复查询次数、每 coin 新获得的有效信息。信息是否有效需要抽样人工审核，不能完全相信 agent 自评。

风险：过早放弃 KB、过度依赖不可靠 simulator、节省预算却缺知识。若完整控制器不优于简单限次规则，应优先保留简单规则，降低贡献主张。

## 6. 方案 B：带来源和依赖的意图状态，以及受约束的修改

### B1. 要解决的问题

`fake_8` 展示指标和排名指标不同步，说明一个用户事实可能影响 SQL 中多个位置；`alien_7` P2 丢旧约束，说明“保存上轮 SQL”不等于“知道哪些语义要保留”。

设计核心是：**每条决策知道自己依赖什么；新证据到来时，受影响的决策标为需要重检，其他条件继续保留。**

### B2. 跨领域来源与不能夸大的地方

借鉴经典 Truth Maintenance System：保留结论的依据，在依据改变时修订依赖结论。这是一般 AI 的信念维护思想，不是新的记忆概念。[Doyle, 1979](https://www.sciencedirect.com/science/article/pii/0004370279900080)

本文的迁移提议是把“用户要求—业务解释—SQL 实现位置”连起来，并引入 Phase 1/2 的生效范围。与长期经验检索不同，但与 MIRA 的证据化局部修复、SQLens 的细粒度检查、EditSQL 的上下文编辑有实质交叉。**只有一个事实清单加检查 prompt，最多算工程增强；依赖传播和受控修订是否有额外收益，需要消融。**

### B3. 拟议数据结构

```python
research_state["intent"] = {
    "version": 1,
    "facts": {
        "f_metric": {
            "value": "用户指定的指标 M",
            "status": "supported",   # tentative / disputed / superseded
            "source_ids": ["ask_3_answer"],
            "scope": "task",         # phase1 / phase2 / task
        }
    },
    "decisions": {
        "d_display_metric": {"depends_on": ["f_metric"], "sql_locations": ["projection.metric"]},
        "d_rank_metric": {"depends_on": ["f_metric"], "sql_locations": ["window.rank.order"]},
    },
    "dirty_decisions": [],
    "phase1_checkpoint": None,
    "change_log": [],
}
```

`source_ids` 引用真实可见消息。`supported` 只表示有来源支持，不能命名为 `true`，因为 simulator 也可能回答错误。

模型负责从文字提出事实与依赖，Python 负责验证来源 ID、维护版本和计算依赖闭包。LLM 不能凭自己声明“已确认”就把假设升格。

### B4. 执行过程

```mermaid
flowchart LR
    O[新用户回复或知识结果] --> F[提取有来源的事实变更]
    F --> G[计算受影响的决策]
    G --> P[生成修改范围与保留条件]
    P --> S[生成或修订 SQL]
    S --> C[检查依赖覆盖与范围外变更]
    C --> T[通过原 submit_sql 提交]
```

以 `fake_8` 的失败类型为例：

1. 旧假设是指标 A；展示值、排名、过滤阈值分别依赖它。
2. 用户否定 A、要求 M。将旧事实设为 `superseded`，不能只追加一句新摘要。
3. 展示、排名和相关筛选进入 `dirty_decisions`。
4. 模型需要逐项重新给出映射；检查器看到排名仍引用 A 时提示“同一个指标依赖未完成更新”。
5. 不用参考 SQL，也不用知道正确公式，仍能发现内部不一致。

P2 则生成一个明确的变更清单：

```text
add：本轮新增限制
replace：本轮明确替换的阈值/范围
remove：本轮明确取消的旧限制
preserve：未被覆盖且作用域仍有效的旧要求
unknown：无法确定是否继承，需要澄清或保留为假设
```

`alien_7` 类型的 follow-up 若只是改 AOI 阈值、增加条件，未被取消的旧要求应进入 preserve。若用户要求一个全新的统计对象，则不能机械保留全部旧 WHERE。P1 通过也不能证明每条中间推理永远正确，只能作为当时 SQL 通过测评的记录。

### B5. 具体改哪些文件

| 文件 | 拟添加功能 |
| --- | --- |
| **新建** `system_agent/intent_state.py` | `extract_fact_updates()` 只读公开上下文；`apply_updates()` 校验来源与版本；`affected_decisions()` 计算依赖闭包；`build_phase_delta()` 区分 add/replace/remove/preserve |
| **新建** `system_agent/sql_contract.py` | `index_sql_usage()` 用 `sqlglot` 解析 SQL 使用位置；`check_dependency_coverage()` 检查需要同步修改的用途；`diff_semantics()` 输出候选变更清单。遇到不支持的语法返回 unknown |
| `system_agent/research_hooks.py` | ask/knowledge 后更新事实；模型前展示 dirty 列表与 preserve；提交前可选检查 |
| `system_agent/tools.py::submit_sql()` | 保存该次提交前的 phase、候选 SQL 与返回状态；P1 成功时保存本 agent SQL 和 intent checkpoint，并记录实际返回的 follow-up；不从 dataset 读未来阶段 |
| `orchestrator/cinteract.py::run_single_task()` | P2 消息明确标记为 follow-up；与工具侧 phase 事件去重，不能每次重置 checkpoint |
| `orchestrator/ainteract.py`、`orchestrator/cinteract.py` | 初始化 intent；输出 `fact_updates`、`sql_change_reports` |
| `system_agent/agent.py` | 要求修订回应 dirty 决策、保留未受影响语义；接入研究 hooks |

注意 `tools.submit_sql()` 当前成功后会更新 `current_phase`。记录 P1 checkpoint 时应先保存 `phase_before_submit`，否则工具后回调可能把 P1 SQL 错归 P2。c-interact 初始 state 没显式设置 `current_phase`，研究状态也应初始化为 1。

### B6. 第一版不要做万能 SQL 等价检查器

先支持三类容易验证的规则：

- 同一个指标在 SELECT、ORDER BY、窗口排名中的一致使用。
- follow-up 前后已有谓词的保留、替换与删除清单。
- 输出列/JSON 键是否覆盖明确来源中的要求。

AST 不等于语义证明。重写为等价 CTE、别名变化、JOIN 改写可能导致结构差异；第一版对不能确定的情况给 warning，不自动判错。DDL、函数和复杂多语句任务先降级为文本契约与 unknown，不要求 sqlglot 完全理解。

建议从只记录检查报告的观察模式开始，确认误报；再启用每个候选最多一次内部重写机会。检查器不能无限拒绝提交，余额不足也不能卡住原版的免费提交出口。

### B7. 成本、指标与消融

最小开销：只有出现新事实/否定/阶段变化时，做一次有 token 上限的结构化抽取；AST 检查不调用 LLM。普通 lookup 不触发整段对话重摘要。可设置每题额外抽取次数上限，失败时保留旧状态并标 unknown。

需要比较：

1. 原版。
2. 同样长度的“已确认条件清单”提示。
3. 结构化事实表，但没有依赖边。
4. 完整 B：来源、依赖失效传播、phase 作用域。

关注“已确认条件遗漏率”“一次事实变更后是否全部同步”“P2 未声明删除的旧条件丢失率”“审查误报与引入错误的比例”。既报告全任务 P2，也报告 P1 成功后的条件 P2；不同方法进入 P2 的题目可能不同，不能只用条件比例宣称因果收益。

B 的主要风险是把错误回复牢固地保护起来。因此要支持 disputed 和撤销，不把“保持旧约束”写成无条件规则。这也是 C 可以与 B 配合的原因。

## 7. 方案 C：澄清回复的语义验收与有界追问

### C1. 要解决的问题

默认 `ask_user()` 拿到 answer 就返回给模型，主要记录问答。它没有显式判断：我问的是公式，用户是否只说了组成部分？我问的是统计范围，用户是否只回答了阈值？

C 把一次信息获取拆成：**说明需要什么 → 收到回答 → 检查缺口是否补齐 → 更新状态或选择追问。**

`cybermarket_1` 已有轨迹说明补问权重有时能得到关键内容；`archeology_1` 说明回答非空却仍可能缺计算规则。最新两阶段 simulator 的标签/fallback 问题则要求区分“没有实质回答”和“回答了但不完整”。

### C2. 跨领域来源与适用边界

借鉴对话研究中的 grounding：交流是否完成，取决于是否建立了足够共同理解，不能只看是否发生了话轮。[Clark & Brennan, 1991](https://web.stanford.edu/~clark/1990s/Clark%2C%20H.H.%20_%20Brennan%2C%20S.E.%20_Grounding%20in%20communication_%201991.pdf)

这里提出的是 agent 侧的信息验收状态机，不修改 simulator 的两阶段 prompt、解析和原始回复。它能检查完整性、相关性和明显冲突，**不能判断所有用户业务答案是否符合隐藏真相**。例如 simulator 把 `1-x` 说成倒数，若 agent 没有其他可见证据，不可能仅凭验收器可靠纠正。

### C3. 状态与判定

```python
research_state["clarification"] = {
    "pending_request": {
        "gap_id": "metric_formula",
        "requested_parts": ["operands", "operators", "weights", "units"],
        "question_id": "ask_4",
    },
    "answer_checks": [],
    "followup_count_by_gap": {},
}
```

`requested_parts` 依赖所问内容。例如公式不一定需要单位或权重；不要对所有答案机械要求四项。查是否需要某项本身也可能不确定，应允许 `not_applicable`。

拟议状态：

| 状态 | 含义 | 下一步 |
| --- | --- | --- |
| `sufficient` | 回答已覆盖本次实际要求 | 记录来源，更新对应缺口 |
| `partial` | 有用，但仍缺某个部分 | 如果值得且预算允许，单独追问缺失部分 |
| `nonanswer` | 标签、固定 fallback、无关内容或明确未回答 | 不把问题标为已解决；考虑换一种表达 |
| `conflicting` | 与另一条可见证据存在冲突 | 保留双方来源，必要时请用户澄清冲突 |
| `uncertain` | 检查器无法可靠判定 | 显式保留不确定性，避免自动补全 |

对比两种处理：

```text
收到“指标由长度、次数、风险和完整度组成”
旧路径：模型可能直接猜权重并写 SQL
C 路径：记录这些是成分信息；公式仍 partial，缺 operators / weights
       下一步只询问如何组合，不能自动填入历史样例中的权重
```

### C4. 如何追问才不变成“向 simulator 索取答案”

追问围绕公开任务中的业务含义，例如：“这些因素分别怎样组合，是否存在权重或反向项？”

不要求 simulator 给参考 SQL、测试断言、隐藏正确结果。对于新建对象的名字、用户指定 JSON 键等公开输出要求，可以询问需求；对于已有数据库结构，优先通过 schema 工具获得。

第一版每个缺口最多一次针对性补问；确实需要更多时由正常控制器决定，并计费。无论追问为何，**必须再次通过 `ask_user`，正常扣 2 coins / 消耗 c-interact 话轮**。不能在 `ask_user()` 函数内部偷偷循环请求 `/ask`，把两三次交互算一次。

### C5. 具体改哪些文件

| 文件 | 拟添加功能 |
| --- | --- |
| **新建** `system_agent/clarification_guard.py` | `describe_information_need(question, context)` 记录本次目标；`assess_answer(question, answer, expected_parts, visible_evidence)` 返回状态、缺项、来源片段；`suggest_followup()` 生成一个有针对性的问题 |
| `system_agent/research_hooks.py::before_tool()` | 在正常 ask 执行前记录提问目标；被预算拦截时不能记为用户已回答 |
| `system_agent/research_hooks.py::after_tool()` | 只对实际收到的 answer 验收；保留原文，并把完整性诊断送入下一次上下文 |
| `system_agent/tools.py::ask_user()` | 如需稳定 observation ID，可在保存原问答时一并记录 ID、phase；不改变 simulator 请求内容和 answer 本身 |
| `system_agent/agent.py` | 强调 partial 不等于 resolved；追问只补缺项，不能把猜测写成用户确认 |
| 两个 orchestrator 的结果收集 | 导出 `clarification_checks`，包括判定、是否实际追问、额外费用 |

先做规则版：识别空文本、原版固定 fallback、明显 action-only。再做语义版：给结构化检查器看提问、原始回答和必要上下文，要求返回短 JSON，不让其访问数据库或隐藏任务字段。

检查器若调用 `shared.llm.call_llm()`，应显式传 system-agent 模型和固定参数，记录额外 usage；不要误用 simulator 专属模型配置。实际统计 token 需扩展调用包装器，当前普通函数只返回文本。

### C6. 如何验证它不是只让 agent 多问几次

比较：原版、简单“回答不清就再问一次”提示、固定每次补问一次、C 的选择性补问。固定补问版本可能成本高，但能检验收益是否只来自更多用户交互。

指标包含每次 ask 获得的需求覆盖、新增加的问答次数、无效补问率、把 partial 错判 sufficient 的比例、P1/P2 和总成本。对验收器单独抽样人工标注；标注者可以看完整研究材料做离线审查，但这些材料不回流给在线 agent。

风险：检查器误判“没说权重就一定不完整”、把正确简洁回答判为不足、追问耗尽预算、simulator 对改写更不稳定。若在更可靠的 simulator 下收益消失，应把结论限定为交互鲁棒性，不声称普遍提升 SQL 推理。

C 与已有 EIG 澄清的区别是检查回答之后的信息完成程度；但不能由此断言无人做过回答质量检查。这一方向需要继续查对话状态跟踪、clarification repair 文献。

## 8. 方案 D：有预算的主动失败诊断

### D1. 要解决的问题

收到 `Your SQL is not correct` 后，默认 agent 会尝试修复，但反馈没有指出哪个部分错了。修改连接、排序、公式可能恰好修好，也可能破坏本来正确的内容。

D 要求先给出少量**可以被证据区分的失败假设**，再选择一个便宜行动收集信息。不是让模型写更长反思，也不是每轮生成十条 SQL 轮流 submit。

### D2. 借鉴来源与重合边界

跨领域可借鉴 MedAction 的主动诊断思路：先提出候选解释、选择检查、根据得到的证据更新判断；其论文主要是轨迹生成与训练方法，本文只迁移行动与证据对应的设计思想，不声称复现其算法或医学性能。[MedAction](https://arxiv.org/html/2605.07305v1)

通用 agent 的 LATS 用树搜索组织行动和反馈，Reflexion 用文字反馈改进后续尝试。本文不直接搬完整树搜索：BIRD 的每次环境动作都收费，提交还可能改变阶段，不能免费回退和重放环境。[LATS](https://arxiv.org/abs/2310.04406)、[Reflexion](https://arxiv.org/abs/2303.11366)

SQL 领域已有 SQLens 的信号诊断、CHESS 的测试、APEL 的区分性输入。因此 D 的研究问题只能收窄为：**面对成本不同、可观测性不同的 SQL 错误假设，是否应该先查证，哪些时候应直接修改或停止？** 它是四套中最不适合直接宣称新颖的一套。

### D3. 先分类“能从哪里知道答案”

| 假设类型 | 示例 | 合法取证方式 | 不能得出的结论 |
| --- | --- | --- | --- |
| 明确执行错误 | 列不存在、类型转换失败 | 已有 DBMS 错误 + 已获取 schema | 不能把每个 generic fail 都当执行错误 |
| 数据结构/连接现象 | JOIN 放大了行数、存在无子记录的实体 | 正常付费 `execute_sql` 做 COUNT、NULL/匹配覆盖探测 | 出现 fan-out 不等于业务上一定不允许 fan-out |
| 用户意图未明确 | 按记录计数还是按用户去重；排名依据哪个指标 | 正常付费 `ask_user` | 数据分布不能决定用户想要哪个口径 |
| 可见契约违例 | 用户要求三个输出字段，SQL 只有两个 | 静态 SQL/JSON 检查 + 原需求来源 | 不需要数据库结果也能发现，但不能推断其他部分正确 |
| 无法定位 | 当前 SQL 可执行，只有 generic fail | 保持多个假设，或针对未确认需求提问 | 不能从失败标签反推隐藏参考公式 |

这张分类表是控制器的关键：只做真正能验证所关心命题的探测。

### D4. 示例：COUNT 的问题怎么查

若存在“每个实体出现多次”的疑问，可以通过原 `execute_sql` 比较连接前后行数和唯一实体数。探测结果只支持“连接确实放大行数”这一事实。

要决定结果应该用 `COUNT(*)` 还是 `COUNT(DISTINCT entity_id)`，还需要公开问题或用户回答对统计单位的规定。**不能因为 DISTINCT 更少、更好看，就认定它正确。** 历史 `news_9` 就提醒我们这一点。

如果明确需求是“每个实体仅计一次”，探测和需求共同支持修改计数；若需求不明确，应问统计单位，而不是盲换聚合。

### D5. 状态与规则

```python
research_state["diagnosis"] = {
    "failed_candidate": "sql_hash",
    "phase": 1,
    "hypotheses": [
        {
            "id": "h1",
            "claim": "同一实体在连接后被重复计数",
            "status": "untested",
            "test_action": "execute_sql",
            "expected_observations": ["唯一实体数不变而行数增大"],
            "does_not_establish": ["用户是否要求去重"],
        }
    ],
    "tested_actions": [],
    "repair_history": [],
}
```

第一版每次失败最多保留三个假设，每轮最多做一个区分性行动，最多两次诊断循环。它们是开发初值，不能根据最终测试题单独改参数。

有直接证据的语法修复优先于泛泛假设搜索。预算不足时不再测试，只依据当前已获得信息生成最佳候选，保留原版提交出口。若没有可执行、可解释的测试，返回 `unknown`，不能编造观测。

对重复候选，用“phase + 环境版本 + SQL 指纹”识别。相同 SQL 在 P1/P2、数据库变化或时间条件变化后不一定等价；不要全局禁止。最小版只提醒完全相同 SQL 在相同上下文中刚刚失败，生成新候选；不自动额外提交。

### D6. 具体改哪些文件

| 文件 | 拟添加功能 |
| --- | --- |
| **新建** `system_agent/diagnostic_policy.py` | `classify_feedback()` 区分执行错/generic fail；`propose_hypotheses()` 最多三个；`choose_probe()` 根据可观测性与预算选一个动作；`update_hypotheses()` 只消费真实工具证据 |
| `system_agent/sql_contract.py` | 可选复用 B 的投影/谓词/计数静态检查；即使不启用 B，也可仅实现少量明确规则 |
| `system_agent/research_hooks.py` | submit 失败后初始化诊断；模型前只展示当前要验证的假设与探测约束；工具后更新，不直接执行额外查询 |
| `system_agent/tools.py::submit_sql()` | 记录结构化结果、候选 SQL、提交前 phase；保持 evaluator 回应原义 |
| `system_agent/agent.py` | 研究版指令要求修复理由引用观察 ID；允许 `unknown`，不奖励虚构的根因解释 |
| `orchestrator/ainteract.py` | 输出 probe、假设更新、SQL 修改和费用，使诊断成本可独立分析 |

第一版的探测只是建议给主 agent，最终仍由它调用现有工具。更严格的控制器可以检查下一动作是否符合当前 probe 计划，但这属于后续版本，需处理批量动作与拒绝重试。

不能在本地私建数据库执行候选绕过收费；不能用 oracle 模式获取正确性信号。管理类任务也不能借探测之名把写操作藏进允许的 SQL 前缀。第一版 D 只做公开环境允许的只读探测与静态检查；DDL/DML 主要通过公开需求与 schema 检查，保留原提交路径。

### D7. 验证与否证

必须比较“同样额外模型 token 的直接反思”“静态检查后修复”“D 主动探测后修复”，否则无法分清是诊断策略还是更多计算带来的收益。

指标：每次修复是否有新证据、generic fail 后无依据改变已确认条件的比例、重复提交率、探测可执行率、每次有效修复消耗的 coins/token，以及最终 P1/P2。根因解释是否正确要抽样离线审查。

若探测经常只是验证数据库能执行、却不能区分业务假设，或者其费用挤掉了澄清和提交，D 就不值得继续扩展。不要为了保住方法而把探测免费化。

## 9. 一个可单独做的工程对照：有界继续运行

这不是主要研究方案，只针对历史 Kimi“还有预算但停在文本”的现象。Flash 36 题已有提交且主要耗尽预算，对它的预期收益较低。

拟在 `system_agent/adk_runtime.py::run_turn()` 中，当 a-interact 的 `run_async` 正常结束、`task_done=False`、预算非负、原轮次上限未到时，最多发送一次简短继续消息，要求选择正常工具完成剩余工作。保留原 session 和计数，不重置预算。

**不要用于 c-interact。** c-interact 在 submit 后有意结束一次运行，继续它会破坏外层阶段控制。也不能对网络异常、超时、已成功提交重放未知状态的请求。

额外继续次数、消息、模型成本须单独记录。把它作为 baseline+ 工程对照，避免把“修复意外停止”混成 B/C/D 的研究贡献。

## 10. 如何分阶段实施，避免四套一起做后无法解释收益

### 第一阶段：先建立可重复的当前 baseline

冻结同一任务划分、system model、推理参数、simulator 模型与 prompt 版本、依赖版本、patience、评分器和日期策略。按当前配置重新跑 baseline；旧 Flash 36 题用于故障定位，不直接与新方法成绩相减。

环境问题有两种合法处理：保留原协议并明确限制，或者建立统一修复后的协议。无论选哪种，baseline 和所有方法保持一致。不要只修新方法的环境。

### 第二阶段：先试 A 的小版本

因为它最直接针对 Flash 的行为，且可先不增加模型调用：

```text
baseline
baseline + 无效检索限次提示
A：缺口状态 + 换渠道建议 + 软预算保护
```

若只减少 lookup 而不提升成功率，检查节省的预算是否转化为有效澄清/执行，而不是只多提交几次。

### 第三阶段：以 B 为主要研究候选

```text
baseline + prompt 中的条件检查清单
B-small：有来源事实表
B-full：事实表 + 依赖传播 + phase 作用域
```

先只支持指标一致性、谓词保留、输出要求三个检查族。证明依赖机制有帮助后，再扩展粒度、聚合、DDL 语义。

A 和 B 各自有效后再做 `A+B`。不要默认二者效果相加：A 改变了观察到的内容，可能让 B 更容易或更难工作。

### 第四阶段：C 作为交互鲁棒性模块

先独立测试 C 对 partial/nonanswer 的判别与成本，再测试 `B+C`。可以在第二种固定 simulator 配置下做敏感性实验，但两边都要重新跑 baseline，不把 simulator 变强归因于 C。

### 第五阶段：有证据表明仍存在大量盲修时再做 D

若 A/B/C 已经让主要问题变成稳定的 SQL 结构错误，D 才有更清楚的目标。不要一开始实现全量 MCTS、并行多候选、跨题长期记忆库；当前证据不足以证明这些开销必要。

## 11. 文件级总清单：哪些是方法，哪些是测量

下表是未来实现时的导航，不要求一次创建全部文件。

| 文件 | 最小作用 | 关联方案 |
| --- | --- | --- |
| `system_agent/agent.py` | variant 选择、研究指令、hooks 绑定 | 全部 |
| `system_agent/research_state.py`（拟新增） | 每题状态、观察 ID、观察类型规范化 | 全部 |
| `system_agent/research_hooks.py`（拟新增） | 将研究逻辑接入三个回调阶段 | 全部 |
| `system_agent/acquisition_policy.py`（拟新增） | 无效信息源识别、换渠道和预算建议 | A |
| `system_agent/intent_state.py`（拟新增） | 事实来源、依赖闭包、阶段变更 | B |
| `system_agent/sql_contract.py`（拟新增） | 有限范围的 SQL 结构检查，允许 unknown | B，可被 D 复用 |
| `system_agent/clarification_guard.py`（拟新增） | 回复完整性判别和有界追问建议 | C |
| `system_agent/diagnostic_policy.py`（拟新增） | 失败假设、证据获取计划、更新 | D |
| `system_agent/tools.py` | 记录实际观察/submit 结构化反馈；不扩大环境权限 | B/C/D 按需 |
| `system_agent/callbacks.py` | 保留原计费和停止语义；供研究 hooks 包装或抽取共用逻辑 | 全部 |
| `system_agent/callbacks_cinteract.py` | 保留阶段停止；研究内部拒绝不算已提交 | B/C 按需 |
| `system_agent/adk_runtime.py` | 真实模型事件与 usage 记录；可选 a-interact 有界继续 | 测量与工程对照 |
| `shared/llm.py` | 内部抽取/检查调用的统一模型参数、超时、usage；不能误用 simulator | B/C/D 按需 |
| `shared/config.py` | variant、固定阈值和内部调用上限 | 全部 |
| 两个 `orchestrator/*.py` 的单题函数 | 初始化研究状态，导出研究轨迹，不传隐藏数据 | 全部 |
| `orchestrator/runner.py` | 保存 variant、参数、模型/依赖版本和配对结果 | 实验记录 |
| `scripts/analyze_agent_variants.py`（拟新增） | 离线按 task_id 对齐新结果、汇总成本与行为指标 | 测量 |

无需为这些方案修改 `user_simulator/prompts.py`、评分器、奖励表、原始费用、数据库重置或 ADK 的 `site-packages`。如果后来确实修改环境，作为另一个明确版本比较。

## 12. 测试和评估要回答哪些问题

### 12.1 方法接线是否正确

未来实现时建议使用少量人工构造的状态/反馈做针对性验证，**不要用测试集隐藏答案写规则**：

- not found 与网络错误不会混为一类；A 的重复记录不会跨任务/phase 泄漏。
- 一个事实被替换后，所有依赖决策变 dirty，无关事实仍有效；B 不把合法新任务强行套回 P1。
- C 对 partial 不会补出没有依据的权重；每次真正追问都会通过正常工具计费。
- D 对 generic fail 返回候选/unknown，不自动声称某个错误原因已被确认。
- 内部拒绝不会扣环境费用、不会误标 c-interact 已提交；实际 HTTP 操作仍只扣原版费用。
- 预算不足的最终提交、原轮次停止、P1→P2 切换仍按原协议运行。
- 解析失败、LLM 检查超时等异常可以降级回正常 agent；降级次数必须记录，不能悄悄拿 baseline 行为冒充新机制。

现有 [user_simulator/test_server.py](../user_simulator/test_server.py) 对若干 system-agent 文件做原版字节一致性检查。有意修改研究 variant 后，失败可能只是“已不等于原版”。需要保留 baseline 一致性验证与研究功能测试的区分，不能简单删除所有协议测试。

### 12.2 先确认机制，再确认成绩

| 问题 | 证据 |
| --- | --- |
| 分数是否提高 | 同一任务 ID 配对的 P1、P2、reward，新增成功与新增失败分别统计 |
| 是否只是多花钱 | 实际模型调用、输入/输出 token、延迟、bird-coins；内部调用单列 |
| 是否改变了预期行为 | A 的换渠道、B 的依赖同步、C 的信息补齐、D 的证据驱动修复分别记录 |
| 是否只在这 36 题有效 | 冻结方案后在未参与设计的样本验证；能按数据库划分更利于检查迁移 |
| 是否依赖某个 simulator 的表达习惯 | 在第二个固定 simulator 配置下重跑配对 baseline/方法，报告差异 |
| 是否只是更多提示或反思 | prompt-only、相同额外模型预算、简单限次规则等对照 |

可用按 task_id 的配对 bootstrap 估计 reward 差异区间；对二值阶段结果可报告配对胜负和 McNemar 检验。小样本不确定性通常较大，不因几个题改善就给出稳定排名。

端到端轨迹随动作改变，后续 simulator 回答也会改变，不能把旧日志直接替换一个动作就当真实新成绩。离线回放可验证状态更新和检查器行为，最终收益仍需新的真实运行。

token 统计不能只数 `model_turns`，日志事件也可能重复；上一份说明文档已指出 c-interact 事件汇总的问题。方法实验开始前，要让真实请求/usage 与研究模块调用能被区分。

## 13. 推荐的研究主张与停止条件

较适合以 B 为中心的研究问题：

> 在有成本的多轮数据库交互中，基于证据来源和依赖关系的局部意图修订，能否减少需求遗漏与无依据 SQL 变化，并在受控推理成本下提高任务完成率？

A 可以是独立的低成本改进与强对照，也可以作为 B 的信息获取前端。C 可用于研究不完整用户反馈，D 更适合作后续探索。

不宜直接使用的主张：

- “首次给 Text-to-SQL 加长期记忆、反思、多 agent、测试或信息增益。”已有直接相关工作。
- “用了依赖图就有因果保证。”图中的语义映射仍可能由 LLM 错误提取。
- “改进可以解决 simulator 错误和数据标注冲突。”在线 agent 不拥有隐藏真相，最多检测可见冲突与保留不确定性。
- “推理没有多花 bird-coins，所以零额外成本。”内部模型检查仍有 token 与延迟成本。

每个方向都有应当接受的否证结果：A 不优于简单限次；B 不优于相同长度的条件清单；C 的追问成本超过补齐信息的收益；D 的探测不能区分假设。如果出现这些结果，优先保留较简单的实现，并缩小研究主张。

## 14. 文献阅读路径

按与你的实现最接近的顺序读，不必先读完所有论文：

1. **避免直接重复：** 两篇 MERIT、MIRA；重点看记忆存什么、何时检索、如何判定可用，而不是只看名字和分数。链接见第 2 节。
2. **做 A：** [BATS](https://arxiv.org/html/2511.17006v2) 的预算规划/验证部分、[INTENT](https://arxiv.org/html/2602.11541v1) 的成本规划；再对照 [交互 SQL 的 EIG 方法](https://arxiv.org/abs/2507.06467)。
3. **做 B：** [Truth Maintenance System](https://www.sciencedirect.com/science/article/pii/0004370279900080) 的依赖与修订思想；对照 [MIRA](https://arxiv.org/html/2608.06950v1)、[SQLens](https://arxiv.org/abs/2506.04494)、[EditSQL](https://arxiv.org/abs/1909.00786)，具体写出仍重合和可能不同的机制。
4. **做 C：** [Grounding in Communication](https://web.stanford.edu/~clark/1990s/Clark%2C%20H.H.%20_%20Brennan%2C%20S.E.%20_Grounding%20in%20communication_%201991.pdf)，关注“收到信息”和“建立足够理解”的区别。
5. **做 D：** [MedAction](https://arxiv.org/html/2605.07305v1) 的行动—证据关系，[SQLens](https://arxiv.org/abs/2506.04494) 的诊断与修复；[LATS](https://arxiv.org/abs/2310.04406) 只用于理解搜索结构，不默认照搬整个算法。

文献提供的是思路和已有工作的边界。本文四套方案的具体状态字段、文件拆分、启发式阈值与组合方式，是结合本仓库失败轨迹提出的设计建议，尚未实现，也没有实验结果支持其优于现有方法。
