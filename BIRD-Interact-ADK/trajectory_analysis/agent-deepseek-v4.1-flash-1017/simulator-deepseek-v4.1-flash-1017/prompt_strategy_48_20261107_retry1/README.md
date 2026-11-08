# Prompt 策略对照实验

已保存 48/48 次，语义审查 48/48。四任务 × 四条件 × 三重复；诊断运行不计入。所有率以0–1表示。下表为12个run的均值及样本标准差，混合任务异质性另由逐任务表揭示；每任务每条件只有3次，不能声称统计显著性。

## 控制变量与完整 Prompt

deepseek/deepseek-flash（Agent与Simulator一致）、a-interact / Lite / 原版v1两阶段 / 非思考 / patience=3 / temperature=0；Agent max_tokens=4096，Simulator action=200 / response=1024，concurrency=1。继承原代理配置。工具、Callback、预算公式、任务和数据库不变；未配置模型或Simulator随机种子。Baseline常量与HEAD逐字一致。Prompt加载改动已通过原版与修改版同环境配对运行验证；两者均正常，无法追认上次中断的确切根因。

| 条件 | 完整 Prompt | 追加规则 |
| --- | --- | --- |
| baseline | [baseline.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/prompts/baseline.txt) | 无，原文 |
| A | [A.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/prompts/A.txt) | 只考虑工具成本与单项/全量选择 |
| B | [B.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/prompts/B.txt) | 信息需求、已有内容、相关性、解决状态、预算、上下文负担 |
| C | [C.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/prompts/C.txt) | 完整B + 四类不确定性及数据库/知识库/用户来源选择 |

## 知识检索

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Knowledge Tool Calls | 6.750 ± 2.491 | 5.333 ± 2.871 | 5.750 ± 1.815 | 5.667 ± 1.826 |
| Knowledge Tool Cost | 3.625 ± 1.448 | 3.042 ± 1.499 | 3.042 ± 1.076 | 2.917 ± 1.019 |
| Single Knowledge Calls | 6.250 ± 2.137 | 4.583 ± 2.811 | 5.417 ± 1.564 | 5.500 ± 1.679 |
| Get All Knowledge Calls | 0.500 ± 0.522 | 0.750 ± 0.452 | 0.333 ± 0.492 | 0.167 ± 0.389 |
| Name Discovery Calls | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Knowledge Cost incl. Names | 4.125 ± 1.448 | 3.542 ± 1.499 | 3.542 ± 1.076 | 3.417 ± 1.019 |
| Unique Definitions Retrieved | 28.417 ± 24.511 | 39.833 ± 21.502 | 20.667 ± 23.180 | 12.917 ± 18.793 |
| Exact Duplicate Retrievals（调用） | 0.500 ± 0.522 | 0.667 ± 0.651 | 0.333 ± 0.492 | 0.333 ± 0.492 |
| Exact Duplicate Definition Occurrences | 3.667 ± 4.207 | 3.250 ± 3.306 | 2.000 ± 3.275 | 1.250 ± 2.491 |
| Semantic Redundancy（调用并集，含精确重复） | 0.583 ± 0.669 | 0.750 ± 0.754 | 0.333 ± 0.492 | 0.333 ± 0.492 |
| Additional Semantic Redundancy（跨来源/不同ID） | 0.083 ± 0.289 | 0.083 ± 0.289 | 0.083 ± 0.289 | 0.000 ± 0.000 |
| No New Relevant Information Calls | 5.167 ± 2.791 | 3.917 ± 2.429 | 4.167 ± 1.992 | 4.000 ± 2.000 |
| Retrieval Relevance（条目级宏平均） | 0.212 ± 0.222 | 0.113 ± 0.161 | 0.263 ± 0.217 | 0.301 ± 0.222 |
| Query with Relevant Content Rate | 0.320 ± 0.160 | 0.450 ± 0.290 | 0.334 ± 0.148 | 0.333 ± 0.189 |
| P1 Knowledge Coverage：tool-only | 0.417 ± 0.151 | 0.417 ± 0.151 | 0.375 ± 0.190 | 0.333 ± 0.213 |
| P1 Knowledge Coverage：tools+user，最终可靠 | 0.958 ± 0.144 | 0.958 ± 0.144 | 0.958 ± 0.144 | 0.917 ± 0.195 |
| P1 Knowledge Coverage：ever-correct-seen | 0.958 ± 0.144 | 0.958 ± 0.144 | 0.958 ± 0.144 | 0.958 ± 0.144 |
| P1 Knowledge Calls | 6.750 ± 2.491 | 5.333 ± 2.871 | 5.667 ± 1.969 | 5.500 ± 1.977 |
| P1 Knowledge Cost | 3.625 ± 1.448 | 3.042 ± 1.499 | 3.000 ± 1.148 | 2.833 ± 1.094 |
| P2 Knowledge Calls | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.083 ± 0.289 | 0.167 ± 0.389 |
| P2 Knowledge Cost | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.042 ± 0.144 | 0.083 ± 0.195 |

