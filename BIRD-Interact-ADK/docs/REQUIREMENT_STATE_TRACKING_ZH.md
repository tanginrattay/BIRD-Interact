# Requirement State Tracking：同一次回复更新 State

本次版本对应用户指定的机制：Agent 在一次正常模型回复中给出 `state_update` 和本轮行动，注册的 **`after_model_callback` 解析、校验并保存 State**。没有独立需求整理请求，没有隐藏的模型纠错调用。

## Git 与实验隔离

| 分支 | 状态与含义 |
| --- | --- |
| `state/requirement-tracking-2calls` | 已提交 `92a299c`，完整保留之前每步额外调用模型整理 State 的实现、文档和测试证据 |
| `state/requirement-tracking` | 从 `main@8138403` 重新创建，本文件所述单次回复版本；新实现未自动创建 commit |
| `main` | 保持 `8138403` |
| `prompt/exploration-policy` | 保持原有分支，未合并或修改 |

新分支只复用通用 Requirement 校验与 Session 保存代码，不包含两次调用的整理逻辑。默认新结果目录带 `requirement_tracking_1call_v1/`，metadata 的 `state_mechanism` 同名，以区分此前 State/Prompt 实验。

## 与两次调用版本的区别

```text
两次调用版本：
读取证据 → 模型整理 State → 保存 → 模型决定行动 → 工具执行

本版本：
读取当前 State 和新证据 → 模型同时返回更新与行动
                         ↓
               after_model_callback
             校验整份响应 → 保存 State
                         ↓
                 ADK 执行模型所选工具
```

`before_model_callback` 只注入 State、协议和工具说明并准备请求；不调用模型。`after_model_callback` 只做确定性的解析、校验、赋值和格式转换；不替模型决定行动，也不调用模型。

一次回复包含以下三个固定字段：

```json
{
  "state_update": {
    "base_revision": 2,
    "upserts": [
      {
        "id": "r3",
        "requirement": "Determine TCR formula",
        "category": "knowledge",
        "status": "candidate",
        "value": "TCR = total/capacity; applicability unconfirmed (source: KB)",
        "priority": 3,
        "reason": "The generic KB formula has not been confirmed for this task."
      }
    ]
  },
  "tool_calls": [
    {
      "name": "ask_user",
      "args": {"question": "Does total/capacity define TCR in this task, and what threshold makes a chain suspicious?"}
    }
  ],
  "response": ""
}
```

这是示意更新，假设 revision 2 已存在同 ID、同 requirement 文本的条目。首次必须初始化全部独立约束；后续无变化时 `upserts: []`，但仍必须返回 `state_update`。使用工具时 `response` 为空；结束并返回文本时 `tool_calls: []`，`response` 非空。

这里的自定义字段位于模型返回的 JSON 文本中，不是向 ADK `LlmResponse` 强行添加属性。Callback 读取 `llm_response.content.parts` 的文本进行解析。模型在 `tool_calls` 中自行选择行动，Callback 验证后把它转换为标准 `FunctionCall`。这是格式适配，不是额外 Planner/Controller。

## Requirement 数据结构与规则

Session 中保存：

```json
{
  "task_id": "example",
  "revision": 1,
  "requirements": [
    {
      "id": "r1",
      "requirement": "Return 10 chains",
      "category": "user_semantics",
      "status": "resolved",
      "value": "10 (source: user)",
      "priority": 0
    }
  ]
}
```

以上仅展示一个条目的结构，不代表完整初始化结果。每项保持五个研究字段，仅增加内部 `id`。Category 固定 schema/knowledge/user_semantics/unknown；Status 固定 unresolved/candidate/conflict/resolved。priority 是严格整数，resolved 必须为 0，其他状态必须为 1–3。候选、冲突和已解决状态要求非空 Value；冲突值要求 `|`，多个候选按指令使用 `&`。来源保存在 Value，没有独立 source 字段。

初始化指令要求记录所有影响正确性的独立约束，包括明确的数量、输出列、排序，以及未知公式、筛选、schema 映射、聚合/分组、格式、CREATE VIEW 等特殊操作。公式与 schema 映射分开；不按每个单词拆分。明确需求 resolved/0，未知需求保留非零 priority。

