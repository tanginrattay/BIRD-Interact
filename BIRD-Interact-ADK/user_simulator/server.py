"""User Simulator Service (Port 6001), with selectable simulation protocol."""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, HTTPException

from shared.config import settings
from shared.models import AskUserRequest, AskUserResponse, InitTaskRequest, PhaseTransitionRequest
from user_simulator.prompts import USER_SIMULATOR_ACTION_PARSER, USER_SIMULATOR_RESPONSE_GENERATOR
from user_simulator.sql_parser import segment_sql
from user_simulator.bailian import call_bailian, is_qwen_simulator

logger = logging.getLogger(__name__)
app = FastAPI(title="BIRD-Interact User Simulator", version="1.0.0")

PROMPT_VERSION = settings.prompt_version  # v1=legacy, v2=recommended


class TaskSimState:
    def __init__(self, task_data: Dict[str, Any]):
        self.task_data = task_data
        self.db_name = task_data["selected_database"]
        self.amb_user_query = task_data["amb_user_query"]
        self.clear_query = task_data.get("query", task_data["amb_user_query"])
        self.reference_sql = task_data["sol_sql"]
        self.user_query_ambiguity = task_data.get("user_query_ambiguity", {})
        self.knowledge_ambiguity = task_data.get("knowledge_ambiguity", [])
        self.current_phase = 1
        self.db_schema = ""
        fu = task_data.get("follow_up") or {}
        self.follow_up_sol_sql = fu.get("sol_sql") if fu else None

    def get_sql_segments(self, sql: str) -> str:
        segs = segment_sql(sql)
        return "\n\n".join(f"{clause}:\n{text}" for clause, text in segs)

    def get_all_sql_segments(self) -> str:
        sql_list = self.reference_sql if isinstance(self.reference_sql, list) else [self.reference_sql]
        return "\n===\n".join(self.get_sql_segments(sql) for sql in sql_list)

    def get_ambiguity_json(self) -> str:
        if self.current_phase == 1:
            return ("user_query_ambiguity: \n"
                    + json.dumps(self.user_query_ambiguity, indent=4)
                    + "\n\nknowledge_ambiguity: \n"
                    + json.dumps(self.knowledge_ambiguity, indent=4))
        return json.dumps({}, indent=4)

    def get_gt_sql_str(self) -> str:
        if isinstance(self.reference_sql, list):
            return "\n".join(self.reference_sql)
        return self.reference_sql

    def transition_to_phase2(self):
        self.current_phase = 2
        if self.follow_up_sol_sql:
            self.reference_sql = self.follow_up_sol_sql


_task_states: Dict[str, TaskSimState] = {}


def _call_llm(prompt: str, max_tokens: int = 200,
              reasoning_effort: str = None, system_prompt: str = None) -> str:
    kwargs = {"model_name": settings.user_sim_model, "temperature": 0,
              "max_tokens": max_tokens}
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    if is_qwen_simulator(settings.user_sim_model):
        content = call_bailian(messages, max_tokens=max_tokens)
    else:
        from shared.llm import call_llm
        content = call_llm(messages, **kwargs)
    if not content or not content.strip():
        raise ValueError("User simulator model returned an empty response")
    return content.strip()


