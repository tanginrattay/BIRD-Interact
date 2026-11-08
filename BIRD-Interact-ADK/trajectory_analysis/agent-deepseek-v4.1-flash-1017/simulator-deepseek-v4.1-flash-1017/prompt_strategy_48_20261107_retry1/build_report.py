"""Render verified per-run observations and explicit semantic labels as tables."""
import json
import statistics
from analyze import OUT, RAW, TASKS

CONDITIONS = ['baseline', 'A', 'B', 'C']
LABELS = {
    'knowledge_tool_calls': 'Knowledge Tool Calls', 'knowledge_tool_cost': 'Knowledge Tool Cost',
    'single_knowledge_calls': 'Single Knowledge Calls', 'get_all_knowledge_calls': 'Get All Knowledge Calls',
    'name_discovery_calls': 'Name Discovery Calls', 'knowledge_cost_including_names': 'Knowledge Cost incl. Names',
    'unique_definitions_retrieved': 'Unique Definitions Retrieved', 'exact_duplicate_retrievals': 'Exact Duplicate Retrievals（调用）',
    'duplicate_definition_occurrences': 'Exact Duplicate Definition Occurrences',
    'semantic_redundancy_including_exact_calls': 'Semantic Redundancy（调用并集，含精确重复）',
    'semantic_redundancy_calls': 'Additional Semantic Redundancy（跨来源/不同ID）',
    'no_new_relevant_information_calls': 'No New Relevant Information Calls',
    'retrieval_relevance': 'Retrieval Relevance（条目级宏平均）',
    'useful_query_rate': 'Query with Relevant Content Rate',
    'knowledge_coverage_tool_only': 'P1 Knowledge Coverage：tool-only',
    'knowledge_coverage_tools_plus_user': 'P1 Knowledge Coverage：tools+user，最终可靠',
    'knowledge_coverage_ever_correct_seen': 'P1 Knowledge Coverage：ever-correct-seen',
    'phase1_knowledge_calls': 'P1 Knowledge Calls', 'phase1_knowledge_cost': 'P1 Knowledge Cost',
    'phase2_knowledge_calls': 'P2 Knowledge Calls', 'phase2_knowledge_cost': 'P2 Knowledge Cost',
    'ask_user_count': 'Ask User Count', 'knowledge_calls_before_first_ask': 'Knowledge Calls Before First Ask',
    'knowledge_cost_before_first_ask': 'Knowledge Cost Before First Ask', 'first_ask_timing': 'First Ask Timing（工具一基序号）',
    'ambiguity_resolution_rate': 'Ambiguity Resolution Rate（固定P1信息需求）',
    'user_semantic_resolution_rate': 'User-Semantic Resolution Rate（子集）',
    'unnecessary_ask_rate': 'Unnecessary Ask Rate（run宏平均）',
    'unnecessary_ask_count': 'Fully Unnecessary Ask Count', 'partially_unnecessary_ask_count': 'Partially Unnecessary Ask Count',
    'priority_success': 'Priority Success', 'follow_up_success': 'Follow-up Success', 'total_reward': 'Total Reward / run',
    'remaining_budget': 'Remaining Budget', 'total_tool_calls': 'Total Tool Calls（实际执行）',
    'attempted_tool_calls': 'Attempted Tool Calls', 'budget_rejected_calls': 'Budget-Rejected Calls',
    'context_tokens': 'Context Tokens', 'elapsed_seconds': 'Elapsed Seconds',
    'simulator_incorrect_answer_count': 'Simulator Incorrect Answer Count',
    'simulator_incomplete_answer_count': 'Simulator Incomplete Answer Count',
}


def fmt(values):
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return 'NA'
    sd = statistics.stdev(values) if len(values) > 1 else None
    return f'{statistics.mean(values):.3f} ± {sd:.3f}' if sd is not None else f'{values[0]:.3f}（n=1）'


def metric_table(rows, keys):
    lines = ['| 指标（mean ± sample SD） | Baseline | A | B | C |', '| --- | ---: | ---: | ---: | ---: |']
    for key in keys:
        lines.append('| ' + LABELS[key] + ' | ' + ' | '.join(fmt([r.get(key) for r in rows if r['condition'] == c]) for c in CONDITIONS) + ' |')
    return '\n'.join(lines) + '\n\n'


