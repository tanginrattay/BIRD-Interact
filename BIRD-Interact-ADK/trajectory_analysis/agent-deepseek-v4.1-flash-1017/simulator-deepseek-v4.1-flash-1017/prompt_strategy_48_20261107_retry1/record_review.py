"""Save explicit offline analyst labels; no inference or automatic semantic judge."""
import json
from pathlib import Path
from analyze import OUT, RAW, REQUIRED, extract

UNITS = {'credit_11': ['S1', 'S2', 'S3', 'S4', 'S5'], 'virtual_1': ['S1', 'S2', 'S3'],
         'polar_M_4': ['S1', 'S2', 'S3', 'S4', 'S5'], 'cybermarket_1': ['S1', 'S2', 'S3', 'S4']}
USER_UNITS = {'credit_11': ['S1', 'S3', 'S4'], 'virtual_1': ['S1', 'S3'],
              'polar_M_4': ['S1', 'S4'], 'cybermarket_1': ['S1', 'S3']}


def review(run, task, resolved, user_knowledge, asks, evidence, notes=None, redundant=None):
    """Inputs are manually assigned after inspecting the full trajectory evidence.

    asks: [(tool_index, necessary|partially_unnecessary|unnecessary, reason)]
    redundant: [(tool_index, [definition_ids], prior_evidence)] for nonexact equivalence.
    """
    path = OUT / 'semantic_annotations.json'
    annotations = json.loads(path.read_text()) if path.exists() else {}
    record = next(r for r in json.loads((RAW / run / 'eval_a_interact.json').read_text())['results'] if r['task_id'] == task)
    row, events = extract(run, record)
    actual_asks = {e['tool_index'] for e in events if e['tool'] == 'ask_user'}
    assert {a[0] for a in asks} == actual_asks, (run, task, actual_asks, asks)
    resolved = set(resolved)
    assert resolved <= set(UNITS[task])
    covered = (set(row['p1_required_knowledge_ids_retrieved']) | set(user_knowledge)) & REQUIRED[task]
    redundant = redundant or []
    semantic_by_index = {i: set(ids) for i, ids, _ in redundant}
    exact_by_index = {e['tool_index']: set(e.get('exact_duplicate_ids', [])) for e in events if e.get('exact_duplicate_ids')}
    redundant_indices = set(semantic_by_index) | set(exact_by_index)
    union_occurrences = sum(len(semantic_by_index.get(i, set()) | exact_by_index.get(i, set())) for i in redundant_indices)
    extra_no_new = sum(bool(e.get('new_relevant_ids')) and set(e['new_relevant_ids']) <= semantic_by_index.get(e['tool_index'], set()) for e in events)
    unnecessary = sum(label == 'unnecessary' for _, label, _ in asks)
    partial = sum(label == 'partially_unnecessary' for _, label, _ in asks)
    annotations[run + '__' + task] = {
        'metrics': {
            'knowledge_coverage_tools_plus_user': len(covered) / len(REQUIRED[task]),
            'ambiguity_resolution_rate': len(resolved) / len(UNITS[task]),
            'user_semantic_resolution_rate': len(resolved & set(USER_UNITS[task])) / len(USER_UNITS[task]),
            'unnecessary_ask_count': unnecessary, 'partially_unnecessary_ask_count': partial,
            'unnecessary_ask_rate': unnecessary / len(asks) if asks else None,
            'semantic_redundancy_calls': len(redundant),
            'semantic_redundancy_definition_occurrences': sum(len(ids) for _, ids, _ in redundant),
            'semantic_redundancy_including_exact_calls': len(redundant_indices),
            'semantic_redundancy_including_exact_definition_occurrences': union_occurrences,
            'no_new_relevant_information_calls': row['no_new_relevant_information_calls'] + extra_no_new,
        },
        'resolved_information_units': sorted(resolved),
        'unresolved_information_units': sorted(set(UNITS[task]) - resolved),
        'required_knowledge_ids_covered': sorted(covered),
        'user_supplied_knowledge_ids': user_knowledge,
        'coverage_and_resolution_evidence': evidence,
        'ask_reviews': [{'tool_index': i, 'label': label, 'reason': reason} for i, label, reason in asks],
        'semantic_redundancy_evidence': [{'tool_index': i, 'definition_ids': ids, 'prior_evidence': prior} for i, ids, prior in redundant],
        'notes': notes or [],
        'review_method': 'Explicit single-reviewer offline labels grounded in visible evidence and benchmark/KB content; not agent self-evaluation; not blinded or independently replicated.',
    }
    path.write_text(json.dumps(annotations, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit('Import review() to record explicit inspected labels; there is no automatic semantic classifier.')
