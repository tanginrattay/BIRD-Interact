"""Offline extraction only; never calls the agent, simulator, or database."""
import csv
import hashlib
import json
import re
import statistics
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
RAW = REPO / 'results' / OUT.relative_to(REPO / 'trajectory_analysis')
TASKS = {t['instance_id']: t for t in map(json.loads, (RAW / 'tasks.jsonl').read_text().splitlines())}
SNAPSHOTS = json.loads((RAW / 'visible_knowledge_snapshot.json').read_text())
DEFINITION_TOOLS = {'get_knowledge_definition', 'get_all_knowledge_definitions'}
KNOWLEDGE_TOOLS = DEFINITION_TOOLS | {'get_all_external_knowledge_names'}
REQUIRED = {'credit_11': {7, 14, 50}, 'virtual_1': {34, 49}, 'polar_M_4': {7, 53}, 'cybermarket_1': {16, 23}}
# Content-level direct support, including needed field/cohort meanings.
RELEVANT = {'credit_11': {7, 51}, 'virtual_1': {3, 7, 49}, 'polar_M_4': {53}, 'cybermarket_1': {23}}
COST = {'get_knowledge_definition': .5, 'get_all_knowledge_definitions': 1., 'get_all_external_knowledge_names': .5}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def fence(value, language='json'):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    marker = '`' * max(3, 1 + max([len(s) for s in re.findall(r'`+', text)] or [0]))
    return f'{marker}{language}\n{text}\n{marker}\n\n'


def extract(block, record):
    tid = record['task_id']
    task = TASKS[tid]
    db = task['selected_database']
    kb = SNAPSHOTS[tid]['visible_entries']
    visible = {e['knowledge']: e for e in kb}
    trace = record.get('tool_trajectory', [])
    condition, repetition = block.rsplit('_r', 1)
    row = {'run': block, 'condition': condition, 'repetition': int(repetition), 'task_id': tid,
           'priority_success': int(record.get('phase1_passed', False)),
           'follow_up_success': int(record.get('phase2_passed', False)),
           'total_reward': record.get('total_reward', 0), 'remaining_budget': record.get('budget_remaining'),
           'total_tool_calls': 0, 'recorded_tool_calls': len(trace),
           'attempted_tool_calls': 0, 'budget_rejected_calls': 0,
           'knowledge_tool_calls': 0, 'knowledge_tool_cost': 0., 'knowledge_cost_including_names': 0.,
           'single_knowledge_calls': 0, 'get_all_knowledge_calls': 0, 'name_discovery_calls': 0,
           'unique_definitions_retrieved': 0, 'exact_duplicate_retrievals': 0, 'duplicate_definition_occurrences': 0,
           'repeated_failed_lookups': 0, 'failed_knowledge_lookups': 0,
           'no_new_relevant_information_calls': 0, 'retrieval_relevance': None, 'useful_query_rate': None,
           'knowledge_coverage_tool_only': 0., 'ask_user_count': 0,
           'knowledge_calls_before_first_ask': None, 'knowledge_cost_before_first_ask': None,
           'first_ask_timing': None, 'first_ask_normalized_position': None,
           'context_tokens': None, 'elapsed_seconds': record.get('elapsed_seconds'),
           'error': record.get('error')}
    for ev in record.get('adk_events', []):
        row['attempted_tool_calls'] += sum(p.get('type') == 'function_call' for p in ev.get('content', {}).get('parts', []))
    seen, seen_relevant, failed_names, p1_seen = set(), set(), set(), set()
    occurrences, relevant_occurrences, useful_calls, charged_calls = 0, 0, 0, 0
    phase = 1
    evidence = []
    for index, event in enumerate(trace, 1):
        name = event['tool']
        result = str(event.get('result', ''))
        rejected = 'Budget exhausted' in result and 'MUST call submit_sql' in result
        if rejected:
            row['budget_rejected_calls'] += 1
            evidence.append({'tool_index': index, 'tool': name, 'rejected': True, 'result': result})
            continue
        row['total_tool_calls'] += 1
        before, after = event.get('budget_before'), event.get('budget_after')
        paid = max(0, before - after) if before is not None and after is not None and after >= 0 else None
        if name in KNOWLEDGE_TOOLS:
            assert paid is not None, (block, tid, index, event)
            row['knowledge_cost_including_names'] += paid
        if name == 'get_all_external_knowledge_names':
            row['name_discovery_calls'] += 1
        if name in DEFINITION_TOOLS:
            row['knowledge_tool_calls'] += 1
            row['knowledge_tool_cost'] += paid
            row['single_knowledge_calls' if name == 'get_knowledge_definition' else 'get_all_knowledge_calls'] += 1
            charged_calls += 1
            requested = event.get('args', {}).get('knowledge_name', '')
            entries = ([visible[requested]] if requested in visible else []) if name == 'get_knowledge_definition' else list(visible.values())
            # Do not invent definitions when the real call returned an error.
            if result.startswith('Error:') or 'Knowledge not found' in result or result.startswith('{"error"'):
                entries = []
            ids = {e['id'] for e in entries}
            relevant_ids = RELEVANT[tid] | ({13} if tid == 'cybermarket_1' and phase == 2 else set())
            useful = ids & relevant_ids
            duplicate = ids & seen
            if duplicate:
                row['exact_duplicate_retrievals'] += 1
                row['duplicate_definition_occurrences'] += len(duplicate)
            if not entries:
                row['failed_knowledge_lookups'] += 1
                if requested in failed_names:
                    row['repeated_failed_lookups'] += 1
                failed_names.add(requested)
            if useful:
                useful_calls += 1
            if not (useful - seen_relevant):
                row['no_new_relevant_information_calls'] += 1
            occurrences += len(ids)
            relevant_occurrences += len(useful)
            evidence.append({'tool_index': index, 'phase': phase, 'tool': name, 'requested': requested,
                             'paid': paid, 'returned_ids': sorted(ids), 'relevant_ids': sorted(useful),
                             'new_relevant_ids': sorted(useful - seen_relevant), 'exact_duplicate_ids': sorted(duplicate),
                             'reconstruction': 'Frozen source KB + original deleted_knowledge filter; checked against logged result',
                             'result': result})
            seen |= ids
            seen_relevant |= useful
            if phase == 1:
                p1_seen |= ids
        if name == 'ask_user':
            row['ask_user_count'] += 1
            if row['first_ask_timing'] is None:
                row['first_ask_timing'] = index
                row['knowledge_calls_before_first_ask'] = row['knowledge_tool_calls']
                row['knowledge_cost_before_first_ask'] = row['knowledge_tool_cost']
            evidence.append({'tool_index': index, 'phase': phase, 'tool': name, 'question': event['args'].get('question'), 'answer': result})
        if name == 'submit_sql':
            evidence.append({'tool_index': index, 'phase': phase, 'tool': name, 'sql': event['args'].get('sql'), 'result': result})
            if 'Follow-up question:' in result:
                phase = 2
    row['unique_definitions_retrieved'] = len(seen)
    row['retrieval_relevance'] = relevant_occurrences / occurrences if occurrences else None
    row['relevant_definition_occurrences'] = relevant_occurrences
    row['returned_definition_occurrences'] = occurrences
    row['useful_query_rate'] = useful_calls / charged_calls if charged_calls else None
    row['knowledge_coverage_tool_only'] = len(p1_seen & REQUIRED[tid]) / len(REQUIRED[tid])
    row['first_ask_normalized_position'] = row['first_ask_timing'] / len(trace) if row['first_ask_timing'] else None
    row['no_ask'] = int(row['ask_user_count'] == 0)
    row['p1_required_knowledge_ids_retrieved'] = sorted(p1_seen & REQUIRED[tid])
    return row, evidence