更新只允许 upsert，禁止删除或改名；未出现在补丁中的旧需求保留。同一条目沿用 ID 和 requirement 文本，可修改 category/status/value/priority。新证据要求与旧答案比较，实际矛盾转 conflict 并保留两方；resolved 可重开、恢复非零 priority。通用或名称相似的 KB 定义不能直接确认，部分用户回答不能补造缺失信息。

`reason` 是可选的更新审计解释，不进入 Requirement 正文；缺省为空，不因遗漏这个非研究字段拒绝合法的五字段更新。`requirement_state_history` 保存变化前后、原始完整模型 JSON、接受/拒绝结果、错误及该次正常模型调用的 token usage。`requirement_state_error` 是运行错误。上述运行字段不扩大 Requirement 的研究职责。

## Runtime 完整工作流程

1. `/init_session` 创建本任务 Session，保存 revision 0 的空 State 容器。此时还没有模型回复，不能声称已识别需求。
2. `Runner.run_async()` 组织当前对话与新工具结果。原有预算、任务结束、轮数和 c-interact 提交后停止规则首先执行；若已要求停止，不再发模型请求。
3. `before_model_callback` 注入最新 State、固定响应协议、允许工具的名称/描述/参数。模型请求使用 JSON 输出模式。没有在此处进行需求推理。
4. 正常模型调用一次，返回 `state_update + tool_calls/response`。模型一边读取旧 State 与新证据，一边决定更新和行动；因此同一回复中的行动可以基于新确认的理解，而不必先多调用模型。
5. `after_model_callback` 校验整份 JSON：字段/类型、revision、需求五字段、重复 JSON key、重复 ID/规范化同名需求、未知工具、缺失/非法/多余工具参数。更新和行动任何一方无效，整份响应都不执行。
6. 校验成功后对 `callback_context.state` 做顶层赋值，保存最新 State、审计历史。ADK 将赋值捕获到本次模型事件的 `EventActions.state_delta`。
7. 同一个回调将模型已经选定的 JSON 工具行动转换为标准 FunctionCall，带唯一 `call_req_...` ID，交还 ADK。ADK 保存模型事件后才执行工具。离线测试在 HTTP 工具开始时读取底层 Session，确认本轮 State 已保存。
8. 工具沿用原 FunctionTool 和两套工具 callbacks，正常扣费、记录轨迹和返回证据。下次模型调用读取刚保存的 State 与这些新证据，再在同一次回复更新。
9. 提交 SQL 也必须包含 State 更新字段，可为空补丁。协议要求检查全部需求，但没有自动 SQL 对应验证，也不强制所有项 resolved 后才允许按原预算规则尽力提交。submit 不允许与其他工具出现在同一批次，避免依赖同批尚未返回的证据。
10. Runtime 通过 SessionService 重新读取结果，orchestrator 保存最终 State、历史和错误。`adk_events` 也通过 `append_event` 保存，避免仅修改 Session 副本。

非法响应时保留旧 State、保存拒绝审计，返回明确停止文本，并移除全部拟执行工具。不自动补发模型纠错请求；需要后续显式发起正常交互才能继续。网络错误仍沿用原 Runtime 调用异常路径，不把故障伪装成有效更新。

## Task 隔离和预算

State 使用普通 Session 键，不使用 app/user/temp 共享作用域。Runner 按 mode 分 app，引用按 `(mode, task_id)` 区分，Session ID 独立。初始化深拷贝传入状态，强制覆盖 task_id、Requirement State 与审计，拒绝跨任务补丁。同一键的初始化、reset 和 run_turn 使用同一异步锁；`reset=False` 复用，`reset=True` 新建 Session。

当前仍是 InMemorySessionService：已验证的是进程内跨事件、跨轮保存；服务重启恢复、数据库 Session、多进程协调未实现。评测结果 JSON 可落盘，但不会自动恢复在线 Session。

State 更新未注册为 FunctionTool，没有独立 HTTP，也不进入 `TOOL_COSTS`。原有 a-interact/c-interact 工具、计费回调和免费最终提交逻辑不变。JSON 行动仍交给这些原工具执行。没有新增 State 模型请求；正常请求因多输出 State/协议而增加 token，不能称为零推理成本。历史中 usage 对应整次正常决策，不能将其视为纯 State 开销。

