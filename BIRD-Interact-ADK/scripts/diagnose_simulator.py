"""Replay action-only failures through the original simulator HTTP endpoint.

Observational wrappers record actual HTTP JSON and stage results without changing
prompts, response parsing, model parameters, or transport. Artifacts include
private benchmark context, but never API headers or keys.
"""
import argparse
from contextvars import ContextVar
from datetime import datetime, timezone
import functools
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from unittest.mock import patch
import uuid

import httpx
import uvicorn

from shared.config import settings
from user_simulator import server

ACTIVE = ContextVar('simulator_diagnostic_record', default=None)
REAL_CLIENT = httpx.Client


class ObservedClient(REAL_CLIENT):
    def __init__(self, *args, **kwargs):
        hooks = {key: list(value) for key, value in kwargs.pop('event_hooks', {}).items()}
        hooks.setdefault('request', []).append(self.record_request)
        hooks.setdefault('response', []).append(self.record_response)
        super().__init__(*args, event_hooks=hooks, **kwargs)

    @staticmethod
    def record_request(request):
        active = ACTIVE.get()
        if active is not None:
            entry = {'request_json': json.loads(request.content)}
            active['stage']['calls'].append(entry)
            request.extensions['diagnostic_entry'] = entry

    @staticmethod
    def record_response(response):
        entry = response.request.extensions.get('diagnostic_entry')
        if entry is not None:
            response.read()
            entry['http_status'] = response.status_code
            entry['response_json'] = response.json()


def install_wrappers(stack, records):
    original_ask = server._ask_sync
    @functools.wraps(original_ask)
    def observed_ask(state, question):
        record = {'task_id': state.task_data['instance_id'], 'question': question,
                  'schema_sha256': hashlib.sha256(state.db_schema.encode()).hexdigest(), 'stages': []}
        token = ACTIVE.set({'record': record, 'stage': None})
        try:
            record['answer'] = original_ask(state, question)
            return record['answer']
        except Exception as exc:
            record['error_type'] = type(exc).__name__
            raise
        finally:
            records.append(record)
            ACTIVE.reset(token)
    stack.enter_context(patch.object(server, '_ask_sync', observed_ask))
    for name, stage_name in [('_parse_action', 'action_parser'), ('_generate_response', 'response_generator')]:
        original = getattr(server, name)
        def make_wrapper(func, label):
            @functools.wraps(func)
            def observed_stage(*args, **kwargs):
                active = ACTIVE.get()
                stage = {'stage': label, 'calls': []}
                active['record']['stages'].append(stage)
                active['stage'] = stage
                try:
                    stage['parsed_output'] = func(*args, **kwargs)
                    return stage['parsed_output']
                except Exception as exc:
                    stage['error_type'] = type(exc).__name__
                    raise
            return observed_stage
        stack.enter_context(patch.object(server, name, make_wrapper(original, stage_name)))
    stack.enter_context(patch.object(httpx, 'Client', ObservedClient))


def main():
    from contextlib import ExitStack
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--port', type=int, default=6101)
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    source = json.loads(Path(args.source).read_text())
    cases = []
    for result in source['results']:
        for tool in result.get('tool_trajectory', []):
            if tool.get('tool') == 'ask_user' and re.fullmatch(r'(?:labeled\(.*\)|unlabeled\(.*\)|unanswerable\(\))', str(tool.get('result', '')), re.S):
                cases.append({'task_id': result['task_id'], 'question': tool['args']['question'], 'previous_answer': tool['result']})
    if len(cases) != 2:
        raise ValueError(f'Expected exactly two prior failures, got {len(cases)}')
    tasks = {t['instance_id']: t for t in map(json.loads, Path(settings.data_path).read_text().splitlines())}
    records = []
    report = {'source': str(Path(args.source).resolve()), 'model': settings.user_sim_model,
              'prompt_version': server.PROMPT_VERSION, 'thinking': settings.user_sim_enable_thinking,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'cases': cases, 'records': records,
              'scope': 'Two exact failed questions, once each, original HTTP /ask and both original stages; no new system-agent generation.',
              'code_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                              ['user_simulator/server.py','user_simulator/prompts.py','user_simulator/bailian.py']}}
    def save():
        tmp = out/'trace.tmp'
        tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        tmp.replace(out/'trace.json')
    with ExitStack() as stack:
        install_wrappers(stack, records)
        instance = uvicorn.Server(uvicorn.Config(server.app, host='127.0.0.1', port=args.port, log_level='warning'))
        thread = threading.Thread(target=instance.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if instance.started:
                    break
                if not thread.is_alive():
                    raise RuntimeError('Diagnostic simulator failed to start')
                time.sleep(0.1)
            if not instance.started:
                raise RuntimeError('Diagnostic simulator startup timed out')
            with REAL_CLIENT(timeout=180, trust_env=False) as client:
                for case in cases:
                    sid = 'diag_' + uuid.uuid4().hex[:12]
                    payload = {'task_id': sid, 'task_data': {**tasks[case['task_id']], '_interact_mode':'a-interact'}}
                    try:
                        resp=client.post(f'http://localhost:{settings.db_env_port}/init_task', json=payload)
                        resp.raise_for_status()
                        resp=client.post(f'http://127.0.0.1:{args.port}/init_task', json=payload)
                        resp.raise_for_status()
                        state=client.get(f'http://127.0.0.1:{args.port}/debug_state/{sid}').json()
                        if state['schema_len'] <= 0:
                            raise RuntimeError('Missing simulator schema')
                        resp=client.post(f'http://127.0.0.1:{args.port}/ask',json={'task_id':sid,'question':case['question']})
                        resp.raise_for_status()
                        case['http_answer'] = resp.json()['answer']
                        save()
                        print(case['task_id'], repr(case['http_answer']), flush=True)
                        for stage in records[-1]['stages']:
                            for call in stage['calls']:
                                raw = call.get('response_json', {})
                                choice = (raw.get('choices') or [{}])[0]
                                print(stage['stage'], 'finish=',choice.get('finish_reason'), 'usage=',raw.get('usage'), flush=True)
                    finally:
                        cleanup=client.post(f'http://localhost:{settings.db_env_port}/cleanup_task',json={'task_id':sid})
                        case['cleanup_http_status']=cleanup.status_code
                        save()
        finally:
            instance.should_exit = True
            thread.join(timeout=10)
            save()
    print('Saved:', out/'trace.json', flush=True)


if __name__ == '__main__':
    main()
