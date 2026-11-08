# Requirement State Tracking：恢复原生 ADK 工具协议

当前直接修改 `state/requirement-tracking`。原生工具接入已提交为 `db4875e`；此后的修改包括移除模型提供的 `base_revision`，以及让缺失/非法 State 不再阻挡正常行动，不新开分支、不自动提交。`main@8138403`、`state/requirement-tracking-2calls@92a299c` 与此前 Prompt 实验分支未修改。

当前机制是：**正常模型回复的文本包含 State 更新，同时保留模型原生 FunctionCall；after_model_callback 校验更新，合法时保存、缺失或非法时记录错误并保留旧 State，两种情况都返回 None，原样交还 ADK 执行。** 没有额外的需求整理 LLM 调用，也没有 JSON 行动适配器。

本轮版本管理调整：模型只输出 `state_update.upserts`；Runtime 内部维护 `revision`，只有需求数据实际变化时递增，空补丁或重复值不增加，非法补丁不改变旧 State。当前需求列表注入模型时不包含 task_id/revision 容器字段，模型不需要返回或记忆版本号。原有原生调用、参数、ID、历史和预算路径未改变。

当前验证：15 项离线测试通过，真实模型测试默认跳过。新增测试验证：缺失/非法 State 后工具仍执行、按原规则扣费、正常进入下一次决策且可恢复合法更新；初始 State 缺失时，a/c 两模式的 submit_sql 也不受阻挡；原始响应、调用 ID 和参数不变。此前移除版本字段时，还将 8 题运行中 `alien_M_5` 的失败响应仅去掉 `base_revision` 后离线回放：补丁被接受，Runtime revision 从 5 自动递增到 6，原生响应未改写。没有执行该 SQL，也没有重跑这 8 题。本轮还新增外层文本恢复及严格拒绝用例，并通过真实 ADK Runner + 受控模型/HTTP 验证：缺失结束标记且带 DSML 尾部的完整 JSON 可保存，get_schema 正常执行并扣 1 coin，下一次模型调用读取更新后的 State。未重跑真实模型或 8 题评测。下文已有真实 smoke 记录均为 `db4875e` 的历史证据，使用的是旧的阻断策略，尚未用当前策略重跑，不改写其原始 JSON 或哈希。

## 相比 05ae014 已撤掉的改动

| 项目 | 当前处理 |
| --- | --- |
| 清空原生 tools，工具说明复制到 Prompt | 撤掉，使用 main 的原生工具注册和声明 |
| 整份 JSON 的 tool_calls/response 行动协议 | 撤掉，模型原生选择和生成工具调用 |
| 从 JSON 重建 FunctionCall、生成调用 ID | 撤掉，保留模型返回的原生 ID、参数和调用 |
| FunctionCall 历史恢复成 JSON、工具结果变为 evidence 文本 | 撤掉，不读写 llm_request.contents |
| 强制 JSON Output Mode、response_schema | 撤掉，不修改这些请求配置 |
| 额外 JSON Schema 业务参数验证 | 撤掉，沿用 ADK FunctionTool 原来的参数处理 |
| 每批最多 9 个工具、submit 必须独立、工具/文本互斥 | 撤掉，不在 State 回调施加这些行动限制 |
| 为此增加的 jsonschema 直接依赖 | 撤掉，requirements.txt 与 main 完全一致 |
| Runtime 的新增同 Session 锁、摘要日志 append_event 改动 | 撤掉，恢复 main 的原调用流程，仅加入 State 容器初始化 |
| 修改默认结果目录，包括 oracle 目录 | 撤掉，恢复 main；只保留一个 State 实验 metadata 字段 |

旧的 `docs/requirement_tracking_1call_smoke/` 是 **05ae014 的历史证据**，未删除或改写，不代表当前代码。当前验证证据在 `docs/requirement_tracking_native_smoke/`。旧方案及其文档亦可通过 `git show 05ae014:...` 查看。

## 实际保留的最小接入点

对比 main，原有框架文件只保留以下变化（另有两个 State 模块、测试和文档）：

