"""Validate and derive counting fields from explicit evidence labels."""
import json
from analyze import OUT, RAW, extract


def main():
    path = OUT / 'semantic_annotations.json'
    annotations = json.loads(path.read_text())
    for key, review in annotations.items():
        run, tid = key.split('__')
        record = next(r for r in json.loads((RAW / run / 'eval_a_interact.json').read_text())['results'] if r['task_id'] == tid)
        row, events = extract(run, record)
        asks = review['ask_reviews']
        assert {q['tool_index'] for q in asks} == {e['tool_index'] for e in events if e['tool'] == 'ask_user'}, key
        semantic = {e['tool_index']: set(e['definition_ids']) for e in review.get('semantic_redundancy_evidence', [])}
        exact = {e['tool_index']: set(e['exact_duplicate_ids']) for e in events if e.get('exact_duplicate_ids')}
        indices = set(semantic) | set(exact)
        m = review['metrics']
        m['semantic_redundancy_including_exact_calls'] = len(indices)
        m['semantic_redundancy_including_exact_definition_occurrences'] = sum(len(semantic.get(i, set()) | exact.get(i, set())) for i in indices)
        m['no_new_relevant_information_calls'] = row['no_new_relevant_information_calls'] + sum(bool(e.get('new_relevant_ids')) and set(e['new_relevant_ids']) <= semantic.get(e['tool_index'], set()) for e in events)
        m.setdefault('knowledge_coverage_ever_correct_seen', m['knowledge_coverage_tools_plus_user'])
        m.setdefault('simulator_incorrect_answer_count', len(review.get('simulator_issues', [])))
        m.setdefault('simulator_incomplete_answer_count', 0)
        m['unnecessary_ask_upper_bound'] = (m['unnecessary_ask_count'] + m['partially_unnecessary_ask_count']) / len(asks) if asks else None
        review.setdefault('review_method', 'Explicit single-reviewer offline labels grounded in actual evidence and benchmark/KB; not agent self-evaluation; unblinded, without independent replication.')
    path.write_text(json.dumps(annotations, ensure_ascii=False, indent=2) + '\n')
    print(f'Validated {len(annotations)} explicit reviews')


if __name__ == '__main__':
    main()