def main():
    rows = json.loads((OUT / 'per_run_metrics.json').read_text())
    groups = {c: [r for r in rows if r['condition'] == c] for c in CONDITIONS}
    review_count = sum(bool(r.get('semantic_review_complete')) for r in rows)
    s = f'# Prompt 策略对照实验\n\n已保存 {len(rows)}/48 次，语义审查 {review_count}/{len(rows)}。'
    s += '四任务 × 四条件 × 三重复；诊断运行不计入。所有率以0–1表示。下表为12个run的均值及样本标准差，混合任务异质性另由逐任务表揭示；每任务每条件只有3次，不能声称统计显著性。\n\n'
    s += '## 控制变量与完整 Prompt\n\n'
    s += 'deepseek/deepseek-flash（Agent与Simulator一致）、a-interact / Lite / 原版v1两阶段 / 非思考 / patience=3 / temperature=0；Agent max_tokens=4096，Simulator action=200 / response=1024，concurrency=1。继承原代理配置。工具、Callback、预算公式、任务和数据库不变；未配置模型或Simulator随机种子。Baseline常量与HEAD逐字一致。Prompt加载改动已通过原版与修改版同环境配对运行验证；两者均正常，无法追认上次中断的确切根因。\n\n'
    relative = '../../../../' + str(RAW.relative_to(OUT.parents[3]))
    s += '| 条件 | 完整 Prompt | 追加规则 |\n| --- | --- | --- |\n'
    for c, description in [('baseline', '无，原文'), ('A', '只考虑工具成本与单项/全量选择'), ('B', '信息需求、已有内容、相关性、解决状态、预算、上下文负担'), ('C', '完整B + 四类不确定性及数据库/知识库/用户来源选择')]:
        s += f'| {c} | [{c}.txt]({relative}/prompts/{c}.txt) | {description} |\n'
    s += '\n## 知识检索\n\n'
    s += metric_table(rows, list(LABELS)[:21])
    s += '知识定义调用只含单项与全量；名称查询另列并纳入含名称的成本。扣费按实际预算差额核验，不把Callback标价直接求和。全量返回条目按冻结可见KB与原隐藏规则重建，不声称恢复截断日志。相关性依内容支持判定，零返回率为NA，失败查询另列在逐run表。相关内容可以重复，因此同时报告无新增相关信息调用。\n\n'
    s += '## 用户交互\n\n'
    s += metric_table(rows, ['ask_user_count', 'knowledge_calls_before_first_ask', 'knowledge_cost_before_first_ask', 'first_ask_timing', 'ambiguity_resolution_rate', 'user_semantic_resolution_rate', 'unnecessary_ask_rate', 'unnecessary_ask_count', 'partially_unnecessary_ask_count'])
    s += '| 组 | 总ask | 完全不必要/总ask | 含部分不必要的上界 | 未询问run |\n| --- | ---: | ---: | ---: | ---: |\n'
    for c, items in groups.items():
        count = sum(r['ask_user_count'] for r in items)
        un = sum(r.get('unnecessary_ask_count', 0) for r in items)
        part = sum(r.get('partially_unnecessary_ask_count', 0) for r in items)
        s += f'| {c} | {count} | {un}/{count} | {un + part}/{count} | {sum(r["no_ask"] for r in items)} |\n'
    s += '\n首次询问时机没有可靠秒级时间戳，使用实际工具序号；没有ask的run记NA。语义标签由单一离线审查者按benchmark/KB与实际问答证据判定，未盲审、未独立双审；它们是可复核标注，不是Agent自评或无误客观真值。\n\n'
    s += '## 整体任务\n\n'
    s += metric_table(rows, ['priority_success', 'follow_up_success', 'total_reward', 'remaining_budget', 'total_tool_calls', 'attempted_tool_calls', 'budget_rejected_calls', 'context_tokens', 'elapsed_seconds', 'simulator_incorrect_answer_count', 'simulator_incomplete_answer_count'])
    s += 'P1/P2主成功率均以全部run为分母，Total Reward表为每run奖励；Context Tokens因原ADK事件未存usage而NA，不能用字符数替代。\n\n'
    s += '| 组 | P1成功 | P2成功 | P2/P1条件成功率 | Reward合计 |\n| --- | ---: | ---: | ---: | ---: |\n'
    for c, items in groups.items():
        p1, p2 = sum(r['priority_success'] for r in items), sum(r['follow_up_success'] for r in items)
        conditional = f'{p2 / p1:.3f}' if p1 else 'NA'
        s += f'| {c} | {p1}/{len(items)} | {p2}/{len(items)} | {conditional} | {sum(r["total_reward"] for r in items):.3f} |\n'
    s += '\n## 每任务三次重复\n\n'
    for tid in TASKS:
        s += f'### {tid}\n\n' + metric_table([r for r in rows if r['task_id'] == tid], ['knowledge_tool_cost', 'knowledge_tool_calls', 'exact_duplicate_retrievals', 'no_new_relevant_information_calls', 'retrieval_relevance', 'knowledge_coverage_tools_plus_user', 'ask_user_count', 'knowledge_calls_before_first_ask', 'ambiguity_resolution_rate', 'priority_success', 'follow_up_success', 'total_reward'])
    s += '## 三个重复轮次的四任务均值\n\n'
    s += '| 组 | 指标 | r1 | r2 | r3 | 三轮均值±SD |\n| --- | --- | ---: | ---: | ---: | ---: |\n'
    for c, items in groups.items():
        for key in ['knowledge_tool_cost', 'ask_user_count', 'priority_success', 'follow_up_success', 'total_reward']:
            means = [statistics.mean([r[key] for r in items if r['repetition'] == rep]) if any(r['repetition'] == rep for r in items) else None for rep in [1, 2, 3]]
            s += f'| {c} | {LABELS[key]} | ' + ' | '.join(f'{v:.3f}' if v is not None else 'NA' for v in means) + f' | {fmt(means)} |\n'
    s += '\n## 解释与证据\n\n[比较问题、典型案例和下一步](FINDINGS.md)；[评价标准](EVALUATION_PROTOCOL.md)；[逐run CSV](per_run_metrics.csv)；[逐run JSON](per_run_metrics.json)；[全部语义标注](semantic_annotations.json)；[完整逐任务轨迹](trajectory/)；[指标与证据卡片](task_cards/)。每个语义判断保留工具序号、问答和依据，原始结果另保存于results同名目录。\n'
    (OUT / 'README.md').write_text(s)


if __name__ == '__main__':
    main()
