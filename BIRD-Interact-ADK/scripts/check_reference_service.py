"""Exactly three live clarifications against the restored simulator HTTP service."""
import json
from pathlib import Path
from datetime import datetime, timezone
import httpx
from shared.config import settings


def main():
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = Path('results/reference_protocol_qwen_20261013') / f'service_three_{run_id}.json'
    tasks = {t['instance_id']: t for t in map(json.loads, Path(settings.data_path).read_text().splitlines())}
    cases = [('alien_1', 'Does atmospheric conditions mean weather or seeing quality, and are usable signals those with SNR greater than zero?'),
             ('alien_2', 'What do you mean by the BFR measure?'),
             ('alien_3', 'By problematic events do you mean signals whose interference label is High?')]
    report = {'model': settings.user_sim_model, 'pipeline': 'original_two_stage',
              'prompt_version': settings.prompt_version, 'thinking': settings.user_sim_enable_thinking,
              'scope': 'Three HTTP clarification requests; six model calls if both stages execute. No SQL scoring.',
              'health': {}, 'cases': []}
    with httpx.Client(timeout=120, trust_env=False) as client:
        for port in (6000, 6001, 6002):
            response = client.get(f'http://localhost:{port}/health');response.raise_for_status()
            report['health'][str(port)] = response.json()
        for index, (task_id, question) in enumerate(cases):
            sid = f'reference3_{run_id}_{index}'
            payload = {'task_id':sid, 'task_data':tasks[task_id]}
            for port in (6002, 6001):
                response=client.post(f'http://localhost:{port}/init_task',json=payload)
                response.raise_for_status()
            state=client.get(f'http://localhost:6001/debug_state/{sid}').json()
            if not state.get('schema_len'):
                raise RuntimeError('Simulator schema is missing')
            response=client.post('http://localhost:6001/ask',json={'task_id':sid,'question':question})
            response.raise_for_status()
            answer=response.json()['answer']
            report['cases'].append({'task_id':task_id,'service_id':sid,'question':question,
                                   'schema_len':state['schema_len'],'answer':answer,
                                   'fallback':answer == "I'm not sure I understand your question."})
            out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
            print(f'{index+1}. {task_id}: {answer}',flush=True)
        report['summary']={'requests':len(report['cases']), 'nonempty':sum(bool(c['answer'].strip()) for c in report['cases']),
                           'fallbacks':sum(c['fallback'] for c in report['cases'])}
        out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
        print(f'Report: {out}',flush=True)
        print(report['summary'],flush=True)


if __name__ == '__main__':
    main()
