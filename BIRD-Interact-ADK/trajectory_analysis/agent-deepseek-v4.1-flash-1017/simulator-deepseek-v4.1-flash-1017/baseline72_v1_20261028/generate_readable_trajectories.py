#!/usr/bin/env python3
"""把指定5条已保存ADK轨迹按原事件顺序展开；只读归档，不执行SQL或调用模型。"""
from pathlib import Path
import collections,hashlib,json,os,re
from trajectory_annotations import MODEL_TEXT,SQL_NOTES,INITIAL
from annotations import QA
from trajectory_sql_analysis import failure_analysis

OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'results').is_dir())
SRC=ROOT/'results'/OUT.relative_to(ROOT/'trajectory_analysis')
SELECTED=['polar_M_4','credit_11','disaster_3','virtual_1','cybermarket_1']
def fence(s,lang='text'):
    marker='`'*max(3,1+max((len(x) for x in re.findall(r'`+',str(s))),default=0))
    return f'{marker}{lang}\n{s}\n{marker}'
def details(title,body):return f'<details>\n<summary>{title}</summary>\n\n{body}\n\n</details>'
def brief(s):return re.sub(r'\s+',' ',str(s)).strip()
def display_unicode(s):return re.sub(r'\\u([0-9a-fA-F]{4})',lambda m:chr(int(m[1],16)),s)
def result_summary(tool,result):
    s=str(result)
    if tool=='get_schema':
        tables=re.findall(r'CREATE TABLE\s+"([^"\n]+)"',s)
        return '返回Schema和样例数据；当前保存片段可见表：'+('、'.join(tables) or '未能完整解析')+'。不据这个片段推断完整表数。'
    if tool in ['get_all_external_knowledge_names','get_all_knowledge_definitions','get_all_column_meanings']:
        return {'get_all_external_knowledge_names':'返回可用知识名称列表。','get_all_knowledge_definitions':'返回全量知识定义请求的已保存片段。','get_all_column_meanings':'返回全量列含义请求的已保存片段。'}[tool]
    if tool=='get_knowledge_definition':
        try:
            d=json.loads(s)
            return f"**{d.get('knowledge','知识定义')}**\n\n用途：{display_unicode(d.get('description','未记录'))}\n\n定义：\n\n{fence(display_unicode(d.get('definition','未记录')))}"
        except (ValueError,TypeError):return s
    if tool=='get_column_meaning':return s
    if tool=='submit_sql':return fence(s)
    if tool=='execute_sql':
        if 'SQL Error:' in s or 'empty result set' in s.lower():return fence(s)
        if len(s)<=850:return '返回：\n\n'+fence(s)
        lines=s.splitlines();preview='\n'.join(lines[:7]) if len(lines)>7 else s[:700]
        return '执行返回数据；以下仅展示阅读片段，不代表全部结果：\n\n'+fence(preview)+'\n\n其余已保存内容可在下方展开；不据片段计算总行数。'
    return s

def sql_statements(value):
    items=value if isinstance(value,list) else [value]
    assert items and all(isinstance(x,str) for x in items)
    return items

