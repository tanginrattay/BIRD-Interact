"""Technical-only State audit; no grading of requirement/value semantics."""
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from system_agent.requirement_state import Requirement, apply_update, empty_state
from system_agent.requirement_tracking import extract_state_update, START, END
RUN=Path(__file__).resolve().parent
result=json.loads((RUN/'eval_a_interact.json').read_text())
metadata=json.loads((RUN/'metadata.json').read_text())
observations=[json.loads(line) for line in (RUN/'state_observations.jsonl').read_text().splitlines()]
expected=metadata['selection']['task_ids']
rows=[]
all_issues=[]

def parse_text(content):
    text=''.join(p.get('text','') for p in (content or {}).get('parts',[]) if not p.get('thought'))
    return text, {"state_update": extract_state_update(text)}


for task_id in expected:
    item=next(r for r in result['results'] if r['task_id']==task_id)
    saved=json.loads((RUN/'sessions'/(task_id+'.json')).read_text())
    session=saved['session'];state=session['state']
    history=state.get('requirement_state_history',[])
    taskobs=[o for o in observations if o.get('task_id')==task_id]
    requests=[o for o in taskobs if o['type']=='model_request']
    responses=[o for o in taskobs if o['type']=='model_response' and not o.get('partial')]
    issues=[]
    if len(requests)!=len(responses):issues.append('request/response counts differ')
    previous=empty_state(task_id)
    later_reads=0
    for index,(request,response) in enumerate(zip(requests,responses)):
        if request['state']!=previous:issues.append(f'input State differs from previous response at {index+1}')
        if request.get('injected_state')!={'requirements':request['state']['requirements']}:issues.append(f'actual injected State mismatch at {index+1}')
        if response['state_before']!=request['state']:issues.append(f'State changed during model invocation {index+1}')
        if index:later_reads+=1
        if not request['native_tools'] or request['response_schema'] is not None or request['tool_config'] is not None:
            issues.append(f'native request configuration mismatch at {index+1}')
        if response['state_after'].get('task_id')!=task_id:issues.append('cross-task State owner')
        if not response['state_error']:
            if not response['callback_returned_none']:issues.append('accepted response was replaced')
            if response['generated_native_calls']!=response['forwarded_native_calls']:issues.append('accepted calls modified')
        else:
            if response['state_after']!=response['state_before']:issues.append('rejected update changed State')
            if not response['callback_returned_none']:issues.append('rejected update replaced original response')
            if response['generated_native_calls']!=response['forwarded_native_calls']:issues.append('rejected update changed native calls')
        if not response['original_response_unchanged']:issues.append('original response mutated')
        previous=response['state_after']
    replay=empty_state(task_id)
    accepted_snapshots=[]
    timeline=[]
    errors=[]
    recovered=[]
    for index,entry in enumerate(history):
        content=entry.get('model_content');text=''.join(p.get('text','') for p in (content or {}).get('parts',[]) if not p.get('thought'))
        call_names=[p['function_call']['name'] for p in (content or {}).get('parts',[]) if p.get('function_call')]
        if entry['accepted']:
            try:
                _,payload=parse_text(content)
                if 'DSML' in text or ('<requirement_state_update' in text and (START not in text or END not in text)):
                    recovered.append(index+1)
                replay,changes=apply_update(replay,payload['state_update'],task_id)
                if replay['revision']!=entry['revision'] or changes!=entry['changes']:issues.append(f'replay mismatch at {index+1}')
                accepted_snapshots.append(copy.deepcopy(replay))
            except Exception as exc:issues.append(f'accepted patch replay error at {index+1}: {exc}')
        else:
            try:
                _, rejected_payload=parse_text(content)
                apply_update(replay,rejected_payload['state_update'],task_id)
            except (ValueError,TypeError,KeyError):pass
            else:issues.append(f'rejected patch unexpectedly valid at {index+1}')
            technical_type='invalid_state'
            if entry['error']=='stale base_revision':technical_type='stale_revision'
            elif 'DSML' in text:technical_type='missing_end_marker_with_DSML_tail'
            elif not text.strip() or 'state_update' not in text:technical_type='missing_state_update'
            elif 'block order' in entry['error']:technical_type='malformed_marker'
            expected_revision=entry['revision'];supplied_revision=None
            match=re.search(r'"base_revision"\s*:\s*(\d+)',text)
            if match:supplied_revision=int(match.group(1))
            errors.append({'response_index':index+1,'type':technical_type,'error':entry['error'],
                           'expected_revision':expected_revision,'supplied_revision':supplied_revision,
                           'generated_native_tools':call_names,'raw_text':text})
        timeline.append({'response_index':index+1,'accepted':entry['accepted'],'revision':entry['revision'],
                         'requirements':len(replay['requirements']),'changed_requirements':len(entry['changes']),
                         'generated_native_tools':call_names,'error':entry['error']})
    final=state.get('requirement_state')
    if replay!=final:issues.append('replayed State differs from saved final State')
    if item.get('requirement_state')!=final:issues.append('evaluation result differs from Session State')
    if not saved['returned_state_matches_saved_requirement_state']:issues.append('runtime return differs from fresh get_session')
    for record in (final or {}).get('requirements',[]):
        try:Requirement.model_validate(record)
        except Exception as exc:issues.append('final State structural validation: '+str(exc))
    event_snapshots=[];event_call_ids=[];event_result_ids=[]
    for event in session.get('events',[]):
        delta=event.get('actions',{}).get('state_delta',{})
        if 'requirement_state' in delta:event_snapshots.append(delta['requirement_state'])
        for part in (event.get('content') or {}).get('parts',[]):
            if part.get('function_call'):event_call_ids.append(part['function_call'].get('id'))
            if part.get('function_response'):event_result_ids.append(part['function_response'].get('id'))
    if event_snapshots!=accepted_snapshots:issues.append('persisted Event state_delta differs from accepted updates')
    forwarded=[c['id'] for o in responses for c in o['forwarded_native_calls']]
    if Counter(forwarded)!=Counter(event_call_ids):issues.append('native call IDs not preserved in events')
    if Counter(event_call_ids)!=Counter(event_result_ids):issues.append('native call/result ID association mismatch')
    session_ids={o['session_id'] for o in taskobs}
    if session_ids!={saved['session_id']}:issues.append('observation session owner mismatch')
    stop=[o.get('stop_text') for o in taskobs if o['type']=='before_model_stop']
    if item.get('error'):termination='runtime_error'
    elif state.get('task_done'):termination='task_done'
    elif state.get('budget_remaining',0)<0:termination='original_budget_exit'
    elif state.get('model_turns',0)>60:termination='model_turn_limit'
    else:termination='stopped_without_task_done'
    row={'task_id':task_id,'database':item['database'],'model_calls':len(requests),'accepted_updates':sum(h['accepted'] for h in history),
         'rejected_updates':len(errors),'revision':final['revision'],'requirements':len(final['requirements']),
         'native_calls_generated':sum(len(o['generated_native_calls']) for o in responses),
         'native_calls_forwarded':len(forwarded),'native_calls_blocked_by_state':sum(max(0,len(o['generated_native_calls'])-len(o['forwarded_native_calls'])) for o in responses),
         'native_calls_forwarded_despite_state_error':sum(len(o['forwarded_native_calls']) for o in responses if o['state_error']),
         'recovered_outer_text_response_indexes':recovered,
         'tool_trajectory_entries':len(item.get('tool_trajectory',[])),'submissions':sum(t['tool']=='submit_sql' for t in item.get('tool_trajectory',[])),
         'subsequent_state_reads_checked':later_reads,'persisted_event_updates_checked':len(event_snapshots),
         'structural_checks_passed':not issues,'structural_issues':issues,'session_id':saved['session_id'],
         'termination':termination,'runtime_error':item.get('error'),'protocol_errors':errors,
         'budget_remaining_raw':state.get('budget_remaining'),'phase1_passed':item['phase1_passed'],'phase2_passed':item['phase2_passed'],
         'stop_messages':stop,'timeline':timeline,
         'model_usage':{key:sum(h.get('usage',{}).get(key,0) or 0 for h in history) for key in ['prompt_token_count','candidates_token_count','total_token_count']}}
    rows.append(row)
    all_issues.extend({'task_id':task_id,'issue':i} for i in issues)
