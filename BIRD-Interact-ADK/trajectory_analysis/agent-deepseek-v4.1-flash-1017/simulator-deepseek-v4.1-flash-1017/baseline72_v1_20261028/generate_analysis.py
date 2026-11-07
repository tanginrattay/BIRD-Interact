#!/usr/bin/env python3
"""离线读取已保存轨迹，验证 Markdown 与 JSON 一致性并生成第一轮分析。无网络/模型/数据库调用。"""
from pathlib import Path
from collections import Counter, defaultdict
import csv, difflib, hashlib, json, re, os
from annotations import NOTES, QA, LOC_CANDIDATES, PARTIAL, REFUSED

OUT=Path(__file__).resolve().parent
ROOT=next(parent for parent in OUT.parents if (parent/'results').is_dir())
SRC=ROOT/'results'/OUT.relative_to(ROOT/'trajectory_analysis')
BOOL=lambda v: 'TRUE' if v is True else 'FALSE' if v is False else 'UNKNOWN'
def compact(s,n=None):
    s=re.sub(r'\s+',' ',str(s)).strip()
    return s if n is None or len(s)<=n else s[:n]+'…'
def cell(s): return str(s).replace('|','\\|').replace('\n',' ')
def leaves(v):
    if isinstance(v,dict) and v:
        for x in v.values(): yield from leaves(x)
    elif isinstance(v,list) and v:
        for x in v: yield from leaves(x)
    else: yield v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)
def blocks(raw):
    lines=raw.splitlines(keepends=True);out=[];i=0
    while i<len(lines):
        m=re.fullmatch(r'(`{3,})(\w*)\n',lines[i])
        if not m: i+=1;continue
        marker=m.group(1);i+=1;buf=[]
        while i<len(lines) and lines[i].rstrip('\n')!=marker:
            buf.append(lines[i]);i+=1
        assert i<len(lines),'Unclosed fence'
        content=''.join(buf)
        assert content.endswith('\n')
        out.append(content[:-1]);i+=1
    return out

def errors(result):
    s=str(result).lower()
    if 'only select queries allowed' in s:return 'POLICY_READ_ONLY'
    if 'error' not in s:return None
    if 'violates foreign key' in s:return 'FOREIGN_KEY_CONSTRAINT'
    if 'division by zero' in s:return 'DIVISION_BY_ZERO'
    if 'already exists' in s:return 'OBJECT_ALREADY_EXISTS'
    if re.search(r'(column|relation).*does not exist',s):return 'MISSING_COLUMN_OR_RELATION'
    if 'function' in s and 'does not exist' in s:return 'FUNCTION_SIGNATURE_OR_TYPE'
    if 'syntax error' in s:return 'SYNTAX'
    return 'OTHER_EXECUTION_ERROR'
def phase_map(tools):
    phase='Priority';out=[]
    for x in tools:
        out.append(phase)
        if x['tool']=='submit_sql' and 'Phase 1 correct!' in str(x['result']): phase='Follow-up'
    return out

