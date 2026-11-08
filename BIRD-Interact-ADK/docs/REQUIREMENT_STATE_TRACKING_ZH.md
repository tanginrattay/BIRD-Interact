# Requirement State Tracking 实现与验证

本次是独立 State 机制实验，日期 2026-11-08。分支为 `state/requirement-tracking`，从干净的 `main@8138403` 创建；该 main 与本地 `origin/main` 一致。原 `prompt/exploration-policy@775e5b0` 未合并、修改或删除。本次未创建 commit。没有引入 Planner、独立 Controller、Memory Retrieval 或 SQL 自动对应机制。

## 1. 实际修改的文件

| 文件 | 职责 |
| --- | --- |
| `system_agent/requirement_state.py`（新增） | 五字段 Requirement 加内部 ID；严格验证 JSON 更新；revision 校验；原子 upsert；禁止删除/改名；规范化文本去重 |
| `system_agent/requirement_tracking.py`（新增） | 同一个 Agent 模型的内部需求整理调用；可见证据序列化；校验和有限纠正；State 注入正常决策；更新审计与 token/耗时记录；混合提交批次保护 |
| `system_agent/agent.py` | 在 a-interact/c-interact 中组合原有停止回调与 State 整理回调，接入提交批次保护；原有两份环境任务 prompt 未修改 |
| `system_agent/adk_runtime.py` | 在 Session 创建时隔离 State，覆盖不可信 task_id；同一任务的初始化/重置/运行串行化；通过 ADK Event 保存运行事件 |
| `orchestrator/ainteract.py`、`orchestrator/cinteract.py` | 将最终 State、更新历史和错误写进评测结果 |
| `orchestrator/runner.py` | 默认结果目录增加 `requirement_tracking_v1/`，metadata 标识 State 实验；oracle 使用独立 `oracle/` 目录 |
| `tests/test_requirement_tracking.py`（新增） | 真实 ADK Runner + 可控模型/HTTP 的离线验证 |
| `tests/test_requirement_tracking_live.py`（新增） | 显式开启的真实模型 smoke，环境服务用合成 fixture |
| 本文与 `docs/requirement_tracking_smoke/` | 实现说明、测试摘要及完整可检查的 smoke 证据 |

没有修改 `system_agent/tools.py`、两套预算/轨迹 callbacks、DB evaluator、用户模拟器或此前实验结果。内部更新没有注册为 FunctionTool。

## 2. 数据结构

Session 普通作用域键 `requirement_state`：

```json
{
  "task_id": "example",
  "revision": 2,
  "requirements": [
    {
      "id": "r1",
      "requirement": "Return 10 chains",
      "category": "user_semantics",
      "status": "resolved",
      "value": "10 (source: user)",
      "priority": 0
    },
    {
      "id": "r2",
      "requirement": "Determine TCR formula",
      "category": "knowledge",
      "status": "candidate",
      "value": "TCR = total/capacity; applicability unconfirmed (source: KB)",
      "priority": 3
    }
  ]
}
```

每项仅增加内部稳定 `id`。Category、Status 严格限定为任务要求的四种值，priority 为严格整数；`resolved` 与 `priority == 0` 必须双向对应，其他状态必须为 1–3。候选/冲突/已解决必须有非空 Value，冲突 Value 必须包含 `|`。多个候选使用 `&`；来源保存在 Value 中。不同字段互不替代，例如 KB 知识得到用户确认后 Category 仍可为 knowledge。

Runtime 另保存 `requirement_state_history` 和 `requirement_state_error`：它们是运行审计数据，不是新的需求研究字段。历史包含每次成功/失败整理的 revision、条目变化前后、变更解释、验证错误、模型 token usage 与耗时。State 正文不截断；原有工具轨迹仍沿用原先预览长度。

## 3. 完整运行流程及更新协议

