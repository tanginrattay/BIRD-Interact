# Simulator 网页手工对照包

目的：在不重跑完整 benchmark 的情况下，诊断模型是否理解隐藏意图、纠正错误前提、保持条件完整并遵守泄漏边界。仅限研究者/simulator 使用；包含 benchmark 隐藏真值，不要交给 system agent，也不要直接公开上传结果仓库。

## 使用步骤

1. 打开 [固定输入](01_COPYABLE_CASES.md)。每题只复制一个完整 text 块。每题每模型开新会话，关闭联网/搜索、记忆和自定义指令（如产品允许），不要先告诉它正确答案。
2. 用界面实际显示的模式分别测试。候选来自你的界面描述：Kimi 3、Kimi 2.8、Kimi 快速（后端未知）、DeepSeek 网页（后端未知）、AI Studio 手动选择的具体型号、GPT 页面显示的 5.5/5.6sol。这里只记录标签，不验证或推断这些产品标签对应的 API 型号。未知后端也能比较产品行为，但不能声称是某个基础模型的结果。
3. 复制 [结果模板](04_RESULT_TEMPLATE.md)，每种模式保存一个 MD，完整贴原始回复。现在模板中没有任何伪造/待测模型的结果。先保存，再用 [人工核查](03_REVIEW_GUIDE.md) 评价。
4. 用 [K2.6历史结果](02_KIMI26_HISTORICAL_RESULTS.md) 参考；不是严格同请求重新测量。先测10题，选有分歧的题重复，不必立即全模型重复整个 benchmark。

网页输入将 API system instruction 和 user context 合并。即便文本相同，角色优先级与隐藏产品提示仍不同。若产品有专用 system instruction 框，可将块中第一段放该框，Task ID起的部分放 user；但需把此方式记录成另一测试条件，不能与单消息方式混算。不要把整个本目录一次喂给模型。

## 测试集来源与复现边界

C01–C08：已有真实 HTTP calibration，3个Lite任务；C09–C10：pilot自然交互，2个额外Lite任务。共10问、5任务，全部 Phase 1。完整保留 simulator 所用 clear query、ambiguous query、两类歧义、参考 SQL、历史与当前问题；没有新增参考答案到输入中。当前 Kimi 直接路径不传 db_schema，本包也不另加。

C01–C08 使用校准 JSON 的 hidden_context/request 重建；C09–C10 使用 pilot tasks.jsonl 和对话重建。固定角色说明逐字抽取本次工作树 `_ask_kimi` 的 instructions。历史运行未保存完整 system message，因此不保证历史请求与本包逐字节一致。v2/v3文件名是本地校准迭代名，不是模型版本。

## 本次 K3 API 配置改动

`shared/llm.py` 中 `build_adk_model` 对最终模型名恰为 `kimi-k3` 的模型传入顶层 `reasoning_effort="low"`；直接 `call_llm` 对该模型未显式指定时也默认 low，有显式参数则保留。其他模型默认行为不变。K2.6 simulator 仍显式 none，max_tokens=1024；system agent max_tokens=4096和coin budget未改。

依据：[Kimi官方推理强度文档](https://platform.kimi.com/docs/guide/use-reasoning-effort)，查询日期2026-10-04：K3支持low/high/max，默认max。low预期减少思考消耗/延迟，但本次未执行付费调用，没有测得节省比例或效果变化。95元K3、13元K2.6合计108元；与口述总109元的1元差异未核销（可能为舍入或其他消费，不能确定）。消费分布支持优先优化K3，但不是费用全部由推理模式造成的证据。

修改只影响新创建的模型实例。已有服务需要在安全停止当前实验后重启才能生效。本次没有重启服务、停止任务或启动新benchmark，避免影响主线程实验。仓库 start_services.sh 含广泛 pkill uvicorn，不应在其他任务运行时盲目执行。新增 shared/test_llm.py 可离线测试参数传递，无付费调用。

低推理强度是新的实验条件，后续结果请命名/标注 kimi3-low，不与旧默认配置当作完全相同baseline。未来方法对照双方都用low，或单列推理强度消融。

## 来源指纹

SHA256用于核查本包创建时来源；原文件之后可能变化，固定输入以本包为准。

- `results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v3.json`：`122062593e03a0c3ea18e539979ba686a12680c4720c62fd670ae398e6c4522d`
- `results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v2.json`：`2a3caff5e7e5b9cefc1cc9ba0e02578f848ae09da263ae76156cc0968af05dc5`
- `results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume1.json`：`7683d833f6bcc2d878d0e0bdcbc454253617ac46c9d5768f2f226e7c244e1e3e`
- `results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/tasks.jsonl`：`aeb851d78736e4b1794f1c83080b2bf99425b0d0dcfe23f4e1728638d61c6b52`
- `user_simulator/server.py`：`05315e5cca761b650dee2d2402fd8d8f1b679a4886a6365a76c76dbc945a32f8`
