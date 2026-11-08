"""Requirement updates in assistant text alongside unchanged native tool calls.

No model invocations, tool declarations, argument adapters, or history rewrites.
"""

from __future__ import annotations

import json
import re

from google.genai import types

from system_agent.requirement_state import STATE_KEY, apply_update, empty_state

START = "<requirement_state_update>"
END = "</requirement_state_update>"
STATE_MARKER = "Current Requirement State (runtime validated):\n"
OPEN_BLOCK = re.compile(r'<requirement_state_update(?=[\s">])[^>]*>')
CLOSE_BLOCK = re.compile(r'</requirement_state_update\s*>')

STATE_INSTRUCTION = """REQUIREMENT STATE: use the original native tools normally, but
replace ordinary planning narration in assistant.content with a state update.
Your SAME assistant message must contain BOTH (1) the JSON text below and (2)
any native function calls you choose. Do not send a state-only preliminary turn.
Do not put state in tool arguments or encode actions as JSON. Do not omit the
text just because you are calling a tool. Do not write "I'll explore..." instead
of the required update.

Required assistant TEXT format (not function arguments):
<requirement_state_update>{"state_update":{"base_revision":0,"upserts":[{"id":"r1","requirement":"Result count","category":"user_semantics","status":"resolved","value":"10 (source: user)","priority":0}]}}</requirement_state_update>
This illustrates one item, NOT complete initialization. Use the current revision
and all relevant requirements for the actual question. A plain JSON object with
the same state_update field is also accepted. After initialization, upserts: []
is allowed for no change. Initialization must include all task constraints.

Each requirement: id (r1, r2, ...), requirement, category, status, value, priority.
Optional reason is audit-only. Reuse existing ids and requirement text; add new
ids only for genuinely new constraints. Preserve existing items; avoid duplicates.
Record ALL independent correctness constraints, including explicit ones: metrics
and formulas, filters/thresholds, schema/joins, grouping/aggregation, output
columns, sorting/limits, format and special operations such as CREATE VIEW.
Keep metric formulas separate from schema mappings; do not split every word.
For top 10 suspicious chains sorted by TCR descending, record count, suspicious
criteria, TCR formula and descending order separately, plus needed mappings.

category = schema | knowledge | user_semantics | unknown (source, not certainty).
status = unresolved | candidate | conflict | resolved. Priority is integer 1..3
for non-resolved and MUST be 0 exactly when resolved; it is advisory, not ordering.
Explicit user requirements are resolved/0 with their value and provenance.
Unclear requirements stay open. Value is a string; cite provenance inside it,
use & for multiple candidates, | for actual contradictory answers. No source field.
Compare evidence before changing an answer. Generic/name-similar KB definitions
remain candidate until applicability is confirmed; matching columns alone do not
confirm a definition explicitly described as generic. Never deduce an unspecified
filter definition from a requested sort order or top-N limit. Partial replies or errors
do not fill missing information. Actual contradiction reopens even a resolved
item as conflict, retaining both answers with | and nonzero priority. Only new
reliable evidence resolves it. Preserve explicit user constraints unless revised.

Read current State and tool/user evidence; in one response update State AND
choose your native action. Avoid repeating answered exploration. Before submit_sql
recheck every requirement against your SQL. No automatic SQL mapping or forced
priority order; original best-effort/budget rules still apply. Never infer hidden
ground truth. Invalid/missing state preserves old State and blocks that response's
tools without an extra model call. Include the update also in final text replies.
"""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON number: {value}")


def before_model_with_requirements(original_before):
    async def before_model_callback(callback_context, llm_request):
        stop = await original_before(callback_context, llm_request)
        if stop is not None:
            return stop
        state = callback_context.state
        task_id = state.get("task_id", "")
        current = state.get(STATE_KEY, empty_state(task_id))
        if not task_id or current["task_id"] != task_id:
            raise ValueError("Requirement State must belong to the current task")
        llm_request.append_instructions([
            STATE_INSTRUCTION,
            STATE_MARKER + json.dumps(current, ensure_ascii=False),
        ])
        return None
    return before_model_callback


async def after_model_callback(callback_context, llm_response):
    if llm_response.partial or llm_response.error_code:
        return None
    state = callback_context.state
    task_id = state.get("task_id", "")
    current = state.get(STATE_KEY, empty_state(task_id))
    text = "".join(p.text for p in (llm_response.content.parts if llm_response.content else []) or []
                   if p.text and not p.thought)
    error = ""
    changes = []
    try:
        if "<requirement_state_update" in text or "</requirement_state_update" in text:
            opening, closing = list(OPEN_BLOCK.finditer(text)), list(CLOSE_BLOCK.finditer(text))
            if len(opening) != 1 or len(closing) != 1:
                raise ValueError("expected exactly one requirement_state_update text block")
            begin = opening[0].end()
            finish = closing[0].start()
            if finish < begin:
                raise ValueError("invalid requirement_state_update block order")
            raw = text[begin:finish]
        else:
            raw = text
        payload = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if not isinstance(payload, dict) or set(payload) != {"state_update"}:
            raise ValueError("the block must contain only the state_update field")
        snapshot, changes = apply_update(current, payload["state_update"], task_id)
    except (ValueError, TypeError, KeyError) as exc:
        error = str(exc)
    else:
        state[STATE_KEY] = snapshot
    state["requirement_state_error"] = error
    history = list(state.get("requirement_state_history", []))
    history.append({
        "accepted": not error, "revision": current["revision"] if error else snapshot["revision"],
        "changes": changes, "error": error,
        "model_content": llm_response.content.model_dump(mode="json", exclude_none=True)
                         if llm_response.content else None,
        "usage": llm_response.usage_metadata.model_dump(mode="json", exclude_none=True)
                 if llm_response.usage_metadata else {},
    })
    state["requirement_state_history"] = history
    if error:
        return llm_response.model_copy(update={"content": types.Content(role="model", parts=[
            types.Part.from_text(text="Requirement State update rejected; no proposed tools executed. " + error)
        ])})
    return None  # Preserve original text, native calls, IDs, arguments and history.