def _extract_output(content: str) -> str:
    """Accept the prompt's <s> format and plain text from chat models."""
    match = re.search(r"<s>(.*?)(?:</s>|$)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    if "</s>" in content:
        content = content.split("</s>", 1)[0]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    content = re.sub(r"^(?:-\s*)?(?:Action|Response):\s*", "", content.strip(), flags=re.I)
    return content.strip().strip("`").strip()


def _parse_action(state: TaskSimState, question: str, dialogue_history: List[Dict[str, str]] = None) -> str:
    """Stage 1: Action Parser — maps clarification question to action (AMB/LOC/UNA)."""
    template = USER_SIMULATOR_ACTION_PARSER[PROMPT_VERSION]
    prompt = template.replace("[[clarification_Q]]", question)
    prompt = prompt.replace("[[amb_json]]", state.get_ambiguity_json())
    prompt = prompt.replace("[[SQL_Glot]]", state.get_all_sql_segments())
    prompt = prompt.replace("[[DB_schema]]", state.db_schema)
    if dialogue_history:
        prompt += "\n\nPrevious clarification dialogue:\n" + json.dumps(dialogue_history, ensure_ascii=False)
    # v2 includes <think> reasoning, needs more tokens
    max_tok = 500 if PROMPT_VERSION == "v2" else 200
    content = _call_llm(prompt, max_tokens=max_tok)
    # Extract action from <s>...</s> (skip <think>...</think> if present)
    action = _extract_output(content)
    action_match = re.search(r"(labeled\([^\n]*?\)|unlabeled\([^\n]*?\)|unanswerable\(\))", action)
    if not action_match:
        raise ValueError(f"User simulator returned an invalid action: {action[:200]!r}")
    action = action_match.group(1)
    logger.info(f"Parsed action: {action}")
    return action


def _generate_response(state: TaskSimState, question: str, action: str,
                       dialogue_history: List[Dict[str, str]] = None) -> str:
    """Stage 2: Response Generator — produces user response from action + context."""
    template = USER_SIMULATOR_RESPONSE_GENERATOR[PROMPT_VERSION]
    prompt = template.replace("[[clarification_Q]]", question)
    prompt = prompt.replace("[[Action]]", action)
    prompt = prompt.replace("[[clear_query]]", state.clear_query)
    prompt = prompt.replace("[[amb_json]]", state.get_ambiguity_json())
    prompt = prompt.replace("[[GT_SQL]]", state.get_gt_sql_str())
    prompt = prompt.replace("[[SQL_Glot]]", state.get_all_sql_segments())
    prompt = prompt.replace("[[DB_schema]]", state.db_schema)
    if dialogue_history:
        prompt += "\n\nPrevious clarification dialogue:\n" + json.dumps(dialogue_history, ensure_ascii=False)
    content = _call_llm(prompt, max_tokens=1024)
    response = _extract_output(content)
    if not response:
        raise ValueError("User simulator returned an empty answer")
    return response


@app.post("/init_task")
async def init_task(req: InitTaskRequest):
    state = TaskSimState(req.task_data)
    _task_states[req.task_id] = state
    # Load schema from DB env
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            resp = await client.post(
                f"http://localhost:{settings.db_env_port}/schema",
                json={"task_id": req.task_id})
            state.db_schema = resp.json().get("schema", "")
    except Exception as e:
        logger.warning(f"Could not load schema: {e}")
    return {"status": "ok", "task_id": req.task_id}


def _ask_sync(state: "TaskSimState", question: str,
              dialogue_history: List[Dict[str, str]] = None) -> str:
    """Choose the protocol independently of the transport. Runs in thread pool."""
    if settings.user_sim_pipeline == "single_stage" or (
        settings.user_sim_pipeline == "auto" and (
            settings.user_sim_model.startswith("moonshot/kimi-")
            or is_qwen_simulator(settings.user_sim_model)
        )
    ):
        return _ask_direct(state, question, dialogue_history)
    action = _parse_action(state, question, dialogue_history)
    return _generate_response(state, question, action, dialogue_history)


def _ask_direct(state: TaskSimState, question: str,
              dialogue_history: List[Dict[str, str]] = None) -> str:
    """Shared single-stage protocol, preserving the existing calibrated prompt."""
    instructions = (
        "You are the user who wrote the original request. Answer the collaborator's "
        "clarification question directly and briefly. The original clear request and "
        "reference SQL define your intent. The ambiguous request, the collaborator's "
        "question, and earlier dialogue may contain WRONG assumptions; they do not "
        "override that intent. Correct any false premise relevant to the question "
        "before answering it, including the grouping object, metric, population, or "
        "threshold. If offered choices are all wrong or partly wrong, reject or qualify "
        "them instead of agreeing. Correct earlier mistaken user replies when needed. "
        "Answer each requested clarification, but do not volunteer unrelated details "
        "or reproduce the full original request. Use ordinary language and conceptual "
        "metric names; never quote SQL expressions, table aliases, schema identifiers, "
        "internal annotations, or reasoning. Refuse requests for SQL or implementation "
        "details. If the private information does not determine an answer, say so; "
        "if its sources conflict, acknowledge the conflict rather than inventing a "
        "definite answer. Never mention private context, original/ambiguous versions, "
        "or knowledge IDs. Do not put schema names in parentheses or explain which "
        "fields implement a concept. Do not add thresholds or formulas unless asked. "
        "For requests for reference SQL, table names, column names or implementation "
        "details, reply ONLY: 'Sorry, I can clarify my requirements, but cannot provide "
        "SQL or database implementation details.' Do not append requirements or hints."
    )
    prompt = (
        f"Task ID: {state.task_data.get('instance_id', '')}\n"
        f"Original request: {state.clear_query}\n"
        f"Ambiguous request: {state.amb_user_query}\n"
        f"Ambiguity annotations: {state.get_ambiguity_json()}\n"
        f"Ground truth SQL: {state.get_gt_sql_str()}\n"
        f"Previous clarification dialogue: {json.dumps(dialogue_history or [], ensure_ascii=False)}\n"
        f"Clarification question: {question}\n"
        "Your concise answer:"
    )
    effort = "none" if settings.user_sim_model.startswith("moonshot/kimi-") else None
    content = _call_llm(prompt, max_tokens=1024, reasoning_effort=effort,
                        system_prompt=instructions)
    answer = _extract_output(content)
    if not answer:
        raise ValueError("User simulator returned an empty answer")
    return answer


@app.post("/ask", response_model=AskUserResponse)
async def ask_user(req: AskUserRequest):
    state = _task_states.get(req.task_id)
    if not state:
        raise HTTPException(404, f"Task {req.task_id} not initialized")
    response = await asyncio.to_thread(_ask_sync, state, req.question, req.dialogue_history)
    logger.info(f"User response for {req.task_id}: {response[:100]}...")
    return AskUserResponse(answer=response)


@app.post("/phase_transition")
async def phase_transition(req: PhaseTransitionRequest):
    state = _task_states.get(req.task_id)
    if not state:
        raise HTTPException(404, f"Task {req.task_id} not initialized")
    state.transition_to_phase2()
    return {"status": "ok", "phase": 2}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user_simulator"}


@app.get("/debug_state/{task_id}")
async def debug_state(task_id: str):
    state = _task_states.get(task_id)
    if not state:
        return {"error": "not found"}
    return {
        "db_name": state.db_name,
        "schema_len": len(state.db_schema),
        "schema_first_100": state.db_schema[:100],
        "current_phase": state.current_phase,
        "amb_query": state.amb_user_query[:100],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.user_sim_port)