知识定义调用只含单项与全量；名称查询另列并纳入含名称的成本。扣费按实际预算差额核验，不把Callback标价直接求和。全量返回条目按冻结可见KB与原隐藏规则重建，不声称恢复截断日志。相关性依内容支持判定，零返回率为NA，失败查询另列在逐run表。相关内容可以重复，因此同时报告无新增相关信息调用。

## 用户交互

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Ask User Count | 1.917 ± 0.793 | 1.833 ± 0.577 | 1.667 ± 0.651 | 1.750 ± 0.452 |
| Knowledge Calls Before First Ask | 6.167 ± 2.588 | 4.667 ± 2.902 | 5.500 ± 2.195 | 5.333 ± 2.229 |
| Knowledge Cost Before First Ask | 3.250 ± 1.500 | 2.583 ± 1.550 | 2.875 ± 1.281 | 2.750 ± 1.215 |
| First Ask Timing（工具一基序号） | 9.583 ± 2.610 | 8.500 ± 2.541 | 9.000 ± 2.216 | 8.917 ± 1.564 |
| Ambiguity Resolution Rate（固定P1信息需求） | 0.817 ± 0.163 | 0.858 ± 0.182 | 0.783 ± 0.236 | 0.733 ± 0.249 |
| User-Semantic Resolution Rate（子集） | 0.611 ± 0.358 | 0.722 ± 0.328 | 0.597 ± 0.417 | 0.542 ± 0.377 |
| Unnecessary Ask Rate（run宏平均） | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Fully Unnecessary Ask Count | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Partially Unnecessary Ask Count | 0.333 ± 0.492 | 0.167 ± 0.389 | 0.167 ± 0.389 | 0.083 ± 0.289 |

| 组 | 总ask | 完全不必要/总ask | 含部分不必要的上界 | 未询问run |
| --- | ---: | ---: | ---: | ---: |
| baseline | 23 | 0/23 | 4/23 | 0 |
| A | 22 | 0/22 | 2/22 | 0 |
| B | 20 | 0/20 | 2/20 | 0 |
| C | 21 | 0/21 | 1/21 | 0 |

首次询问时机没有可靠秒级时间戳，使用实际工具序号；没有ask的run记NA。语义标签由单一离线审查者按benchmark/KB与实际问答证据判定，未盲审、未独立双审；它们是可复核标注，不是Agent自评或无误客观真值。

## 整体任务

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Priority Success | 0.333 ± 0.492 | 0.333 ± 0.492 | 0.250 ± 0.452 | 0.417 ± 0.515 |
| Follow-up Success | 0.333 ± 0.492 | 0.250 ± 0.452 | 0.250 ± 0.452 | 0.333 ± 0.492 |
| Total Reward / run | 0.333 ± 0.492 | 0.308 ± 0.462 | 0.250 ± 0.452 | 0.392 ± 0.491 |
| Remaining Budget | 0.625 ± 1.003 | 0.125 ± 0.226 | 1.167 ± 1.969 | 0.958 ± 1.529 |
| Total Tool Calls（实际执行） | 17.917 ± 2.314 | 17.500 ± 2.067 | 17.083 ± 3.088 | 17.333 ± 2.188 |
| Attempted Tool Calls | 17.917 ± 2.314 | 17.500 ± 2.067 | 17.083 ± 3.088 | 17.333 ± 2.188 |
| Budget-Rejected Calls | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Context Tokens | NA | NA | NA | NA |
| Elapsed Seconds | 36.419 ± 11.338 | 38.099 ± 10.392 | 34.044 ± 11.017 | 34.990 ± 10.866 |
| Simulator Incorrect Answer Count | 0.083 ± 0.289 | 0.083 ± 0.289 | 0.000 ± 0.000 | 0.083 ± 0.289 |
| Simulator Incomplete Answer Count | 0.167 ± 0.577 | 0.083 ± 0.289 | 0.083 ± 0.289 | 0.000 ± 0.000 |

P1/P2主成功率均以全部run为分母，Total Reward表为每run奖励；Context Tokens因原ADK事件未存usage而NA，不能用字符数替代。

| 组 | P1成功 | P2成功 | P2/P1条件成功率 | Reward合计 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 4/12 | 4/12 | 1.000 | 4.000 |
| A | 4/12 | 3/12 | 0.750 | 3.700 |
| B | 3/12 | 3/12 | 1.000 | 3.000 |
| C | 5/12 | 4/12 | 0.800 | 4.700 |