| 文件 | 当前职责 |
| --- | --- |
| `system_agent/agent.py` | 两种模式都在原 before-model 回调外包一层 State 注入，并注册 after-model State 回调；原 prompt、tools、工具前后回调和生成配置保留 |
| `system_agent/adk_runtime.py` | 创建 Session 时写入对应 task_id、空 State、空审计与错误；其余 Runtime 流程恢复 main |
| `orchestrator/ainteract.py`、`cinteract.py` | 各增加三个结果字段：State、审计历史、错误 |
| `orchestrator/runner.py` | 仅增加 `state_mechanism=requirement_tracking_native_v1` metadata |
| `system_agent/requirement_state.py` | 五字段与 ID、枚举/优先级/原子补丁校验；Runtime 自动维护 revision，模型补丁只含 upserts |
| `system_agent/requirement_tracking.py` | 仅 State 指令注入、文本更新解析、State 校验保存及审计；不调用模型、不定义工具、不改写行动或历史 |

`system_agent/tools.py`、两套 `callbacks*.py`、`shared/llm.py`、`requirements.txt` 与 main 完全一致。当前原生工具仍为 a-interact 的九个、c-interact 的两个。没有新增 State Tool。

## 一次正常模型回复的结构

ADK 的同一份 Content 可以包含文本 Part 和 FunctionCall Part。模型响应示意：

```text
Content(role="model", parts=[
  Part(text='<requirement_state_update>{"state_update":{
    "upserts":[{
      "id":"r4", "requirement":"TCR formula", "category":"knowledge",
      "status":"candidate", "value":"total/capacity; generic (source: KB)",
      "priority":3
    }]
  }}</requirement_state_update>'),
  Part(function_call=FunctionCall(
    id="供应商原生ID", name="ask_user",
    args={"question":"Please confirm the exact TCR formula and threshold."}
  ))
])
```

这不是把调用放在 JSON 文本里。JSON 中只有 `state_update`，工具仍由原生 Function Calling 提供。纯文本 JSON `{"state_update": ...}` 也可接受。外层标记仅为输出约定，解析不依赖其完整性：缺失/错误标记、代码围栏、前后说明与 DSML 尾部均可忽略，直接扫描完整的外层 JSON 对象。字符串中的括号和转义引号不会截断对象。必须恰好找到一个 State 更新；多个更新、嵌套在其他 JSON 容器内的更新会拒绝。不会修复缺失括号、跳过损坏的 State 对象后选择另一个，或从损坏父对象中抢救子对象。JSON 语法、重复 key、非法数值及五字段规则仍严格校验。

模型最终只返回文本时也应带 State 更新，可以在标记外给正常回答。成功回调保留完整原始响应，因此 State 文本自然保留在 assistant 历史中；没有剥离、恢复或转换整段历史，也没有最终展示过滤器。正常的工具调用 ID、工具参数和工具结果不由 State 代码修改。

## State 与完整流程

Runtime 保存的 State 仍为 `{"task_id": ..., "revision": ..., "requirements": [...]}`，模型只看到 `{"requirements": [...]}`。版本号仅供 Runtime 保存与审计，不属于 LLM 更新协议。Requirement 正文仅含 `id` 与五字段 `requirement/category/status/value/priority`。category 四种、status 四种、resolved 必须 priority 0，其他状态 1–3；来源放 Value，候选用 `&`，冲突用 `|`。可选 reason 仅进入审计，不是新的研究字段。

1. 初始化 Session，创建任务专属 revision 0 空容器；识别需求发生在第一次正常模型响应中，而非空容器创建时。
2. 原 before-model 检查先运行，保留预算、轮数、task_done、c-interact 提交后停止行为。
3. 若原规则允许调用模型，只向 system_instruction 追加 State 指令和当前 requirements 列表；不注入容器版本号，原生工具、选择配置、历史、输出格式均不变。
4. 正常模型调用一次，在同一次响应中识别/更新需求，并选择原生行动。
5. after-model 只解析文本中的更新：拒绝非法 JSON、重复 key、非法字段/类型/状态/priority、重复 ID/规范化重名等。不再要求或检查模型提供的版本号；完整补丁通过前不改变 Requirement State。
6. 成功后通过 callback_context.state 顶层赋值，ADK 将变化记录为本次模型事件的 state_delta。失败则只记录错误和审计，保留旧 State。两种情况均返回 None，原始 FunctionCall 等内容不替换。
7. ADK 保存事件，再进入原 before-tool 扣费、FunctionTool 执行、after-tool 轨迹记录。离线测试在工具 HTTP 开始时读取 Session，确认 State 已保存。
8. 下一轮模型使用原生 FunctionCall/FunctionResponse 历史读取新证据和最新 State。新增需求、category/status/value/priority 动态更新，原条目不被空补丁删除。
9. SQL 提交仍由原 submit_sql 执行，State 指令要求提交前检查所有需求；没有自动 SQL 对应关系，也不强制按 priority 或全部 resolved 后才能尽力提交。

