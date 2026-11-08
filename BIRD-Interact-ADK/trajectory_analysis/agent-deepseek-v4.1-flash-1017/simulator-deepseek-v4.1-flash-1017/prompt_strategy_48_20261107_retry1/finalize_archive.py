"""Validate and unify finished outputs from the existing repository runner."""
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from analyze import OUT, RAW, REPO, TASKS, SNAPSHOTS


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    metadata = json.loads((RAW / 'metadata.json').read_text())
    for filename, digest in json.loads((RAW / 'source_hashes.json').read_text()).items():
        assert sha(REPO / filename) == digest, filename
    for filename, digest in metadata['prompts_sha256'].items():
        assert sha(RAW / 'prompts' / filename) == digest, filename
    original = subprocess.check_output(['git', 'show', 'HEAD:./system_agent/agent.py'], cwd=REPO, text=True)
    tree = ast.parse(original)
    baseline = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'AINTERACT_INSTRUCTION' for t in n.targets))
    assert baseline == (RAW / 'prompts/baseline.txt').read_text()
    for snapshot in SNAPSHOTS.values():
        assert sha(REPO / snapshot['source']) == snapshot['source_sha256']
    data_path = REPO / 'bird-interact-lite/bird_interact_data.jsonl'
    original_tasks = {t['instance_id']: t for t in map(json.loads, data_path.read_text().splitlines())}
    for tid, task in TASKS.items():
        assert task == original_tasks[tid], tid
    records, matrix, invocation_ids, source_manifest = [], [], set(), []
    definition_calls, mismatches, budget_issues, service_errors = 0, [], [], []
    block_files = sorted(RAW.glob('*_r*/eval_a_interact.json'))
    assert len(block_files) == 12
    for path in block_files:
        condition, repetition = path.parent.name.rsplit('_r', 1)
        repetition = int(repetition)
        data = json.loads(path.read_text())
        rm = data['run_metadata']
        assert rm['system_agent_model'] == metadata['system_agent_model']
        assert rm['user_sim_model'] == metadata['user_sim_model']
        assert rm['prompt_version'] == 'v1' and rm['user_sim_pipeline'] == 'two_stage'
        assert rm['patience'] == 3 and rm['concurrency'] == 1 and rm['dataset'] == 'lite'
        assert {r['task_id'] for r in data['results']} == set(TASKS)
        assert len(data['results']) == 4
        verification = json.loads((path.parent / 'verification.json').read_text())
        assert verification['instruction_sha256'] == sha(RAW / 'prompts' / f'{condition}.txt')
        assert verification['health']['6000']['adk_available']
        source_manifest.append({'path': str(path.relative_to(RAW)), 'sha256': sha(path)})
        for index, r in enumerate(data['results']):
            tid = r['task_id']
            assert not r.get('error'), (condition, repetition, tid)
            assert r.get('tool_trajectory') and r.get('adk_events')
            invocation = {e['invocation_id'] for e in r['adk_events'] if e.get('invocation_id')}
            assert invocation and not (invocation & invocation_ids)
            invocation_ids |= invocation
            matrix.append((condition, repetition, tid))
            records.append({**r, 'experiment_condition': condition, 'repetition': repetition,
                            'logical_run_id': f'{condition}_r{repetition}__{tid}',
                            'source_result_file': str(path.relative_to(RAW)), 'source_record_index': index})
            visible = {e['knowledge']: e for e in SNAPSHOTS[tid]['visible_entries']}
            previous_budget = None
            for i, e in enumerate(r['tool_trajectory'], 1):
                if previous_budget is not None and e.get('budget_before') != previous_budget:
                    budget_issues.append([path.parent.name, tid, i, previous_budget, e.get('budget_before')])
                previous_budget = e.get('budget_after')
                name, logged = e['tool'], str(e['result'])
                if name not in ['get_knowledge_definition', 'get_all_knowledge_definitions']:
                    continue
                if 'Budget exhausted' in logged and 'MUST call submit_sql' in logged:
                    continue
                requested = e['args'].get('knowledge_name')
                expected = (json.dumps(visible[requested], indent=2) if requested in visible else 'Knowledge not found.') if name == 'get_knowledge_definition' else json.dumps(list(visible.values()), indent=2)
                if logged not in [expected, expected[:2000] + '...<truncated>']:
                    mismatches.append([path.parent.name, tid, i])
                expected_cost = .5 if name == 'get_knowledge_definition' else 1.
                assert e['budget_before'] - e['budget_after'] == expected_cost, (path, tid, i)
                definition_calls += 1
        for line in (path.parent / 'services.log').read_text().splitlines():
            if re.search(r'LLM call failed|ServiceUnavailableError|Traceback|ERROR:', line):
                service_errors.append({'block': path.parent.name, 'line': line})
    expected_matrix = {(c, rep, tid) for c in ['baseline', 'A', 'B', 'C'] for rep in [1, 2, 3] for tid in TASKS}
    assert set(matrix) == expected_matrix and len(matrix) == len(set(matrix)) == 48
    assert not mismatches and not budget_issues and not service_errors
    rows = json.loads((OUT / 'per_run_metrics.json').read_text())
    reviews = json.loads((OUT / 'semantic_annotations.json').read_text())
    assert len(rows) == len(reviews) == 48 and all(r['semantic_review_complete'] for r in rows)
    assert {r['run'] + '__' + r['task_id'] for r in rows} == set(reviews)
    for r in rows:
        assert r['knowledge_tool_calls'] == r['single_knowledge_calls'] + r['get_all_knowledge_calls']
        assert r['attempted_tool_calls'] == r['recorded_tool_calls']
        assert r['knowledge_tool_cost'] == .5 * r['single_knowledge_calls'] + r['get_all_knowledge_calls']
        assert r['context_tokens'] is None
    metadata['dataset_file_sha256'] = sha(data_path)
    metadata['selected_task_file_sha256'] = sha(RAW / 'tasks.jsonl')
    dump(RAW / 'metadata.json', metadata)
    dump(RAW / 'eval_a_interact.json', {
        'mode': 'a-interact', 'run_metadata': metadata,
        'metrics': {'total_tasks': 48, 'total_reward': sum(r['total_reward'] for r in records),
                    'average_reward': sum(r['total_reward'] for r in records) / 48,
                    'phase1_count': sum(r['phase1_passed'] for r in records),
                    'phase2_count': sum(r['phase2_passed'] for r in records)},
        'results': records})
    dump(RAW / 'summary.json', json.loads((OUT / 'group_summary.json').read_text()))
    dump(RAW / 'validation.json', {
        'complete': True, 'planned_runs': 48, 'valid_completed_runs': 48, 'task_errors': 0,
        'conditions': dict(Counter(c for c, _, _ in matrix)), 'tasks': dict(Counter(tid for _, _, tid in matrix)),
        'balanced_matrix_verified': True, 'all_sources_and_prompts_match_frozen_hashes': True,
        'baseline_matches_HEAD': True, 'benchmark_and_KB_unchanged': True,
        'all_tool_trajectories_and_adk_events_present': True, 'invocation_ids_disjoint_between_runs': True,
        'session_isolation_basis': 'Original init_session reset=True, new create_session, fresh initial state; per-block service restart; disjoint invocation IDs. Session IDs are not included by the original runner.',
        'knowledge_returns_verified': definition_calls, 'knowledge_return_mismatches': mismatches,
        'budget_chain_mismatches': budget_issues, 'service_errors_detected': service_errors,
        'semantic_reviews_complete': 48, 'context_tokens_available': False,
        'diagnostic_runs_included': 0})
    dump(RAW / 'source_result_manifest.json', source_manifest)
    print(f'Validated 48 independent runs, {definition_calls} knowledge returns, zero errors/mismatches.')


if __name__ == '__main__':
    main()