## 每任务三次重复

### credit_11

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Knowledge Tool Cost | 2.333 ± 0.289 | 1.500 ± 0.866 | 2.500 ± 0.000 | 2.333 ± 0.764 |
| Knowledge Tool Calls | 4.667 ± 0.577 | 2.333 ± 2.309 | 5.000 ± 0.000 | 4.667 ± 1.528 |
| Exact Duplicate Retrievals（调用） | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.333 ± 0.577 |
| No New Relevant Information Calls | 2.667 ± 0.577 | 1.000 ± 1.732 | 3.000 ± 0.000 | 2.667 ± 1.528 |
| Retrieval Relevance（条目级宏平均） | 0.433 ± 0.058 | 0.160 ± 0.208 | 0.400 ± 0.000 | 0.467 ± 0.176 |
| P1 Knowledge Coverage：tools+user，最终可靠 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Ask User Count | 2.000 ± 1.000 | 2.333 ± 0.577 | 2.333 ± 0.577 | 2.000 ± 0.000 |
| Knowledge Calls Before First Ask | 4.667 ± 0.577 | 2.333 ± 2.309 | 5.000 ± 0.000 | 4.667 ± 1.528 |
| Ambiguity Resolution Rate（固定P1信息需求） | 0.867 ± 0.115 | 0.933 ± 0.115 | 0.933 ± 0.115 | 0.800 ± 0.000 |
| Priority Success | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Follow-up Success | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Total Reward / run | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |

### virtual_1

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Knowledge Tool Cost | 3.833 ± 1.443 | 4.333 ± 1.155 | 3.000 ± 0.000 | 3.000 ± 0.000 |
| Knowledge Tool Calls | 7.333 ± 2.309 | 8.000 ± 1.732 | 6.000 ± 0.000 | 6.000 ± 0.000 |
| Exact Duplicate Retrievals（调用） | 0.333 ± 0.577 | 0.667 ± 0.577 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| No New Relevant Information Calls | 4.333 ± 2.309 | 5.000 ± 1.732 | 3.000 ± 0.000 | 3.000 ± 0.000 |
| Retrieval Relevance（条目级宏平均） | 0.365 ± 0.234 | 0.232 ± 0.232 | 0.500 ± 0.000 | 0.500 ± 0.000 |
| P1 Knowledge Coverage：tools+user，最终可靠 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Ask User Count | 1.667 ± 1.155 | 1.333 ± 0.577 | 1.333 ± 0.577 | 1.667 ± 0.577 |
| Knowledge Calls Before First Ask | 7.333 ± 2.309 | 7.000 ± 1.732 | 6.000 ± 0.000 | 6.000 ± 0.000 |
| Ambiguity Resolution Rate（固定P1信息需求） | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Priority Success | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.333 ± 0.577 | 1.000 ± 0.000 |
| Follow-up Success | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.333 ± 0.577 | 0.667 ± 0.577 |
| Total Reward / run | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.333 ± 0.577 | 0.900 ± 0.173 |

### polar_M_4

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Knowledge Tool Cost | 4.833 ± 1.528 | 4.167 ± 0.289 | 4.667 ± 0.289 | 4.333 ± 0.289 |
| Knowledge Tool Calls | 8.667 ± 3.055 | 7.333 ± 0.577 | 8.333 ± 0.577 | 8.000 ± 1.000 |
| Exact Duplicate Retrievals（调用） | 1.000 ± 0.000 | 1.333 ± 0.577 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| No New Relevant Information Calls | 7.667 ± 3.055 | 6.333 ± 0.577 | 7.333 ± 0.577 | 7.000 ± 1.000 |
| Retrieval Relevance（条目级宏平均） | 0.033 ± 0.002 | 0.039 ± 0.010 | 0.033 ± 0.000 | 0.059 ± 0.045 |
| P1 Knowledge Coverage：tools+user，最终可靠 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.833 ± 0.289 |
| Ask User Count | 2.333 ± 0.577 | 1.667 ± 0.577 | 1.667 ± 0.577 | 1.667 ± 0.577 |
| Knowledge Calls Before First Ask | 8.667 ± 3.055 | 7.333 ± 0.577 | 8.333 ± 0.577 | 8.000 ± 1.000 |
| Ambiguity Resolution Rate（固定P1信息需求） | 0.733 ± 0.115 | 0.667 ± 0.231 | 0.533 ± 0.231 | 0.467 ± 0.306 |
| Priority Success | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Follow-up Success | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Total Reward / run | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |

### cybermarket_1