1. `/init_session` → `AdkRuntime.init_session()`：为 `(mode, task_id)` 创建独立 ADK Session，写入 revision 0 的空容器；尚未调用模型，因此此时不声称已识别任务需求。
2. `run_turn()` → `Runner.run_async()`：ADK 组织 instruction、对话及工具结果，进入 `before_model_callback`。
3. 先调用原有 a/c 模式停止回调。若任务结束、轮数耗尽或原有预算规则要求停止，保持原有终止行为，不额外调用需求整理模型。
4. 否则调用内部需求整理 pass。首次正常决策前初始化所有独立可检查约束，包括已经明确的数量、排序、输出列等。指标公式与 schema 映射分开记录；任务约束不是按每个单词机械拆分。
5. 内部请求没有工具，使用与 Agent 完全相同的模型实例，输入为当前 State 和实际可见的对话/工具响应，以及 c-interact 已提供的 schema/知识。不会把完整 Session、hidden ambiguity、ground truth SQL 或测试用例送入整理请求。
6. 模型向 Runtime 返回以下 JSON，**这就是 Agent 的 State 更新通道**：

```json
{
  "base_revision": 2,
  "upserts": [
    {
      "id": "r2",
      "requirement": "Determine TCR formula",
      "category": "user_semantics",
      "status": "resolved",
      "value": "TCR = total/capacity; user confirms applicability (source: user & KB)",
      "priority": 0,
      "reason": "User explicitly confirms this KB formula applies to the current task."
    }
  ]
}
```

`reason` 是更新协议的审计解释，保存历史，不进入五字段 Requirement。首次必须返回至少一项需求；后续无变化可返回空 upserts。未出现在补丁中的旧需求保留。已有 ID 的 requirement 文本不能改名；新的需求使用新 ID。只在实际数据改变时增加 revision。

7. Pydantic 拒绝非法枚举、未知字段、错误类型、非法 priority/status、重复 ID、同名需求、过期 revision 和跨任务补丁。整个补丁验证完成前不写入 State。Runtime 对 Requirement 文本做 NFKC、大小写与标点规范化去重；语义改写重复由模型识别。
8. 校验成功后对 `callback_context.state["requirement_state"]` 做顶层赋值，由 ADK 捕获 `EventActions.state_delta`。最新 snapshot 通过 `llm_request.append_instructions()` 注入当前正常决策请求。模型决定下一步行动，Priority 仅供参考。
9. 环境工具执行并返回后，ADK 下一次决策前重复整理，从而处理新 schema、KB 定义、用户回答、错误与 follow-up。同一回复包含多个查询工具时，在整批返回后的下一次决策统一整理。
10. `submit_sql` 前的正常决策已经读取并复查全部当前需求。注入指令要求逐项检查 SQL；没有自动 SQL 与 Requirement 对应验证，也不强制所有项 resolved 后才允许按原预算规则尽力提交。禁止把 submit 与其他工具放在同一个批次，否则该批次全部停止、不扣费，并保存错误，避免 SQL 使用尚未整理的新回答。
11. Runner 保存事件中的 state_delta；新一次 `get_session()` 和下一次 `run_turn()` 读取同一个已保存 State。orchestrator 将 State/历史写入结果 JSON。Runtime 原来直接给 session 副本赋值保存 `adk_events` 的代码也改为 `append_event`。

非法 JSON/字段/更新最多进行一次纠正，即每次整理最多两个请求；两次均失败，保存错误与失败审计、保留旧 snapshot，返回明确停止响应，不继续环境行动。这是内部协议错误处理，不替 Agent 选择普通工具或强制需求解决次序。上游网络异常目前仍按原调用栈上抛；取消、进程退出与服务级故障不属于补丁事务保证。

## 4. Task 隔离和持久化范围

Runner 按 mode 隔离 app；Session 引用按 `(mode, task_id)` 区分；每题有独立 Session ID 与 `user_{task_id}`，State 键不使用 `app:`、`user:` 或 `temp:` 前缀。创建时深拷贝输入并强制使用请求参数 task_id、空 Requirement State 和空审计，防止外部传入旧题的 Requirement State。更新时再次验证 task_id 和 base_revision。

同一键的初始化、重置和 run_turn 使用同一把异步锁，避免两个 HTTP 请求同时改同一 Session。`reset=False` 复用已有 Session；`reset=True` 创建新 Session，旧 Session 不被删除。不同 Task 不共用 Requirement 容器。