def summarize(rows):
    output = {}
    columns = [k for k, v in rows[0].items() if isinstance(v, (int, float)) or v is None]
    for condition in ['baseline', 'A', 'B', 'C']:
        items = [r for r in rows if r['condition'] == condition]
        group = {'n': len(items), 'metrics': {}}
        if not items:
            output[condition] = group
            continue
        for key in columns:
            values = [r[key] for r in items if isinstance(r.get(key), (int, float))]
            group['metrics'][key] = {'n_observed': len(values), 'mean': statistics.mean(values) if values else None,
                                     'sample_sd': statistics.stdev(values) if len(values) > 1 else None}
        group['relevance_micro'] = sum(r['relevant_definition_occurrences'] for r in items) / sum(r['returned_definition_occurrences'] for r in items) if sum(r['returned_definition_occurrences'] for r in items) else None
        group['repetition_means'] = {str(rep): {key: statistics.mean([r[key] for r in items if r['repetition'] == rep and isinstance(r.get(key), (int, float))]) for key in columns if any(r['repetition'] == rep and isinstance(r.get(key), (int, float)) for r in items)} for rep in [1, 2, 3]}
        output[condition] = group
    return output


def main():
    (OUT / 'trajectory').mkdir(exist_ok=True)
    (OUT / 'task_cards').mkdir(exist_ok=True)
    rows, all_evidence, manifest = [], {}, []
    for path in sorted(RAW.glob('*_r*/eval_a_interact.json')):
        data = json.loads(path.read_text())
        manifest.append({'path': str(path.relative_to(REPO)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for record in data['results']:
            row, evidence = extract(path.parent.name, record)
            key = row['run'] + '__' + row['task_id']
            rows.append(row)
            all_evidence[key] = evidence
            (OUT / 'trajectory' / f'{key}.md').write_text(f'# {key}\n\n原始结果全部字段，保留源日志既有截断。\n\n' + fence(record))
            (OUT / 'task_cards' / f'{key}.md').write_text(f'# {key}\n\n' + fence(row) + '## 检索、询问和提交证据\n\n' + fence(evidence))
    if not rows:
        return
    annotation_path = OUT / 'semantic_annotations.json'
    if annotation_path.exists():
        annotations = json.loads(annotation_path.read_text())
        for row in rows:
            key = row['run'] + '__' + row['task_id']
            if key in annotations:
                row.update(annotations[key]['metrics'])
    dump(OUT / 'per_run_metrics.json', rows)
    dump(OUT / 'retrieval_evidence.json', all_evidence)
    dump(OUT / 'source_manifest.json', manifest)
    dump(OUT / 'group_summary.json', summarize(rows))
    dump(OUT / 'per_task_summary.json', {tid: summarize([r for r in rows if r['task_id'] == tid]) for tid in TASKS})
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / 'per_run_metrics.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Extracted {len(rows)}/48 runs')


if __name__ == '__main__':
    main()