| 指标（mean ± sample SD） | Baseline | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Knowledge Tool Cost | 3.500 ± 1.500 | 2.167 ± 1.041 | 2.000 ± 0.500 | 2.000 ± 0.500 |
| Knowledge Tool Calls | 6.333 ± 2.517 | 3.667 ± 1.528 | 3.667 ± 0.577 | 4.000 ± 1.000 |
| Exact Duplicate Retrievals（调用） | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.333 ± 0.577 | 0.000 ± 0.000 |
| No New Relevant Information Calls | 6.000 ± 2.646 | 3.333 ± 1.528 | 3.333 ± 1.155 | 3.333 ± 0.577 |
| Retrieval Relevance（条目级宏平均） | 0.018 ± 0.018 | 0.019 ± 0.019 | 0.118 ± 0.187 | 0.178 ± 0.168 |
| P1 Knowledge Coverage：tools+user，最终可靠 | 0.833 ± 0.289 | 0.833 ± 0.289 | 0.833 ± 0.289 | 0.833 ± 0.289 |
| Ask User Count | 1.667 ± 0.577 | 2.000 ± 0.000 | 1.333 ± 0.577 | 1.667 ± 0.577 |
| Knowledge Calls Before First Ask | 4.000 ± 0.000 | 2.000 ± 0.000 | 2.667 ± 1.155 | 2.667 ± 1.155 |
| Ambiguity Resolution Rate（固定P1信息需求） | 0.667 ± 0.144 | 0.833 ± 0.144 | 0.667 ± 0.144 | 0.667 ± 0.144 |
| Priority Success | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.667 ± 0.577 | 0.667 ± 0.577 |
| Follow-up Success | 0.667 ± 0.577 | 0.333 ± 0.577 | 0.667 ± 0.577 | 0.667 ± 0.577 |
| Total Reward / run | 0.667 ± 0.577 | 0.567 ± 0.513 | 0.667 ± 0.577 | 0.667 ± 0.577 |

## 三个重复轮次的四任务均值

| 组 | 指标 | r1 | r2 | r3 | 三轮均值±SD |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline | Knowledge Tool Cost | 3.125 | 4.250 | 3.500 | 3.625 ± 0.573 |
| baseline | Ask User Count | 2.000 | 1.500 | 2.250 | 1.917 ± 0.382 |
| baseline | Priority Success | 0.250 | 0.500 | 0.250 | 0.333 ± 0.144 |
| baseline | Follow-up Success | 0.250 | 0.500 | 0.250 | 0.333 ± 0.144 |
| baseline | Total Reward / run | 0.250 | 0.500 | 0.250 | 0.333 ± 0.144 |
| A | Knowledge Tool Cost | 3.250 | 3.125 | 2.750 | 3.042 ± 0.260 |
| A | Ask User Count | 1.750 | 2.000 | 1.750 | 1.833 ± 0.144 |
| A | Priority Success | 0.250 | 0.500 | 0.250 | 0.333 ± 0.144 |
| A | Follow-up Success | 0.250 | 0.250 | 0.250 | 0.250 ± 0.000 |
| A | Total Reward / run | 0.250 | 0.425 | 0.250 | 0.308 ± 0.101 |
| B | Knowledge Tool Cost | 3.125 | 3.000 | 3.000 | 3.042 ± 0.072 |
| B | Ask User Count | 2.000 | 1.500 | 1.500 | 1.667 ± 0.289 |
| B | Priority Success | 0.250 | 0.250 | 0.250 | 0.250 ± 0.000 |
| B | Follow-up Success | 0.250 | 0.250 | 0.250 | 0.250 ± 0.000 |
| B | Total Reward / run | 0.250 | 0.250 | 0.250 | 0.250 ± 0.000 |
| C | Knowledge Tool Cost | 2.750 | 3.250 | 2.750 | 2.917 ± 0.289 |
| C | Ask User Count | 2.000 | 1.250 | 2.000 | 1.750 ± 0.433 |
| C | Priority Success | 0.250 | 0.500 | 0.500 | 0.417 ± 0.144 |
| C | Follow-up Success | 0.000 | 0.500 | 0.500 | 0.333 ± 0.289 |
| C | Total Reward / run | 0.175 | 0.500 | 0.500 | 0.392 ± 0.188 |

## 解释与证据

[比较问题、典型案例和下一步](FINDINGS.md)；[评价标准](EVALUATION_PROTOCOL.md)；[逐run CSV](per_run_metrics.csv)；[逐run JSON](per_run_metrics.json)；[全部语义标注](semantic_annotations.json)；[完整逐任务轨迹](trajectory/)；[指标与证据卡片](task_cards/)。每个语义判断保留工具序号、问答和依据，原始结果另保存于results同名目录。

[四组Prompt完整展开](PROMPTS.md) · [运行矩阵与原始档案](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/README.md) · [原版/修改版诊断](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/original_code_diagnosis_20261107T083430Z/README.md)。