**这里验证的持久化是进程内、跨 ADK 事件与多轮调用的 Session 保存。** 当前项目仍用 InMemoryRunner/InMemorySessionService，进程重启会丢失；没有实现磁盘 Session 恢复，也没有替换为数据库 SessionService。评测结果 JSON 是可持久保存的实验产物，但不会自动恢复成在线 Session。旧 Session/锁的服务生命周期回收本次未实现。

## 5. Bird-coin 与新增推理成本

内部整理直接调用 `model.generate_content_async()`，没有 FunctionTool、DB HTTP 或用户询问；因此不会触发 `TOOL_COSTS`、扣币回调或工具轨迹。环境工具费用和免费最终提交规则沿用原实现。两模式的原有正常决策轮数限制保留，内部整理不增加 `model_turns`，调用次数、usage 和耗时另记历史。

这不代表免费推理：每个非终止决策前增加一次模型调用，非法更新时可能增加第二次；provider 自身重试仍沿用原 LiteLLM 配置。真实 smoke 中内部整理 6 次，累计 11,661 tokens，耗时约 16.25 秒；这部分不会计入 Bird-coin。usage 是 provider 报告的 token 数，未换算货币费用，也不能与普通决策调用总费用混淆。

结果默认进入 `results/agent-.../simulator-.../requirement_tracking_v1/<run_id>/`，metadata 的 `state_mechanism` 为 `requirement_tracking_v1`。`--output` 仍可显式指定。此前 Prompt Engineering 分支和归档未混入。

## 6. 完整 smoke 示例

用户问题：`Find the top 10 suspicious chains ordered by TCR descending. Return chain_id and TCR.`

离线证据见 [offline.json](requirement_tracking_smoke/offline.json)：真实 ADK Runner、Agent 工具、预算 callbacks、Runtime 和 SessionService；模型响应与 HTTP 是可控 fixture，未运行数据库评分。

| 阶段 | 实际 State 行为 |
| --- | --- |
| 初始化 revision 1 | 数量 10、TCR 降序、输出 chain_id/TCR 已 resolved/0；suspicious 条件、TCR 公式、schema 映射 unresolved/非零；共 6 项 |
| get_schema → revision 2 | `chains(chain_id,total,capacity)` 映射 resolved |
| get_knowledge_definition → revision 3 | 通用 TCR 定义为 `total/capacity`，适用性未确认，保持 candidate |
| 第一次 ask_user → revision 4 | 回答只有“TCR 高于阈值”，尚无阈值数字；suspicious 保持 candidate |
| 第二次 ask_user → revision 5 | 明确阈值 0.8、确认公式并排除零容量；相应需求 resolved/0 |
| submit_sql 与后续 run_turn | 正常请求已包含 revision 5；从新取出的 Session 与下一轮决策均读到相同 State，明确数量/排序/输出约束未丢失 |

离线 SQL 为 `SELECT chain_id, total/NULLIF(capacity,0) AS tcr FROM chains WHERE total/NULLIF(capacity,0)>0.8 ORDER BY tcr DESC LIMIT 10`。工具费用为 schema 1 + KB 0.5 + 两次询问 4 + submit 3 = 8.5，初始 12，剩余 3.5。所有内部更新均未出现在工具轨迹。

真实模型证据见 [live.json](requirement_tracking_smoke/live.json)。使用当前配置的 `deepseek/deepseek-flash`，没有替换模型输出；HTTP 仍是合成 fixture，提交成功标记也由 fixture 给出，**不代表 SQL 在真实 PostgreSQL 中被评测正确**。

真实模型首次记录 8 项需求，明确数量/排序/输出已解决，未知公式和映射仍待确认。其实际工具路径为 `get_schema → get_all_external_knowledge_names → get_knowledge_definition → ask_user → ask_user → execute_sql → submit_sql`。KB 公式及部分用户回答保持 candidate；完整回答后 revision 5，9 项需求全 resolved，并新增 `Exclude chains with zero capacity`。环境扣费 10，初始 16，剩余 6。真实模型确实使用了候选定义与两轮用户回答；固定模型测试另外验证了下一轮正常模型请求实际包含 State。