## ADK 与供应商的实际限制

本机验证 google-adk 2.9.2、LiteLLM 1.102.0、Pydantic 2.13.5、jsonschema 4.26.0，使用 conda 环境 `bird-interact`。增加直接依赖 `jsonschema>=4.0.0` 校验模型给出的工具参数。其他版本未验证。

- `after_model_callback` 能替换响应并更新 State，但不会自动为模型创造自定义字段。必须定义 JSON 协议，再解析内容；官方说明见 [ADK callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)。
- 已验证 Callback 的 State delta 在工具执行前保存，下一轮请求读到前一轮保存的 revision。
- ADK 默认的 `adk-...` 内部工具 ID 会在下一轮模型请求中被移除。最初真实 smoke 遇到空/重复 tool_call_id 导致 DeepSeek 400。当前适配器生成自己的唯一 ID，保留标准 ADK 调用/结果关联。
- 仅提示“输出 JSON”，甚至设置 native tool_choice=none，仍观察到 DeepSeek 在后续回复输出 DSML 内部工具标记。仅转换历史为文本也未完全解决，失败时 Runtime 拒绝响应、旧 State 保留。
- 最终模型端采用全文本协议：工具定义作为普通指令，历史中的标准 FunctionCall 只在**请求副本**中通过调用 ID 恢复为模型先前实际返回的完整 JSON；工具结果转为证据文本，缺少旧 JSON 审计的行动才使用执行记录文本；不改变已保存 ADK 事件。保留完整旧 JSON 有助于多轮持续遵守协议，避免历史只呈现工具行动却遗漏 State 更新。请求不携带原生 tools；回调转换后的行动仍在 ADK 内执行。这改变了工具行动的输出编码，是本实验需要说明的工程差异。
- 同时启用 DeepSeek 官方 [JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 的 `response_format={"type":"json_object"}`。本机 ADK LiteLLM 接受 `config.response_schema={"type":"json_object"}` 并原样传递该格式，有专门适配测试；最终真实 smoke 另外记录了实际 provider 请求，确认六次都带该参数。JSON mode 用于约束语法，不保证业务字段或语义；调试中仅加 JSON mode 也没有独自解决历史格式问题，仍必须校验、拒绝坏响应。该配置路径针对本机 LiteLLM，未声称支持所有 ADK backend。
- 本次 Runtime 使用非流式调用。部分 streaming 响应不会提交 State，但未验证完整 SSE/Realtime 生命周期。
- 需求召回、语义重复、公式适用性与冲突识别仍依赖模型。工程校验不能证明语义正确；没有新增语义裁判调用。输出过长、token 截断或不符合协议时停止，未实现压缩或额外重试。

## Smoke 与验证范围

离线完整证据：[offline.json](requirement_tracking_1call_smoke/offline.json)。真实 ADK Runner、SessionService、callbacks 与工具 HTTP 包装均运行；模型输出与 HTTP 返回使用 fixture。

示例问题为：`Find the top 10 suspicious chains ordered by TCR descending. Return chain_id and TCR.`

| 模型回复 | 同次 State 更新 | 同次选择的行动 |
| --- | --- | --- |
| 第一次 | 初始化数量/排序/输出为 resolved，公式/筛选/schema 待确认；revision 1 | get_schema |
| 第二次 | schema 映射已解决；revision 2 | get_knowledge_definition |
| 第三次 | 通用 KB TCR 公式保留 candidate；revision 3 | ask_user |
| 第四次 | 用户仅说“高于阈值”，缺数值，保持 candidate；revision 4 | ask_user |
| 第五次 | 用户给出阈值 0.8、确认公式、要求排除零容量；解决旧需求并新增规则；revision 5 | submit_sql |
| 第六次 | 空补丁保留 State | 结束文本 |
| 下一轮请求 | 实际读取保存的 revision 5，仍无额外整理调用 | 复查文本 |

该受控流程前六次决策恰好调用模型 6 次，没有另加 6 次 State 调用。工具开始前观察到已保存的 revision 序列 1/2/3/4/5。最终 7 项需求；schema 1 + KB 0.5 + 两次询问 4 + submit 3 = 8.5 coins，初始 12，剩余 3.5。fixture 接收 SQL，不执行真实数据库评分。

离线还覆盖：候选/冲突/解决/重开、Category 更新、新增需求；非法字段/状态/priority、过期 revision、重复 ID/JSON key、未知工具/参数、缺失 State、原生调用绕过协议的拒绝；跨轮保存与读取；Task/mode 隔离、reset、同 Session 并发串行；c-interact 提交后停止与新轮复用；多查询批次的唯一 ID/预算；ADK-LiteLLM 的 json_object 参数传递。

真实模型 smoke 使用配置的模型，模型输出不替换，所有环境服务均为合成 fixture。每个请求的当前 State、模型完整 JSON、State 变化、token usage、工具轨迹均保存到 [live.json](requirement_tracking_1call_smoke/live.json)。最终验证结果、实际次数与哈希见 [validation.json](requirement_tracking_1call_smoke/validation.json)。

最终真实 smoke 通过：**6 次正常模型请求、6 份接受的 State 响应、额外 State 模型请求 0**，完成 7 次环境工具调用（首轮含查询批次）；最终 7 项需求、revision 5，初始 16 coins、剩余 6。整段模型请求 usage 共 22,290 tokens，测试耗时约 11.88 秒；这是正常决策总 usage，不是单独 State 成本，也不能直接与两次调用版本的内部整理 token 数比较。

需要保留的语义限制：真实轨迹中 TCR 公式在 KB 后先被记录为 candidate，但随后模型在用户只回答部分筛选语义时，就根据 schema 匹配把公式适用性判为 resolved，早于第二次回答的明确确认。最终答案随后得到确认，数值阈值也始终保留 candidate 到第二次询问；但公式的提前确认仍是实际观察到的风险，未通过额外语义裁判或确定性规则解决。不能把该 smoke 的链路通过说成所有语义状态都完全符合预期。

协议调试失败记录另保存在 `requirement_tracking_1call_smoke/diagnostics/`；此前失败未计为通过。最终一次测试没有隐藏重试，也没有用 fixture 替换模型更新。退出时 LiteLLM/aiohttp 仍有 `Event loop is closed` 连接清理告警，结果已保存且断言通过；共享 provider 生命周期未在本次修改。

未进行真实 PostgreSQL/用户模拟器端到端评测、72 题比较、真实复杂冲突语义验证、进程重启恢复或多 provider 测试。不能由 smoke 推断单次回复比两次调用效果更好。

## 复现

```bash
# 离线测试；live 默认跳过。
REQUIREMENT_SMOKE_ARTIFACT=/tmp/requirement_tracking_1call_offline.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -v

# 真实模型，有正常 token 费用；环境仍使用合成 fixture。
REQUIREMENT_LIVE_SMOKE=1 REQUIREMENT_LIVE_ARTIFACT=/tmp/requirement_tracking_1call_live.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -p '*live.py' -v
```

## 修改文件职责

| 文件 | 职责 |
| --- | --- |
| `system_agent/requirement_state.py` | 五字段、ID、原子补丁与 revision 验证；复用两次调用版本的通用数据层 |
| `system_agent/requirement_tracking.py` | 单次回复 JSON 协议、State 注入、after-model 捕获与保存、工具参数验证、文本历史适配、ADK 行动格式转换 |
| `system_agent/agent.py` | 两种模式注册真正负责 State 的 after_model_callback，并保留原有停止/预算工具回调 |
| `system_agent/adk_runtime.py` | Session 隔离、reset、同 Session 锁及 Event 持久化；复用通用基础 |
| `orchestrator/ainteract.py`、`cinteract.py` | 结果保存 State、审计与错误 |
| `orchestrator/runner.py` | 独立单次回复实验结果目录及 metadata |
| `requirements.txt` | 声明 jsonschema 直接依赖 |
| `tests/test_requirement_tracking.py` | 离线真实 ADK 验证与一决策一调用计数 |
| `tests/test_requirement_tracking_live.py` | 可选真实模型验证，计数每次模型调用并核对下一轮实际读取的 revision |
| 本文、`docs/requirement_tracking_1call_smoke/` | 工作流程说明与完整实验记录 |