**State 更新与正常行动解耦。** 缺失或非法时，只拒绝该 State 补丁：保留旧 State，保存错误和拒绝审计，原始文本、原生调用、ID 和参数全部放行。工具是否执行、如何扣币、何时停止仍由原 ADK/预算/阶段规则决定；State 回调不额外扣币、不额外请求模型纠错，也不因为 State 失败停止本轮。即使首次初始化没有成功，也允许该轮正常行动继续，下一次决策仍提供此前保存的需求列表（可能为空）。

`requirement_state_history` 保存接受/拒绝、revision、变化前后、错误、原始模型 Content（含原生调用）和 usage。拒绝表示补丁未应用，不表示工具调用被拒绝。`requirement_state_error` 只表示最近一次更新错误；随后更新有效时它会清空，但历史中的错误保留，判断全程有无 State 错误应检查 history 的 accepted/error。历史不用于重建模型上下文，也不是独立检索/规划机制。partial 或上游错误响应交回 ADK 原处理路径，不在此提交 State。

## Task 隔离与保存范围

复用 main 的 `(mode, task_id)` Session 引用、mode 对应 app、每题独立 Session ID；State 使用普通 Session 键，不使用 app/user/temp 共享前缀。初始化强制写入本题 task_id 和新的 State/审计，reset=False 复用，reset=True 新建。Runtime 检查 State 的 task_id 归属；不依赖模型提交版本。内部 revision 是变更审计计数，不是并发锁；本轮未新增同 Session 并发保护。

持久化验证使用重新取得的 `session_service.get_session()`，不是只看 callback 局部变量。当前仍为进程内 InMemorySessionService，服务重启恢复不支持。main 原有 `state["adk_events"]` 摘要日志的跨轮保存问题本次不顺带修复；这不等于真实 ADK Session Events 或回调 state_delta 未保存。未新增同 Session 并发锁，同一 Session 同时运行多个请求的行为沿用 main，未声明支持。

## 历史 smoke 结果（db4875e，移除 base_revision 之前）

### 离线：真实 ADK，受控模型和 HTTP

完整证据：[offline.json](requirement_tracking_native_smoke/offline.json)。

示例：top 10 suspicious chains，按 TCR 降序，输出 chain_id/TCR。

| 同次模型响应 | State 更新 | 原生行动 |
| --- | --- | --- |
| 第一次 | 六个独立需求初始化，明确数量/排序/输出已解决，公式/筛选/schema 待确认；revision 1 | get_schema |
| 第二次 | schema 映射 resolved；revision 2 | get_knowledge_definition |
| 第三次 | 通用 KB 公式 candidate；revision 3 | ask_user |
| 第四次 | 部分用户回答缺少数值，保持 candidate；revision 4 | ask_user |
| 第五次 | 完整回答解决公式与阈值、新增零容量规则；revision 5 | submit_sql |
| 第六次及新一轮 | 空补丁保留 State，下一轮实际读到 revision 5 | 正常文本 |

前六次决策恰好六次模型调用，没有额外整理请求。工具执行前观察到已保存 revision 1/2/3/4/5。初始 12 coins，工具费用 8.5，剩余 3.5。新一轮请求仍含原生 FunctionCall/FunctionResponse、原生调用 ID 以及 State 文本，没有 evidence 转换。

历史测试另外覆盖：before-model 除 system_instruction 外不改请求；after-model 成功返回 None 且不改响应；原生参数保留并由 FunctionTool 过滤额外参数；原有提交批次行为不被 State 回调拦截；非法 State 无额外调用且保留旧值；Task/mode 隔离、reset、c-interact 提交后停止/下一轮复用；候选、冲突、解决后重开、可选审计字段与严格枚举/priority 校验。本轮增加了不依赖模型版本号的 Runtime revision 递增、空/重复更新不递增、版本不进入模型上下文的测试。