def main():
    target=OUT/'trajectory';target.mkdir(exist_ok=True)
    raw=(SRC/'eval_a_interact.json').read_bytes();all_results=json.loads(raw)['results'];records={t['task_id']:t for t in all_results};manifest=[]
    task_bytes=(SRC/'tasks.jsonl').read_bytes()
    benchmarks={t['instance_id']:t for t in map(json.loads,task_bytes.decode().splitlines())}
    for tid in SELECTED:
        t=records[tid];source=SRC/'markdown/tasks'/f'{tid}.md';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        rel=Path(os.path.relpath(source,target)).as_posix();links={'source':rel}
        benchmark=benchmarks[tid]
        links.update({'gt-priority':rel+'#sol_sql','gt-follow-up':rel+'#follow_up','gt-tests':rel+'#test_cases','gt-evaluator':Path(os.path.relpath(ROOT/'shared/db_utils.py',target)).as_posix()})
        def ref(kind,n):
            key=f'{kind.lower()}{n}';field={'T':'tool_trajectory','A':'adk_events','D':'dialogue_history'}[kind];links[key]=f'{rel}#{field}{n}';return f'[{kind}{n}][{key}]'
        tools=t['tool_trajectory'];events=t['adk_events'];matched=set();call_ids={};responded=[];model_seen=[];phase='Priority';event_sequence=[]
        ask_indices=[i for i,x in enumerate(tools) if x['tool']=='ask_user'];qa=dict(zip(ask_indices,QA[tid]))
        init_message=events[0]['message'];initial_budget=float(re.search(r'budget of ([\d.]+)',init_message)[1]);query=init_message.split('User Query:\n',1)[1].rsplit('\n\nYou have a budget',1)[0]
        lines=[f'# {tid}：按时间顺序展开的 Trajectory',f'\n[原始记录][source] · [Task Card](../task_cards/{tid}.md)',f'\n数据库：`{t["database"]}`；初始预算：**{initial_budget:g} bird-coins**。',
        '\n按原始 `adk_events` 数组顺序呈现，从初始问题到最后一次 `submit_sql`，并保留末尾终止文本。日志没有逐事件时间戳，因此序号表示归档事件顺序；同一模型事件内的多个调用属于同一批，不能理解为Agent先看到前一个工具的返回才决定后一个调用。',
        '\nTn = `tool_trajectory[n]`，An = `adk_events[n]`，均为零基索引。每次工具调用及返回均保留，中文说明便于阅读；公开说明原文、完整SQL与完整已保存问答可展开/查看。Schema、全量知识和长数据结果默认摘要，原始已保存字段放在折叠区。字段中的 `<truncated>` 是归档已发生的裁剪，不代表Agent实际输入也同样被裁剪；不填补缺失的隐藏reasoning。预算 `-1` 为终止标记，报告中的最终预算截为0。',
        f'\n## 00 · 初始问题（{ref("A",0)}）',f'\n**中文理解：** {INITIAL[tid]}',f'\n**Agent实际收到的问题：**\n\n{fence(query)}',details('完整初始任务消息',fence(init_message))]
        step=0
        for ai,e in enumerate(events[1:],1):
            parts=(e.get('content') or {}).get('parts',[])
            if not parts:
                step+=1;lines += [f'\n## {step:02d} · 记录事件（{ref("A",ai)}）',fence(json.dumps(e,ensure_ascii=False,indent=2))];event_sequence.append(ai);continue
            step+=1;event_sequence.append(ai)
            has_response=any(p.get('type')=='function_response' for p in parts)
            lines.append(f'\n## {step:02d} · {"工具返回" if has_response else "Agent公开说明与行动"} · {phase}（{ref("A",ai)}）')
            for part in parts:
                typ=part.get('type')
                if typ=='text':
                    assert ai in MODEL_TEXT[tid],(tid,ai,'missing Chinese narration')
                    model_seen.append(ai);lines += ['\n'+MODEL_TEXT[tid][ai],details('展开Agent公开文本原文',fence(part['text']))]
                elif typ=='function_call':
                    name=part['name'];args=part.get('args',{})
                    ti=next((i for i,x in enumerate(tools) if i not in matched and x['tool']==name and x['args']==args),None)
                    assert ti is not None,(tid,ai,name,args);matched.add(ti);call_ids[part['id']]=ti;x=tools[ti]
                    lines += [f'\n### 发起 {ref("T",ti)} · `{name}`',f'\n预算记录：{x["budget_before"]:g} → {x["budget_after"]:g}；标称成本 {x["cost"]:g}。该预算在调用前回调中处理，不与结果回复再重复扣费。']
                    if 'sql' in args:
                        lines += ['\n**这一步的SQL行为：** '+SQL_NOTES[tid][ti],details('展开完整SQL（原样）',fence(args['sql'],'sql'))]
                    elif name=='ask_user':
                        lines += ['\n**询问要点：** '+qa[ti],f'\n**完整提问：**\n\n{fence(args["question"])}']
                    else:lines += ['\n参数：\n\n'+fence(json.dumps(args,ensure_ascii=False,indent=2),'json')]
                elif typ=='function_response':
                    assert part['id'] in call_ids,(tid,ai,'unmatched response')
                    ti=call_ids[part['id']];responded.append(ti);x=tools[ti];tool=x['tool'];result=x['result']
                    lines.append(f'\n### {ref("T",ti)} · `{tool}` 的返回')
                    if tool=='ask_user':
                        lines += ['\n**问答中文摘要：** '+qa[ti],f'\n**User Simulator完整已保存回复：**\n\n{fence(result)}']
                    else:
                        lines.append('\n'+result_summary(tool,result))
                        if tool not in ['submit_sql','get_column_meaning'] and not (tool=='execute_sql' and len(str(result))<=850):lines.append(details('展开该工具完整已保存返回（可能已被原始日志裁剪）',fence(result)))
                    if '<truncated>' in str(result):lines.append('\n**记录完整性：** 该工具字段包含显式裁剪标记。')
                    if tool=='submit_sql' and 'Phase 1 correct!' in str(result):
                        lines.append('\n**阶段切换：** Priority通过；上面的返回文本给出Follow-up原题，之后使用同一笔剩余预算继续。');phase='Follow-up'
                    elif tool=='submit_sql' and 'Phase 2 correct!' in str(result):lines.append('\n**阶段结果：** Follow-up通过，任务结束。')
                    elif tool=='submit_sql':lines.append('\n**评测反馈：** 本次提交未通过；只有上方明确出现的错误可作为诊断，其余原因未知。')
                else:lines.append(fence(json.dumps(part,ensure_ascii=False,indent=2),'json'))
        assert matched==set(range(len(tools))) and sorted(responded)==list(range(len(tools))),(tid,'tool coverage')
        assert set(model_seen)==set(MODEL_TEXT[tid]),(tid,'model text coverage')
        assert event_sequence==list(range(1,len(events))),(tid,'event order')
        submits=[i for i,x in enumerate(tools) if x['tool']=='submit_sql']
        lines += ['\n## 原记录中的最终结果', '\n|字段|值|','|---|---|',f'|Priority通过|{t["phase1_passed"]}|',f'|Follow-up通过|{t["phase2_passed"]}|',f'|Reward|{t["total_reward"]}|',f'|预算消耗 / 最终剩余|{t["budget_used"]:g} / {t["budget_remaining"]:g}|',f'\n最后一次提交：{ref("T",submits[-1])}。最终公开回复：\n\n{fence(t["final_response"])}']
        lines += ['\n## Ground Truth SQL（研究者对照附录）', '\n以下原样摘自本批任务定义，不属于Agent当时收到的上下文，也不是Agent执行过的SQL。Priority与Follow-up分开列出；最后提交只能与它实际所在阶段比较。这里仅做静态对照，没有执行参考SQL或重新评分。', details('研究者可见的无歧义Priority问题（原文）',fence(benchmark['query'])), '\n### Priority Ground Truth', '\n来源：[原记录sol_sql][gt-priority]。']
        for sql in sql_statements(benchmark['sol_sql']):lines.append(fence(sql,'sql'))
        fu=benchmark.get('follow_up',{})
        if fu.get('sol_sql'):
            lines += ['\n### Follow-up Ground Truth', '\n来源：[原记录follow_up.sol_sql][gt-follow-up]。'+('本条Priority未通过，后续题未实际进入；以下仅供研究者参考，不作为最后Priority提交的比较目标。' if not t['phase1_passed'] else '本条确实进入Follow-up，最后一次提交对应本阶段。'), '\n后续题原文：\n\n'+fence(fu['query'])]
            for sql in sql_statements(fu['sol_sql']):lines.append(fence(sql,'sql'))
        if not t['phase1_passed'] or (fu.get('sol_sql') and not t['phase2_passed']):
            lines += ['\n## 最后提交与Ground Truth的差异及失败分析','\n'+failure_analysis(tid,ref)]
        else:
            lines += ['\n### 评测状态说明', '\n本条Priority与Follow-up均已通过，故不作失败归因。'+('Agent使用直接JOIN而GT使用CTE，且普通结果别名不同；这些文本差异不等于结果错误。' if tid=='cybermarket_1' else 'Agent未显式ROUND礼物分数而GT保留2位；默认评测会移除ROUND，不应把已通过的任务改判为失败。')]
        lines.append('\n'+'\n'.join(f'[{key}]: {value}' for key,value in links.items()))
        rendered='\n'.join(lines)+'\n'
        for x in tools:
            for k in ['sql','question']:
                if k in x['args']:assert x['args'][k] in rendered,(tid,k,'content missing')
            if x['tool']=='ask_user':assert str(x['result']) in rendered
        (target/f'{tid}.md').write_text(rendered)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
        manifest.append(dict(task_id=tid,source_markdown=str(source.relative_to(ROOT)),source_sha256=source_hash,output=f'trajectory/{tid}.md',adk_event_count=len(events),adk_events_in_order=[0]+event_sequence,tool_call_count=len(tools),tool_indices_included=sorted(matched),tool_response_indices_included=responded,public_text_event_indices=model_seen,last_submit_index=submits[-1],all_sql_and_questions_preserved=True,full_saved_clarification_answers_preserved=True,ground_truth_priority_statement_count=len(sql_statements(benchmark['sol_sql'])),ground_truth_follow_up_statement_count=len(sql_statements(fu['sol_sql'])) if fu.get('sol_sql') else 0,ground_truth_appended_before_reference_definitions=True,final_submit_compared_to_phase='Priority' if not t['phase1_passed'] else 'Follow-up',failure_analysis_included=not t['phase1_passed'] or (bool(fu.get('sol_sql')) and not t['phase2_passed'])))
    assert hashlib.sha256((SRC/'eval_a_interact.json').read_bytes()).digest()==hashlib.sha256(raw).digest()
    assert (SRC/'tasks.jsonl').read_bytes()==task_bytes
    (OUT/'trajectory_manifest.json').write_text(json.dumps({'tasks':manifest,'processed':len(manifest),'source_json_sha256':hashlib.sha256(raw).hexdigest(),'source_tasks_sha256':hashlib.sha256(task_bytes).hexdigest()},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{'task_id':x['task_id'],'ADK_events':x['adk_event_count'],'tool_calls':x['tool_call_count'],'last_submit':x['last_submit_index']} for x in manifest],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
