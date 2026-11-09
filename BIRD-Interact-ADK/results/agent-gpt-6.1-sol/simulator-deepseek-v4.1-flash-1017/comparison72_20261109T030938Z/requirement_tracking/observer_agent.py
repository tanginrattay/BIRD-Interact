import litellm
litellm.drop_params = True
"""Read-only callback/session observation for this eight-task run only."""
import copy
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, os.environ["EVAL_PROJECT_ROOT"])
RUN = Path(os.environ["EVAL_RUN_DIRECTORY"])
import system_agent.requirement_tracking as tracking

def emit(kind, **fields):
    record = {"type": kind, "at_utc": datetime.now(timezone.utc).isoformat(), **fields}
    with (RUN / "state_observations.jsonl").open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        f.flush()

def calls(content):
    return [{"name": p.function_call.name, "id": p.function_call.id, "args": p.function_call.args}
            for p in (content.parts if content else []) or [] if p.function_call]

original_factory = tracking.before_model_with_requirements
original_after = tracking.after_model_callback

def observing_factory(original_before):
    callback = original_factory(original_before)
    async def before_model_callback(callback_context, llm_request):
        result = await callback(callback_context, llm_request)
        state = callback_context.state
        emit("model_request" if result is None else "before_model_stop",
             task_id=state.get("task_id"), session_id=callback_context.session.id,
             invocation_id=callback_context.invocation_id,
             state=copy.deepcopy(state.get("requirement_state")),
             injected_state=json.loads(llm_request.config.system_instruction.rsplit(tracking.STATE_MARKER,1)[1]) if result is None else None,
             history_length=len(state.get("requirement_state_history", [])),
             native_tools=bool(llm_request.config.tools),
             response_schema=str(llm_request.config.response_schema) if llm_request.config.response_schema else None,
             tool_config=llm_request.config.tool_config.model_dump(mode="json", exclude_none=True) if llm_request.config.tool_config else None,
             input_native_calls=[c for content in llm_request.contents for c in calls(content)],
             input_native_results=[{"id": p.function_response.id, "name": p.function_response.name}
                 for content in llm_request.contents for p in content.parts or [] if p.function_response],
             stop_text=[p.text for p in (result.content.parts if result and result.content else []) or [] if p.text])
        return result
    return before_model_callback

async def after_model_callback(callback_context, llm_response):
    before = copy.deepcopy(callback_context.state.get("requirement_state"))
    original_content = llm_response.content.model_dump(mode="json", exclude_none=True) if llm_response.content else None
    generated = calls(llm_response.content)
    result = await original_after(callback_context, llm_response)
    state = callback_context.state
    emit("model_response", task_id=state.get("task_id"), session_id=callback_context.session.id,
         invocation_id=callback_context.invocation_id, partial=llm_response.partial,
         upstream_error=llm_response.error_code,
         state_before=before, state_after=copy.deepcopy(state.get("requirement_state")),
         state_error=state.get("requirement_state_error"), history_length=len(state.get("requirement_state_history", [])),
         generated_native_calls=generated,
         forwarded_native_calls=calls(result.content if result is not None else llm_response.content),
         original_response_unchanged=original_content == (llm_response.content.model_dump(mode="json", exclude_none=True) if llm_response.content else None),
         callback_returned_none=result is None,
         usage=llm_response.usage_metadata.model_dump(mode="json", exclude_none=True) if llm_response.usage_metadata else {})
    return result

tracking.before_model_with_requirements = observing_factory
tracking.after_model_callback = after_model_callback
from system_agent import server
original_turn = server.runtime.run_turn

async def observed_turn(task_id, mode, message, **kwargs):
    result = None
    error = None
    try:
        result = await original_turn(task_id=task_id, mode=mode, message=message, **kwargs)
        return result
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        ref = server.runtime._session_refs.get((mode, task_id))
        if ref:
            runner, _ = await server.runtime._get_runner(mode)
            session = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
            snapshot = {"task_id": task_id, "session_id": ref.session_id, "runtime_error": error,
                        "returned_state_matches_saved_requirement_state": None if result is None else
                        result["state"].get("requirement_state") == session.state.get("requirement_state"),
                        "session": session.model_dump(mode="json", exclude_none=True)}
            (RUN / "sessions" / (task_id + ".json")).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
            emit("session_saved", task_id=task_id, session_id=ref.session_id,
                 runtime_error=error, saved_requirement_state=session.state.get("requirement_state"),
                 returned_state_matches_saved=snapshot["returned_state_matches_saved_requirement_state"])
server.runtime.run_turn = observed_turn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(server.app, host="127.0.0.1", port=16000, log_level="info")