def main():
    (OUT/'task_cards').mkdir(exist_ok=True)
    result=json.loads((SRC/'eval_a_interact.json').read_text())['results']
    benchmark={t['instance_id']:t for t in map(json.loads,(SRC/'tasks.jsonl').read_text().splitlines())}
    ids=[t['task_id'] for t in result]
    paths=list((SRC/'markdown/tasks').glob('*.md'))
    assert len(ids)==len(set(ids))==len(paths)==72
    assert set(ids)==set(p.stem for p in paths)==set(benchmark)==set(NOTES)
    manifest=[];features=[];detail={};progress=[]
    all_tool=Counter();all_err=Counter();all_submit_err=Counter()
    for t in result:
        tid=t['task_id'];b=benchmark[tid];note=NOTES[tid];src=SRC/'markdown/tasks'/f'{tid}.md'
        raw=src.read_text();sha=hashlib.sha256(src.read_bytes()).hexdigest()
        expected=list(leaves(t))+list(leaves(b));actual=blocks(raw)
        assert actual==expected,(tid,'Markdown leaf mismatch',len(actual),len(expected))
        manifest.append(dict(task_id=tid,path=str(src.relative_to(ROOT)),sha256=sha,leaf_blocks=len(actual)))
        tools=t['tool_trajectory'];phases=phase_map(tools);counts=Counter(x['tool'] for x in tools);all_tool.update(counts)
        ask_indices=[i for i,x in enumerate(tools) if x['tool']=='ask_user'];assert len(ask_indices)==len(QA.get(tid,[]))
        agent_turns=sum(x['role']=='agent' for x in t['dialogue_history']);user_turns=sum(x['role']=='user' for x in t['dialogue_history'])
        reasons=[(i,p['text']) for i,e in enumerate(t['adk_events']) for p in (e.get('content') or {}).get('parts',[]) if p.get('type')=='text']
        # 原始 action-parser 类型未被写入这三种轨迹字段，不能复原为真值。
        seen={};repeats=[];knowledge_seen={};knowledge_repeats=[]
        for i,x in enumerate(tools):
            key=(x['tool'],json.dumps(x['args'],sort_keys=True,ensure_ascii=False))
            if key in seen:
                j=seen[key];repeats.append(dict(first=j,again=i,tool=x['tool'],same_phase=phases[j]==phases[i],same_result=tools[j]['result']==x['result']))
            else:seen[key]=i
            if x['tool']=='get_knowledge_definition':
                key=compact(x['args'].get('knowledge_name','')).casefold()
                if key in knowledge_seen:knowledge_repeats.append((knowledge_seen[key],i))
                else:knowledge_seen[key]=i
        execs=[i for i,x in enumerate(tools) if x['tool']=='execute_sql'];submits=[i for i,x in enumerate(tools) if x['tool']=='submit_sql']
        ee=[(i,errors(tools[i]['result'])) for i in execs if errors(tools[i]['result'])]
        se=[(i,errors(tools[i]['result'])) for i in submits if errors(tools[i]['result'])]
        all_err.update(k for i,k in ee);all_submit_err.update(k for i,k in se)
        empty=[i for i in execs if 'empty result set' in str(tools[i]['result']).lower()]
        corrections=[]
        eval_rejections=[(i,'EVALUATION_REJECTION') for i in submits if not errors(tools[i]['result']) and 'SQL failed Phase' in str(tools[i]['result'])]
        for i,kind in sorted(ee+se+eval_rejections):
            later=next((j for j in execs+submits if j>i and phases[j]==phases[i] and tools[j]['args'].get('sql')!=tools[i]['args'].get('sql')),None)
            # 最早的后续 SQL，而不是工具类别顺序。
            later=min([j for j in execs+submits if j>i and phases[j]==phases[i] and tools[j]['args'].get('sql')!=tools[i]['args'].get('sql')],default=None)
            if later is not None: corrections.append(dict(feedback=i,later=later,error_type=kind,later_error=errors(tools[later]['result'])))
        similarities=[]
        for a,z in zip(execs,execs[1:]):
            if phases[a]==phases[z]:
                ratio=difflib.SequenceMatcher(None,compact(tools[a]['args'].get('sql','')).lower(),compact(tools[z]['args'].get('sql','')).lower(),autojunk=False).ratio()
                if ratio>=.85:similarities.append(dict(first=a,again=z,text_similarity=round(ratio,3)))
        initial_match=re.search(r'budget of ([\d.]+) bird-coins',t['adk_events'][0].get('message',''))
        initial=float(initial_match.group(1)) if initial_match else None
        nominal=Counter();delta=Counter();ledger=[]
        for i,x in enumerate(tools):
            nominal[x['tool']]+=x.get('cost',0)
            before=x.get('budget_before');after=x.get('budget_after')
            if isinstance(before,(float,int)) and isinstance(after,(float,int)):
                if after>=0:delta[x['tool']]+=before-after
                if after<0 or abs((before-after)-x.get('cost',0))>1e-8:
                    ledger.append(dict(tool_index=i,budget_before=before,budget_after=after,nominal_cost=x.get('cost')))
        trunc_tools=[i for i,x in enumerate(tools) if '<truncated>' in str(x['result'])]
        trunc_events=[i for i,e in enumerate(t['adk_events']) if '<truncated>' in json.dumps(e,ensure_ascii=False)]
        # 检查工具调用/响应归档数；并行调用仅按原索引展示，不宣称有严格因果。
        function_calls=[p for e in t['adk_events'] for p in (e.get('content') or {}).get('parts',[]) if p.get('type')=='function_call']
        function_responses=[p for e in t['adk_events'] for p in (e.get('content') or {}).get('parts',[]) if p.get('type')=='function_response']
        call_match=Counter((p['name'],json.dumps(p.get('args',{}),sort_keys=True)) for p in function_calls)==Counter((x['tool'],json.dumps(x['args'],sort_keys=True)) for x in tools)
        unknown_calls=not call_match or len(function_responses)!=len(tools)
        complete='RECORDED_FIELDS_COMPLETE_WITH_TRUNCATED_PAYLOADS' if trunc_tools or trunc_events else 'RECORDED_FIELDS_COMPLETE'
        if unknown_calls:complete+=';CALL_RESPONSE_MISMATCH'
        recognized=bool(ask_indices) or any(re.search(r'ambigu|uncertain|unclear',s,re.I) for _,s in reasons)
        received=bool(set(ask_indices)-{i for task,i in REFUSED if task==tid})
        use='PARTIAL_OR_CHANGED' if tid in {'polar_M_4','vaccine_7'} else 'PARTIAL' if tid in {'mental_1','fake_1','gaming_7'} else 'OBSERVED' if ask_indices else 'NOT_APPLICABLE'
        p2_attempt=any(p=='Follow-up' for p in phases)
        outcome='两阶段均成功' if t['phase1_passed'] and t['phase2_passed'] else 'Priority 成功但 Follow-up 失败' if t['phase1_passed'] else 'Priority 阶段失败'
        failure_stage='NONE' if t['phase2_passed'] else 'FOLLOW_UP_NOT_ATTEMPTED' if t['phase1_passed'] and not p2_attempt else 'FOLLOW_UP' if t['phase1_passed'] else 'PRIORITY'
        feat={k:t.get(k) for k in ['task_id','database','phase1_passed','phase2_passed','has_follow_up','total_reward','elapsed_seconds','budget_used','budget_remaining']}
        for k in ['phase1_passed','phase2_passed','has_follow_up']:feat[k]=BOOL(feat[k])
        feat.update(budget_exhausted=BOOL(t['budget_remaining']<=0),dialogue_agent_turns=agent_turns,dialogue_user_turns=user_turns,ask_user_count=len(ask_indices),tool_call_count=len(tools))
        for name in ['get_schema','get_column_meaning','get_all_external_knowledge_names','get_knowledge_definition','execute_sql','submit_sql','get_all_knowledge_definitions','get_all_column_meanings']:feat[name+'_count']=counts[name]
        feat.update(repeated_identical_tool_call_count=len(repeats),repeated_knowledge_query_count=len(knowledge_repeats),ambiguity_recognized=BOOL(True if recognized else None),ask_user_used=BOOL(bool(ask_indices)),user_clarification_received=BOOL(received) if ask_indices else 'NOT_APPLICABLE',user_information_utilization=use,reasoning_action_gap_candidate='UNKNOWN',sql_executed=BOOL(bool(execs)),sql_execution_error_count=sum(k!='POLICY_READ_ONLY' for _,k in ee),sql_correction_candidate=BOOL(True if corrections else None),data_completeness=complete,manual_review_priority=note['priority'])
        feat.update(initial_budget=initial,follow_up_attempted=BOOL(p2_attempt),failure_stage=failure_stage,sql_policy_rejection_count=sum(k=='POLICY_READ_ONLY' for _,k in ee),sql_submit_execution_error_count=len(se),sql_empty_result_count=len(empty),similar_consecutive_execute_sql_pair_count=len(similarities),user_partial_reply_count=sum((tid,i) in PARTIAL for i in ask_indices),user_refusal_count=sum((tid,i) in REFUSED for i in ask_indices),simulator_action_classification='UNKNOWN',ambiguity_fully_resolved='UNKNOWN',nominal_tool_cost_sum=sum(nominal.values()),budget_ledger_anomaly_count=len(ledger),tool_payload_truncated_count=len(trunc_tools),adk_event_truncated_count=len(trunc_events),tool_calls_match_adk=BOOL(call_match))
        if feat['user_clarification_received']=='NOT_APPLICABLE':feat['user_clarification_received']='UNKNOWN'
        features.append(feat)
        rel=Path(os.path.relpath(src,OUT/'task_cards')).as_posix()
        def ref(i):return f'[T{i}]({rel}#tool_trajectory{i})'
        def refs(indices):return '、'.join(ref(i) for i in sorted(set(indices)))
        def aref(i):return f'[A{i}]({rel}#adk_events{i})'
        def errdesc(i):
            kind=errors(tools[i]['result'])
            if kind:return {'POLICY_READ_ONLY':'只读策略拒绝（非语法错）','FOREIGN_KEY_CONSTRAINT':'外键约束错误','DIVISION_BY_ZERO':'除零','OBJECT_ALREADY_EXISTS':'对象已存在','MISSING_COLUMN_OR_RELATION':'列或关系不存在','FUNCTION_SIGNATURE_OR_TYPE':'函数签名/类型不匹配','SYNTAX':'语法错误','OTHER_EXECUTION_ERROR':'其他执行错误'}[kind]
            s=str(tools[i]['result'])
            if 'Phase 1 correct!' in s:return 'Priority 通过，返回 Follow-up'
            if 'Phase 2 correct!' in s:return 'Follow-up 通过'
            if 'SQL failed Phase' in s:return '提交未通过；无具体执行错误'
            if 'empty result set' in s.lower():return '执行成功，空结果'
            return '返回数据（不等于评测通过）'
        follow='未进入 Follow-up' if not t['phase1_passed'] else '进入后无工具行动' if not p2_attempt else '有实际工具行动'
        lines=[f'# Task: {tid}',f'\n原始记录：[Markdown]({rel})。Tn/An/Dn 分别指 tool_trajectory/adk_events/dialogue_history 的零基索引。', '\n## 1. 任务概况','\n|项目|内容|','|---|---|']
        for k,v in [('Database',t['database']),('Phase 1 / Phase 2',f"{BOOL(t['phase1_passed'])} / {BOOL(t['phase2_passed'])}"),('Follow-up',f"{BOOL(t['has_follow_up'])}；{follow}"),('Reward / 耗时',f"{t['total_reward']} / {t['elapsed_seconds']:.1f}s"),('Budget',f"初始 {initial:g}；消耗 {t['budget_used']:g}；剩余 {t['budget_remaining']:g}"),('结果',outcome)]:lines.append(f'|{k}|{v}|')
        lines+=['\n## 2. Agent 行为概览',f'\n{note["story"]} 工具{len(tools)}次；对话{agent_turns}问/{user_turns}答（不含内部模型轮次）。', '\n## 3. 关键交互与决策','\n|事件/阶段|Agent 行为|结果或决策信息|证据位置|','|---|---|---|---|']
        important={0,*ask_indices,*[i for i,k in ee+se],*submits}
        # 重要过程保留首个试执行；大表返回不复制。
        if execs:important.add(execs[0])
        if len(important)>13:
            keep={0,*ask_indices,*[i for i,k in ee+se],submits[0],submits[-1]}
            keep.update(i for i in submits if 'correct!' in str(tools[i]['result']))
            important=keep
        qa_by_i=dict(zip(ask_indices,QA.get(tid,[])))
        dialogue_positions=[i for i,d in enumerate(t['dialogue_history']) if d['role']=='agent']
        ask_details=[]
        for i in sorted(important):
            x=tools[i];tool=x['tool']
            if tool=='ask_user':
                summary=qa_by_i[i]
                status='拒答' if (tid,i) in REFUSED else '部分回答' if (tid,i) in PARTIAL else '收到具体答复；正确性未确证'
                dpos=dialogue_positions[ask_indices.index(i)] if ask_indices.index(i)<len(dialogue_positions) else None
                evidence=ref(i)+(f' / [D{dpos}]({rel}#dialogue_history{dpos})' if dpos is not None else '')
                lines.append(f'|T{i} / {phases[i]}|ask_user|{cell(summary)}（{status}）|{evidence}|')
            else:
                desc=errdesc(i) if tool in ['execute_sql','submit_sql'] else '获取 Schema' if tool=='get_schema' else '返回已保存工具结果'
                lines.append(f'|T{i} / {phases[i]}|{tool}|{desc}|{ref(i)}|')
        for i in ask_indices:
            cls='UNKNOWN（拒答不等于可确认 UNA）' if (tid,i) in REFUSED else 'LOC 候选' if (tid,i) in LOC_CANDIDATES else 'AMB 候选'
            ask_details.append(dict(tool_index=i,phase=phases[i],summary=qa_by_i[i],simulator_action='UNKNOWN',analyst_candidate=cls,reply_status='REFUSED' if (tid,i) in REFUSED else 'PARTIAL' if (tid,i) in PARTIAL else 'SUBSTANTIVE_UNVERIFIED'))
        lines+=['\n## 4. 工具使用统计','\n|工具|调用次数|','|---|---:|']
        for name in ['get_schema','get_all_external_knowledge_names','get_column_meaning','get_all_column_meanings','get_knowledge_definition','get_all_knowledge_definitions','ask_user','execute_sql','submit_sql']:
            lines.append(f'|{name}|{counts[name]}|')
        seq=[]
        for x in tools:
            if seq and seq[-1][0]==x['tool']:seq[-1][1]+=1
            else:seq.append([x['tool'],1])
        if len(seq)<=16:order=' → '.join(f'{n}'+(f'×{c}' if c>1 else '') for n,c in seq)
        else:
            order=' → '.join(f'{n}'+(f'×{c}' if c>1 else '') for n,c in seq[:8])+' → … → '+' → '.join(f'{n}'+(f'×{c}' if c>1 else '') for n,c in seq[-4:])
        for tool_name,alias in [('get_all_external_knowledge_names','知识名列表'),('get_all_knowledge_definitions','全量知识'),('get_all_column_meanings','全量列义'),('get_knowledge_definition','知识定义'),('get_column_meaning','列义'),('get_schema','Schema')]:
            order=order.replace(tool_name,alias)
        lines.append('\n顺序：'+order+'。')
        if repeats:
            lines.append('\n完全同参重复（额外调用）'+str(len(repeats))+'次：'+'；'.join(f"{r['tool']} {ref(r['first'])}→{ref(r['again'])}（{'同' if r['same_phase'] else '跨'}阶段；结果{'相同' if r['same_result'] else '变化'}）" for r in repeats)+'。重复不自动等于浪费。')
        else:lines.append('\n完全同参重复0次。不同对象的多次查询不计为完全重复。')
        distinct=len(knowledge_seen)
        lines.append(f'知识单项查询：{counts["get_knowledge_definition"]}次、{distinct}个规范化名称、重复{len(knowledge_repeats)}次。'+('另有全量定义查询，与已读单项存在覆盖候选，不计同参重复。' if counts['get_all_knowledge_definitions'] and distinct else ''))
        lines+=['\n## 5. 关键行为特征']
        critical=[x['term'] for x in b.get('user_query_ambiguity',{}).get('critical_ambiguity',[])]
        hidden=[x['term']+'（is_mask='+BOOL(x.get('is_mask'))+'）' for x in b.get('knowledge_ambiguity',[])]
        lines.append('\n- **Ambiguity Handling：** 任务定义的关键表达：'+ '、'.join(critical)+'；知识歧义项：'+('、'.join(hidden) or '无单独 knowledge_ambiguity 条目')+'（benchmark任务中的研究者可见字段）。'+('可见主动提问；' if ask_indices else '未 ask_user；可见通过 Schema/知识/试执行自行解释；')+'全部歧义是否解决：UNKNOWN。')
        if ask_details:
            lines.append('- **询问类型与回复：** '+ '；'.join(f"{ref(q['tool_index'])} {q['analyst_candidate']}，{q['reply_status']}" for q in ask_details)+'。原始分类均 UNKNOWN；候选不计为真实标签。')
        lines.append(f'- **User Information Utilization：** {use}。{note["use"]}（{refs(note["use_refs"])}）。只证明局部采用，不保证完整忠实。')
        # 可见文本仅作为明确表达证据，不视作完整隐藏 reasoning。
        uncert=[(i,s) for i,s in reasons if re.search('ambig|uncertain|unclear',s,re.I)]
        rtext=f'可见不确定性表达于 {aref(uncert[0][0])}：“{compact(uncert[0][1],100)}”；' if uncert else '未找到可确认的不确定性措辞，不代表未感知歧义；'
        lines.append('- **Reasoning-Action Consistency：** '+rtext+'未暴露完整 reasoning；未确证工具计划落差，gap=UNKNOWN。'+('已有用户公式与后续表达式变化候选，见第6节；与工具计划落差分开。' if tid in {'polar_M_4','vaccine_7'} else ''))
        lines.append(f'- **Tool-use Behavior：** 表/列来源无法独立确证；知识利用见上文。相邻执行相似 SQL（文本相似度≥0.85）{len(similarities)}对'+('，见'+refs([i for pair in similarities for i in [pair['first'],pair['again']]]) if similarities else '')+'。')
        lines.append(f'- **SQL Generation & Correction：** 生成SQL={BOOL(bool(execs or submits))}；execute_sql {len(execs)}次：返回非错误结果 {len(execs)-len(ee)}次（其中明确空集{len(empty)}次），数据库执行错误{sum(k!="POLICY_READ_ONLY" for _,k in ee)}次、只读策略拒绝{sum(k=="POLICY_READ_ONLY" for _,k in ee)}次；提交时执行错误{len(se)}次。'+('错误类型：'+'；'.join(f'{ref(i)} {errdesc(i)}' for i,k in ee+se)+'。' if ee or se else '')+('反馈后出现不同SQL的修正候选：'+'；'.join(f"{ref(c['feedback'])}→{ref(c['later'])}" for c in corrections[:3])+'；不保证语义已纠正。' if corrections else '无已确证的错误/未通过反馈后改写。')+f' submit_sql 共{len(submits)}次。')
        top=nominal.most_common(3)
        lines.append(f'- **Budget Usage：** 初始{initial:g}，末余{t["budget_remaining"]:g}，原字段消耗{t["budget_used"]:g}，耗尽={BOOL(t["budget_remaining"]<=0)}。主要标称工具成本：'+ '、'.join(f'{n}={v:g}' for n,v in top)+f'（合计{sum(nominal.values()):g}，**不等于实际扣费或token费**）。'+('末次账面-1/成本差异见证据索引。' if ledger else '账面变化与标称成本一致。')+('同参同返仅为低信息增量候选。' if any(r['same_result'] and r['same_phase'] for r in repeats) else ''))
        lines+=['\n## 6. 值得关注的现象',f'\n**现象：** {note["finding"]}\n\n**证据：** {refs(note["refs"])}。\n\n**解释：** 可观察事实；与结果的因果关系未知。\n\n**判断置信度：** 事实高；因果解释未知。']
        if repeats:
            lines.append('\n**现象：** 存在完全同参重复，需结合阶段和返回变化审查。\n\n**证据：** '+refs([r['again'] for r in repeats])+'。\n\n**解释：** 相同参数不代表无新信息；跨阶段对象状态可能变化。\n\n**判断置信度：** 重复事实高；低效解释低。')
        if t['phase1_passed'] and not p2_attempt:
            lines.append('\n**现象：** Priority 通过后无 Follow-up 工具调用。\n\n**证据：** '+ref(submits[-1])+'、原始最终预算字段。\n\n**解释：** 未尝试与提交失败应分开统计；预算因果只作候选。\n\n**判断置信度：** 行为事实高；终止原因中。')
        lines+=['\n## 7. 待人工确认的问题']
        if note['priority']=='LOW':lines.append('\n- 已通过两阶段；若精读，核对 '+refs(note['use_refs'])+' 的局部公式采用是否覆盖全部澄清限制，当前不提出新增失败归因。')
        else:lines.append('\n- '+refs(note['refs'])+'：上述关键现象是否还涉及未澄清的范围/粒度或环境约束？请先核查这些事件。')
        lines.append('- 返回含裁剪（如 '+refs(trunc_tools[:1])+'）；关键上下文是否缺失？ADK对应位置见证据索引。' if trunc_tools or trunc_events else '- 完整 reasoning / action 标签未保存。')
        content='\n'.join(lines)+'\n'
        links={}
        def reference_link(m):
            label,url=m.groups()
            if re.fullmatch(r'[TAD]\d+',label):
                key=label.lower();links[key]=url;return f'[{label}][{key}]'
            return m.group(0)
        content=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',reference_link,content)
        content+='\n'+'\n'.join(f'[{k}]: {url}' for k,url in links.items())+'\n'
        (OUT/'task_cards'/f'{tid}.md').write_text(content)
        detail[tid]=dict(source=str(src.relative_to(ROOT)),source_sha256=sha,metadata_fields=list(t),ask_user=ask_details,repeated_identical_calls=repeats,repeated_knowledge_queries=knowledge_repeats,execute_sql_errors=[dict(tool_index=i,type=k) for i,k in ee],submit_sql_execution_errors=[dict(tool_index=i,type=k) for i,k in se],sql_empty_result_indices=empty,sql_correction_candidates=corrections,similar_execute_sql_pairs=similarities,phase_by_tool_index=phases,tool_result_truncated_indices=trunc_tools,adk_event_truncated_indices=trunc_events,nominal_cost_by_tool=dict(nominal),nonnegative_ledger_delta_by_tool=dict(delta),budget_ledger_anomalies=ledger,adk_function_call_count=len(function_calls),adk_function_response_count=len(function_responses),adk_calls_match_trajectory=call_match,dialogue_agent_positions=dialogue_positions,card_char_count=len(content))
        progress.append(dict(task_id=tid,status='COMPLETE',markdown_read=True,markdown_json_leaf_match=True,card=f'task_cards/{tid}.md',features_row=tid,source_sha256=sha))
    with (OUT/'task_features.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(features[0]));w.writeheader();w.writerows(features)
    (OUT/'evidence_index.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2)+'\n')
    (OUT/'progress.json').write_text(json.dumps(dict(discovered=len(paths),processed=len(progress),failed=0,tasks=progress),ensure_ascii=False,indent=2)+'\n')
    # 输出后复核原始 Markdown 未变化。
    assert all(hashlib.sha256((ROOT/p['path']).read_bytes()).hexdigest()==p['sha256'] for p in manifest)
    validation=dict(discovered_markdown_count=len(paths),processed_task_count=len(features),unique_task_count=len(set(ids)),benchmark_count=len(benchmark),unreadable_files=[],markdown_json_full_leaf_match_count=len(manifest),source_markdown_unchanged=True,source_manifest=manifest,tool_counts=dict(all_tool),execute_sql_error_types=dict(all_err),submit_sql_execution_error_types=dict(all_submit_err),cards_count=len(list((OUT/'task_cards').glob('*.md'))),csv_rows=len(features),source_json_sha256=hashlib.sha256((SRC/'eval_a_interact.json').read_bytes()).hexdigest(),source_benchmark_sha256=hashlib.sha256((SRC/'tasks.jsonl').read_bytes()).hexdigest())
    (OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k!='source_manifest'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