summary={
 'scope':'Runtime/protocol/persistence only; no State semantics or SQL analysis',
 'git_head':metadata['git_head'],'task_count':len(rows),'expected_task_count':len(expected),
 'task_set_matches':set(r['task_id'] for r in result['results'])==set(expected),
 'runner_exit_code':json.loads((RUN/'run_completion.json').read_text()).get('runner_exit_code'),
 'runtime_errors':sum(bool(r['runtime_error']) for r in rows),
 'tasks_with_state_protocol_error':sum(bool(r['protocol_errors']) for r in rows),
 'tasks_without_state_protocol_error':sum(not r['protocol_errors'] for r in rows),
 'termination_counts':dict(Counter(r['termination'] for r in rows)),
 'model_calls':sum(r['model_calls'] for r in rows),'accepted_state_updates':sum(r['accepted_updates'] for r in rows),
 'rejected_state_updates':sum(r['rejected_updates'] for r in rows),'state_error_types':dict(Counter(e['type'] for r in rows for e in r['protocol_errors'])),
 'subsequent_state_reads_checked':sum(r['subsequent_state_reads_checked'] for r in rows),
 'persisted_event_updates_checked':sum(r['persisted_event_updates_checked'] for r in rows),
 'native_calls_generated':sum(r['native_calls_generated'] for r in rows),'native_calls_forwarded':sum(r['native_calls_forwarded'] for r in rows),
 'native_calls_blocked_by_state':sum(r['native_calls_blocked_by_state'] for r in rows),
 'native_calls_forwarded_despite_state_error':sum(r['native_calls_forwarded_despite_state_error'] for r in rows),
 'outer_text_recoveries':sum(len(r['recovered_outer_text_response_indexes']) for r in rows),
 'distinct_sessions':len({r['session_id'] for r in rows}),'structural_checks_passed':not all_issues,'structural_issues':all_issues,
 'normal_agent_model_tokens':sum(r['model_usage']['total_token_count'] for r in rows),
 'metrics_from_original_evaluator':result['metrics'],
 'production_code_unchanged':all(Path(p).exists() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in metadata['code_sha256'].items()),
 'semantic_review_performed':False,
 'limits':['Actual injected requirements projection observed after standard request preparation; complete system_instruction strings not archived separately',
           'Forwarded native calls may still be rejected by original budget callbacks; they are not all necessarily executed or charged',
           'No automatic retries or protocol fixes applied; only one run of each selected task'],
 'tasks':rows}
(RUN/'state_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
for row in rows:
    lines=[f"# {row['task_id']}: technical State trace",'',f"Database: {row['database']}; termination: {row['termination']}",'',
           '| Response | Accepted | Revision | Requirements | Changed | Generated native tools |',
           '| --- | --- | --- | --- | --- | --- |']
    for t in row['timeline']:lines.append(f"| {t['response_index']} | {t['accepted']} | {t['revision']} | {t['requirements']} | {t['changed_requirements']} | {', '.join(t['generated_native_tools']) or '(text only)'} |")
    lines+=['',f"Structural audit issues: {json.dumps(row['structural_issues'],ensure_ascii=False)}",'',
            'No semantic assessment of requirements or values was performed.']
    for error in row['protocol_errors']:
        lines+=['',f"Protocol failure at response {error['response_index']}: {error['type']}",error['error'],'',
                f"Runtime revision retained: {error['expected_revision']} (not supplied by model)",'',
                '```text',error['raw_text'],'```']
    (RUN/('trace_'+row['task_id']+'.md')).write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['tasks','metrics_from_original_evaluator','limits']},ensure_ascii=False,indent=2))