### 真实 DeepSeek：原生协议完整流程通过

完整证据：[live.json](requirement_tracking_native_smoke/live.json)。使用配置的 `deepseek/deepseek-flash`，不替换模型输出；环境 HTTP 是合成 fixture，SQL 提交成功标记不代表真实 PostgreSQL 评分正确。

为了明确要求测试用户澄清，真实 smoke 的问题在基本示例后显式说明：suspicious 使用用户尚未给出的个人阈值，TCR 是其自定义指标，需要向其确认。这是合成测试输入，不是生产 prompt 增加该任务的答案；不能将它与旧 smoke 的不同输入直接作性能比较。

实际通过的运行：

- 6 次正常模型调用，6 份接受的 State 响应，额外 State 模型调用 0。
- 原生工具序列：get_schema + get_all_external_knowledge_names（首批）→ get_knowledge_definition → ask_user → ask_user → execute_sql → submit_sql。
- 六次传给 LiteLLMClient 的请求均有原生 tools，response_format/tool_choice 均未强制设置；后续有原生 assistant.tool_calls 和 role=tool 消息。
- 每次带原生工具的模型响应也有 State 文本和供应商 ID。模型原生调用不被回调重建。
- 初始明确数量/输出/排序 resolved；KB 通用公式先 candidate。用户第一次只说“高于阈值”时数值仍未解决，公式仍 candidate；第二次确认公式和 0.8 后才解决，另新增排除零容量。
- 最终 8 项需求，revision 5。初始 16 coins，按原工具规则扣除 10，剩余 6。整次正常决策 usage 为 21,198 tokens，测试约 11.58 秒；不是独立 State 成本，未证明性能优于旧方案。

初始真实响应没有提前记录 schema 映射，而是在 get_schema 后新增；这说明“初始化尽可能完整”仍依赖模型，不能由类型校验保证所有需求召回。suspicious 的条件和阈值也可能存在粒度重叠。不会把单次 smoke 的通过等同于语义完整或稳定可靠。

最初两次真实尝试分别暴露：省略 State；跨轮混合输出成功后标记写成 `<requirement_state_update" >`，随后被拒绝。原始失败见 [attempt_1.json](requirement_tracking_native_smoke/diagnostics/attempt_1.json)、[attempt_2.json](requirement_tracking_native_smoke/diagnostics/attempt_2.json)。第一次工具未执行，第二次最后拟提交未执行。失败没有被计为通过，也没有在同一运行里偷偷请求模型修复。

随后仅调整 State 指令、示例和文本标记容错；没有禁用原生工具、改变历史或启用 JSON Mode。退出时原 LiteLLM/aiohttp 的 Event loop is closed 清理告警仍存在，断言和结果保存成功；共享传输生命周期未修改。

## 验证与未覆盖范围

版本核对为本机 google-adk 2.9.2、LiteLLM 1.102.0、google-genai 2.24.0、Pydantic 2.13.5；系统 python3 未安装 ADK，使用 conda 环境 bird-interact。没有修改安装包或共享模型适配器。

本机接口及原始 API 响应允许同时携带 content 和 tool_calls；本次真实运行也观察到共存。字段结构参见 [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。本次不依赖 provider 特定的 json_object 配置，但其他模型能否稳定输出 State 文本仍需实测，不能从 ADK 支持混合类型推导出所有 backbone 都遵循指令。

测试计数、源码/证据哈希、main 等价文件列表见 [validation.json](requirement_tracking_native_smoke/validation.json)。未测试真实 DB/用户模拟器端到端评测、72 题效果、进程重启恢复、同 Session 并发、SSE/Realtime 或其他 backbone。需求召回、语义去重、知识适用性、复杂冲突判断仍由模型负责，没有新增语义裁判或 Controller。

```bash
# 默认离线检查，真实模型测试跳过。
LITELLM_LOCAL_MODEL_COST_MAP=True REQUIREMENT_SMOKE_ARTIFACT=/tmp/requirement_native_offline.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -v

# 真实模型有正常 token 费用；环境 HTTP 仍使用 fixture。
LITELLM_LOCAL_MODEL_COST_MAP=True REQUIREMENT_LIVE_SMOKE=1 REQUIREMENT_LIVE_ARTIFACT=/tmp/requirement_native_live.json \
  /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -p '*live.py' -v
```