## 7. 已验证与尚未验证

离线覆盖：初始化完整明确/未知约束；新增 Requirement；Category 更新；候选、冲突、resolved 后重开与再次解决；优先级恢复；补丁原子性；非法字段、类型、枚举、过期 revision、重复条目拒绝；一次纠正与两次失败停止；跨事件保存；跨轮读取；Task/mode 隔离；reset；同 Session 并发请求串行化；c-interact 提交后停止/新轮重置；混合提交批次不执行工具；Bird-coin 不受内部更新影响。

真实模型 smoke 已验证：模型自行生成合法 JSON、首次覆盖明确约束与未知需求、Knowledge 候选状态、部分回答不误解决、二次澄清后更新及新增规则、完成提交链路。该 smoke 未覆盖真实模型的冲突判定；冲突重开由离线受控补丁验证。

尚未验证：真实 DB/用户模拟器服务的端到端评测、72 题效果、真实任务的全部需求召回率、复杂业务冲突的语义判定质量、改写重复项的完全消除、真实 follow-up 数据集上的约束继承、进程重启恢复、数据库 SessionService、多进程并发、其他 ADK/provider 版本。

语义判断由模型负责：JSON 校验保证结构、原子性和字段不变量，不能证明“答案足够可靠”、所有需求完整或冲突判定正确。通过 evidence comparison 指令、必填 reason、不可删除旧条目与审计降低风险，不能把这些工程保证等同于语义正确率。

## 8. ADK/provider 限制与注意事项

- 本机验证版本：google-adk 2.9.2、LiteLLM 1.102.0、Pydantic 2.13.5，使用 conda 环境 `bird-interact`。系统 `python3` 没有 google-adk。仓库 requirements 仍为宽范围，未声称兼容所有版本。
- ADK 的 Session State 不会自动进入模型上下文，必须显式注入；`get_session()` 返回副本，直接赋值不构成可靠持久化。官方说明见 [ADK State](https://github.com/google/adk-docs/blob/main/docs/sessions/state.md) 与 [Callback 类型](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)，实现同时以本机源码和 Runner smoke 验证。
- 直接调用内部模型不会触发另一层 ADK 工具循环或自动生成内部模型事件；因此必须手动校验并单独记录 usage/耗时。正常决策的 ADK 事件仍由 Runner 保存。
- 没有强制使用 provider 原生 response_schema，也没有要求同一回复同时产生 JSON 文本和工具调用；使用无工具内部 JSON pass，再本地严格验证，避免不同 provider 的结构化输出/工具并用差异。回复不合协议可被拒绝。
- 每次整理会发送可见历史与 State，token 随上下文增长；长初始化或大量更新可能超过原模型 max_tokens=4096，随后有限纠正仍失败会停止。未加入压缩、检索或需求裁剪。
- submit 与其他工具并发会导致证据时序不清，因此当前明确停止这种批次；没有实现自动重新规划或自动重试该批次。
- 真实 smoke 进程退出时 LiteLLM/aiohttp 打印了 `Event loop is closed` 清理告警，测试断言和结果保存均成功；未修改共享 provider 的连接生命周期。
- 首次联网尝试被沙箱阻止；获准联网后初轮链路完成，但测试对 Knowledge 工具的假设过窄，且 fixture 缺少其他工具响应。完善 fixture、允许两种正常 Knowledge 查询入口后，真实模型 smoke 通过。未将第一次失败算作通过。

## 9. 复现

```bash
# 默认离线检查，live 测试被跳过；可重复生成完整 offline 证据。
REQUIREMENT_SMOKE_ARTIFACT=/tmp/requirement_tracking_smoke.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -v

# 使用 .env 配置的真实模型，有 token 费用；环境 HTTP 仍使用合成 fixture。
REQUIREMENT_LIVE_SMOKE=1 REQUIREMENT_LIVE_ARTIFACT=/tmp/requirement_tracking_live.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -p '*live.py' -v
```

最终测试数量、通过结果和证据哈希见 [validation.json](requirement_tracking_smoke/validation.json)。
