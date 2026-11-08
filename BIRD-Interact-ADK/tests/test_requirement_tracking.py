"""Native function-calling State smoke: real ADK, controlled model/HTTP."""

import copy
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from system_agent.adk_runtime import AdkRuntime
from system_agent.requirement_state import apply_update, empty_state
from system_agent.requirement_tracking import (
    START, END, STATE_MARKER, before_model_with_requirements, after_model_callback,
)

QUERY = "Find the top 10 suspicious chains ordered by TCR descending. Return chain_id and TCR."

SCHEMA = "CREATE TABLE chains(chain_id integer, total numeric, capacity numeric);"

SQL = "SELECT chain_id, total/NULLIF(capacity,0) AS tcr FROM chains WHERE total/NULLIF(capacity,0)>0.8 ORDER BY tcr DESC LIMIT 10"

def row(i, text, category="user_semantics", status="unresolved", value="", priority=3):
    return dict(id=f"r{i}", requirement=text, category=category, status=status,
                value=value, priority=priority, reason="Compared visible evidence with the previous answer.")

INITIAL = [
    row(1, "Return 10 chains", status="resolved", value="10 (source: user)", priority=0),
    row(2, "Define suspicious chains"),
    row(3, "Determine TCR formula", "knowledge"),
    row(4, "Sort by TCR descending", status="resolved", value="TCR DESC (source: user)", priority=0),
    row(5, "Map chain identifiers and formula inputs", "schema"),
    row(6, "Return chain_id and TCR columns", status="resolved", value="chain_id, TCR (source: user)", priority=0),
]

SCHEMA_UPDATE = row(5, INITIAL[4]["requirement"], "schema", "resolved",
                    "chains(chain_id,total,capacity), no joins (source: get_schema)", 0)

KB_UPDATE = row(3, INITIAL[2]["requirement"], "knowledge", "candidate",
                "TCR = total/capacity; applicability unconfirmed (source: KB)", 3)

PARTIAL_UPDATE = row(2, INITIAL[1]["requirement"], "user_semantics", "candidate",
                     "TCR above an unspecified threshold (source: user)", 3)

FINAL_UPDATES = [
    row(2, INITIAL[1]["requirement"], "user_semantics", "resolved", "TCR > 0.8 (source: user)", 0),
    row(3, INITIAL[2]["requirement"], "user_semantics", "resolved",
        "TCR = total/NULLIF(capacity,0); user confirms KB applicability (source: user & KB)", 0),
    row(7, "Exclude zero capacity", "user_semantics", "resolved", "capacity <> 0 (source: user)", 0),
]

class FakeClient:
    calls = []
    asks = 0
    observer = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def post(self, url, json):
        type(self).calls.append({"url": url, "payload": json})
        if type(self).observer:
            type(self).observer()
        if url.endswith("/schema"):
            data = {"schema": SCHEMA}
        elif url.endswith("/knowledge"):
            data = {"knowledge": "TCR = total/capacity (generic definition; confirm task applicability)."}
        elif url.endswith("/knowledge_names"):
            data = {"names": ["TCR"]}
        elif url.endswith("/ask"):
            type(self).asks += 1
            data = {"answer": "Suspicious means TCR above a threshold." if self.asks == 1 else
                    "Use TCR > 0.8. TCR means total/capacity here; exclude zero capacity."}
        elif url.endswith("/execute"):
            data = {"success": True, "result": "chain_id | tcr\n1 | 0.9"}
        elif url.endswith("/submit"):
            data = {"passed": False, "message": "Fixture received SQL; no database evaluation performed."}
        else:
            raise AssertionError(url)
        return type("Response", (), {"status_code": 200, "json": lambda self: data})()

class ValidationTests(unittest.TestCase):
    def test_revision_is_runtime_owned_and_changes_only_with_data(self):
        state, _ = apply_update(empty_state("a"), {"upserts": INITIAL}, "a")
        self.assertEqual(state["revision"], 1)
        state, audit = apply_update(state, {"upserts": []}, "a")
        self.assertEqual(state["revision"], 1)
        self.assertEqual(audit, [])
        state, _ = apply_update(state, {"upserts": [KB_UPDATE]}, "a")
        self.assertEqual(state["revision"], 2)
        unchanged, audit = apply_update(state, {"upserts": [KB_UPDATE]}, "a")
        self.assertEqual(unchanged, state)
        self.assertEqual(audit, [])
        before = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            apply_update(state, {"upserts": [{**KB_UPDATE, "priority": 0}]}, "a")
        self.assertEqual(state, before)
        # Neither version field belongs to the model's update schema anymore.
        for key in ["base_revision", "revision"]:
            with self.assertRaises(ValueError):
                apply_update(state, {"upserts": [], key: 999}, "a")

    def test_optional_audit_reason_keeps_exact_requirement_fields(self):
        patch_rows = [{k: v for k, v in r.items() if k != "reason"} for r in INITIAL]
        state, audit = apply_update(empty_state("a"), {"upserts": patch_rows}, "a")
        self.assertEqual(set(state["requirements"][0]),
                         {"id", "requirement", "category", "status", "value", "priority"})
        self.assertEqual(audit[0]["reason"], "")

    def test_atomic_validation_and_conflict_reopening(self):
        state, _ = apply_update(empty_state("a"), {"upserts": INITIAL}, "a")
        before = copy.deepcopy(state)
        invalids = [
            {"revision": 0, "upserts": []},
            {"upserts": [{**KB_UPDATE, "category": "invalid"}]},
            {"upserts": [{**KB_UPDATE, "status": "resolved", "priority": 3}]},
            {"upserts": [{**KB_UPDATE, "priority": True}]},
            {"upserts": [{**KB_UPDATE, "source": "KB"}]},
            {"upserts": [{**KB_UPDATE, "id": "r7", "requirement": INITIAL[0]["requirement"]}]},
            {"upserts": [KB_UPDATE, KB_UPDATE]},
            {"upserts": [{**KB_UPDATE, "requirement": "rename"}]},
        ]
        for payload in invalids:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                apply_update(state, payload, "a")
            self.assertEqual(state, before)
        with self.assertRaises(ValueError):
            apply_update(state, {"upserts": []}, "another-task")
        for change in [KB_UPDATE, FINAL_UPDATES[1],
                       {**KB_UPDATE, "status": "conflict", "value": "formula A (source: KB) | formula B (source: user)"},
                       {**FINAL_UPDATES[1], "value": "formula B; user explicitly rejects A (source: user)"}, FINAL_UPDATES[2]]:
            state, _ = apply_update(state, {"upserts": [change]}, "a")
        self.assertEqual(len(state["requirements"]), 7)
        self.assertEqual(state["requirements"][0], before["requirements"][0])


def update_text(rows):
    return START + json.dumps({"state_update": {"upserts": rows}}) + END


class ScriptModel(BaseLlm):
    model: str = "native-requirement-smoke"
    _steps: list = PrivateAttr(default_factory=list)
    _requests: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        snapshot = json.loads(llm_request.config.system_instruction.rsplit(STATE_MARKER, 1)[1])
        assert llm_request.config.tools
        assert llm_request.config.tool_config is None
        assert llm_request.config.response_schema is None
        assert llm_request.config.response_mime_type is None
        self._requests.append({"state": snapshot, "tools": list(llm_request.tools_dict),
                               "contents": [c.model_dump(mode="json", exclude_none=True) for c in llm_request.contents]})
        assert self._steps, "unexpected extra model call"
        step = self._steps.pop(0)
        if isinstance(step, dict):
            text, calls = step["raw_text"], step.get("calls", [])
        else:
            rows, action = step
            text = update_text(rows)
            calls = [] if isinstance(action, str) else (action if isinstance(action, list) else [action])
            if isinstance(action, str):
                text += "\n" + action
        parts = [types.Part.from_text(text=text)]
        parts.extend(types.Part(function_call=types.FunctionCall(
            id=f"call_model_{len(self._requests)}_{i}", name=name, args=args,
        )) for i, (name, args) in enumerate(calls))
        yield LlmResponse(content=types.Content(role="model", parts=parts))


class CallbackContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_or_missing_state_preserves_entire_native_response(self):
        current, _ = apply_update(empty_state("test"), {"upserts": INITIAL}, "test")
        for text in ["No State supplied", START + "invalid JSON" + END,
                     update_text([{**KB_UPDATE, "priority": 0}])]:
            state = {"task_id": "test", "requirement_state": copy.deepcopy(current)}
            response = LlmResponse(content=types.Content(role="model", parts=[
                types.Part.from_text(text=text),
                types.Part(function_call=types.FunctionCall(id="call_provider_1", name="submit_sql", args={"sql": SQL})),
            ]))
            before = response.model_dump()
            self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), response))
            self.assertEqual(response.model_dump(), before)
            self.assertEqual(state["requirement_state"], current)
            self.assertTrue(state["requirement_state_error"])
            self.assertFalse(state["requirement_state_history"][-1]["accepted"])

    async def test_plain_json_and_decorated_marker_keep_strict_state_validation(self):
        payload = json.dumps({"state_update": {"upserts": INITIAL}})
        for text in [payload, '<requirement_state_update" >' + payload + END]:
            state = {"task_id": "test", "requirement_state": empty_state("test")}
            response = LlmResponse(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))
            self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), response))
            self.assertEqual(state["requirement_state"]["revision"], 1)

    async def test_outer_text_recovery_keeps_native_calls(self):
        rows = copy.deepcopy(INITIAL)
        rows[0]["value"] = '10; literal braces { } and quote " (source: user)'
        payload = json.dumps({"state_update": {"upserts": rows}})
        cases = [payload + END, START + payload, "broken marker>" + payload,
                 "Plan:\n```json\n" + payload + "\n```\nNext action.",
                 START + payload + "</｜｜DSML｜｜ parameter>\n</｜｜DSML｜｜ invoke>",
                 '{"unrelated": true}\n' + payload,
                 "</requirement_state_update>" + payload + "<requirement_state_update>"]
        for text in cases:
            with self.subTest(text=text):
                state = {"task_id": "test", "requirement_state": empty_state("test")}
                response = LlmResponse(content=types.Content(role="model", parts=[
                    types.Part.from_text(text=text), types.Part(function_call=types.FunctionCall(
                        id="native", name="get_schema", args={}))]))
                original = response.model_dump()
                self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), response))
                self.assertEqual(response.model_dump(), original)
                self.assertEqual(state["requirement_state_error"], "")
                self.assertEqual(state["requirement_state"]["requirements"][0]["value"], rows[0]["value"])

    async def test_recovery_never_relaxes_inner_json_or_schema(self):
        valid = json.dumps({"state_update": {"upserts": INITIAL}})
        invalid = [valid[:-1], valid[:-1] + ",}", valid.replace('"state_update"', "'state_update'"),
                   '{"state_update":{"upserts":[],"upserts":[]}}',
                   '{"state_update":{"upserts":[],"extra":NaN}}',
                   '{"state_update":{"upserts":[],"extra":Infinity}}',
                   '{"state_update":{/*comment*/"upserts":[]}}',
                   '{"state_update":{"upserts":[]},"extra":true}',
                   '{"wrapper":' + valid + '}', '[' + valid + ']',
                   valid + valid, '{"state_update": broken} ' + valid,
                   json.dumps({"state_update": {"upserts": [{**INITIAL[0], "priority": "0"}]}}),
                   json.dumps({"state_update": {"upserts": [{**INITIAL[0], "source": "user"}]}})]
        current, _ = apply_update(empty_state("test"), {"upserts": INITIAL}, "test")
        for text in invalid:
            with self.subTest(text=text):
                state = {"task_id": "test", "requirement_state": copy.deepcopy(current)}
                response = LlmResponse(content=types.Content(role="model", parts=[
                    types.Part.from_text(text="broken wrapper>" + text + "</bad>"),
                    types.Part(function_call=types.FunctionCall(id="native", name="submit_sql", args={"sql": SQL}))]))
                original = response.model_dump()
                self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), response))
                self.assertEqual(response.model_dump(), original)
                self.assertEqual(state["requirement_state"], current)
                self.assertTrue(state["requirement_state_error"])

    async def test_before_model_changes_only_system_instruction(self):
        async def original_before(callback_context, llm_request):
            return None
        content = types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
            id="call_provider_1", name="get_schema", args={}))])
        request = LlmRequest(contents=[content], config=types.GenerateContentConfig(
            temperature=0.0, tools=[types.Tool(function_declarations=[types.FunctionDeclaration(name="get_schema")])]))
        before_config = request.config.model_dump(exclude={"system_instruction"})
        before_contents = request.contents
        before_dump = [c.model_dump() for c in before_contents]
        state = {"task_id": "test", "requirement_state": empty_state("test")}
        state["requirement_state"]["revision"] = 27
        await before_model_with_requirements(original_before)(SimpleNamespace(state=state), request)
        self.assertEqual(request.config.model_dump(exclude={"system_instruction"}), before_config)
        self.assertIs(request.contents, before_contents)
        self.assertEqual([c.model_dump() for c in request.contents], before_dump)
        visible = json.loads(request.config.system_instruction.rsplit(STATE_MARKER, 1)[1])
        self.assertEqual(visible, {"requirements": []})
        self.assertNotIn("base_revision", request.config.system_instruction)
        self.assertNotIn('"revision"', request.config.system_instruction)

    async def test_after_model_preserves_native_response_and_arguments(self):
        state = {"task_id": "test", "requirement_state": empty_state("test")}
        response = LlmResponse(content=types.Content(role="model", parts=[
            types.Part.from_text(text=update_text(INITIAL)),
            types.Part(function_call=types.FunctionCall(id="call_provider_1", name="submit_sql",
                                                       args={"sql": SQL, "unused": "ADK handles arguments"})),
            types.Part(function_call=types.FunctionCall(id="call_provider_2", name="get_schema", args={})),
        ]))
        before = response.model_dump()
        self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), response))
        self.assertEqual(response.model_dump(), before)
        self.assertEqual(state["requirement_state"]["revision"], 1)
        # Partial/error events do not mutate State or rewrite ADK responses.
        for item in [LlmResponse(partial=True, content=response.content), LlmResponse(error_code="upstream")]:
            previous = copy.deepcopy(state)
            self.assertIsNone(await after_model_callback(SimpleNamespace(state=state), item))
            self.assertEqual(state, previous)


class RuntimeSmoke(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.model = ScriptModel()
        self.model_patch = patch("system_agent.agent._build_model", return_value=self.model)
        self.http_patch = patch("system_agent.tools.httpx.Client", FakeClient)
        self.model_patch.start()
        self.http_patch.start()
        FakeClient.calls, FakeClient.asks, FakeClient.observer = [], 0, None
        self.runtime = AdkRuntime()
        self.assertTrue(self.runtime.available, self.runtime.error)

    async def asyncTearDown(self):
        FakeClient.observer = None
        self.http_patch.stop()
        self.model_patch.stop()

    async def session(self, task="smoke", mode="a-interact", reset=False):
        return await self.runtime.init_session(task, mode, {
            "task_id": "untrusted", "budget_remaining": 12., "initial_budget": 12.,
            "db_name": "synthetic", "db_schema": SCHEMA if mode == "c-interact" else "",
            "external_kg": "", "max_turn": 4,
        }, reset=reset)

    async def test_native_smoke_state_saved_before_tools_and_read_next_turn(self):
        await self.session()
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "smoke")]
        observed = []
        def observe():
            session = runner.session_service.sessions[ref.app_name][ref.user_id][ref.session_id]
            observed.append(copy.deepcopy(session.state["requirement_state"]))
        FakeClient.observer = observe
        self.model._steps = [
            (INITIAL, ("get_schema", {})),
            ([SCHEMA_UPDATE], ("get_knowledge_definition", {"knowledge_name": "TCR"})),
            ([KB_UPDATE], ("ask_user", {"question": "Does the generic TCR apply and what is suspicious?"})),
            ([PARTIAL_UPDATE], ("ask_user", {"question": "What threshold and zero-capacity rule apply?"})),
            (FINAL_UPDATES, ("submit_sql", {"sql": SQL})), ([], "Done."),
        ]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        state = result["state"]
        self.assertEqual(len(self.model._requests), 6)
        self.assertEqual(len(state["requirement_state_history"]), 6)
        self.assertEqual([s["revision"] for s in observed], [1, 2, 3, 4, 5])
        self.assertEqual(state["budget_remaining"], 3.5)
        self.assertEqual(len(state["requirement_state"]["requirements"]), 7)
        saved = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(saved.state["requirement_state"], state["requirement_state"])
        self.assertEqual(state["requirement_state"]["revision"], 5)
        self.model._steps = [([], "Read saved state.")]
        later = await self.runtime.run_turn("smoke", "a-interact", "Read the saved requirements.")
        self.assertEqual(self.model._requests[-1]["state"], {"requirements": state["requirement_state"]["requirements"]})
        request_parts = [p for c in self.model._requests[-1]["contents"] for p in c.get("parts", [])]
        calls = [p["function_call"] for p in request_parts if "function_call" in p]
        responses = [p["function_response"] for p in request_parts if "function_response" in p]
        self.assertEqual(len(calls), 5)
        self.assertEqual({c["id"] for c in calls}, {r["id"] for r in responses})
        self.assertTrue(all(c["id"].startswith("call_model_") for c in calls))
        self.assertTrue(any(START in p.get("text", "") for p in request_parts))
        self.assertFalse(any("Tool result (evidence):" in p.get("text", "") for p in request_parts))
        if os.environ.get("REQUIREMENT_SMOKE_ARTIFACT"):
            Path(os.environ["REQUIREMENT_SMOKE_ARTIFACT"]).write_text(json.dumps({
                "kind": "native calls + State text; real ADK, controlled model/HTTP; no SQL evaluation",
                "query": QUERY, "first_run": result, "later_run": later,
                "model_requests": self.model._requests, "http_calls": FakeClient.calls,
                "saved_state_observed_before_tools": observed,
            }, ensure_ascii=False, indent=2) + "\n")

    async def test_recovered_json_is_saved_before_native_tool_and_read_next_turn(self):
        await self.session()
        raw = START + json.dumps({"state_update": {"upserts": INITIAL}}) + "</｜｜DSML｜｜ parameter>"
        self.model._steps = [{"raw_text": raw, "calls": [("get_schema", {})]}, ([], "Done")]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(len(self.model._requests), 2)
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertEqual(result["state"]["budget_remaining"], 11)
        self.assertTrue(all(h["accepted"] for h in result["state"]["requirement_state_history"]))
        self.assertEqual(result["state"]["requirement_state"]["revision"], 1)
        self.assertEqual(self.model._requests[-1]["state"]["requirements"],
                         result["state"]["requirement_state"]["requirements"])

    async def test_invalid_state_allows_tools_and_normal_continuation_without_retry(self):
        await self.session()
        self.model._steps = [(INITIAL, "Ready")]
        good = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        bad_rows = [{**KB_UPDATE, "status": "resolved", "priority": 3}]
        for raw in ["No State supplied", START + "invalid JSON" + END,
                    START + '{"state_update":{"upserts":[],"revision":0}}' + END, update_text(bad_rows),
                    update_text([]) + update_text([]),
                    '{"state_update":{},"state_update":{}}']:
            with self.subTest(raw=raw):
                before = len(self.model._requests)
                before_http = len(FakeClient.calls)
                before_budget = good["state"]["budget_remaining"] - before_http
                self.model._steps = [{"raw_text": raw, "calls": [("get_schema", {})]}, ([], "Continued normally")]
                result = await self.runtime.run_turn("smoke", "a-interact", "New evidence")
                # One tool decision and its ordinary follow-up; no State retry.
                self.assertEqual(len(self.model._requests), before + 2)
                self.assertEqual(result["state"]["requirement_state"], good["state"]["requirement_state"])
                rejected, continued = result["state"]["requirement_state_history"][-2:]
                self.assertFalse(rejected["accepted"])
                self.assertTrue(rejected["error"])
                self.assertTrue(continued["accepted"])
                self.assertFalse(result["state"]["requirement_state_error"])
                self.assertEqual(result["state"]["budget_remaining"], before_budget - 1)
                self.assertEqual(len(FakeClient.calls), before_http + 1)
                self.assertEqual(result["state"]["tool_trajectory"][-1]["tool"], "get_schema")
                self.assertIn("Continued normally", result["response"])

    async def test_missing_initial_state_does_not_block_submit_in_either_mode(self):
        for mode in ["a-interact", "c-interact"]:
            with self.subTest(mode=mode):
                task = "missing-" + mode
                await self.session(task, mode)
                FakeClient.calls = []
                before = len(self.model._requests)
                self.model._steps = [{"raw_text": "", "calls": [("submit_sql", {"sql": SQL})]}]
                if mode == "a-interact":
                    self.model._steps.append({"raw_text": "Submitted normally.", "calls": []})
                result = await self.runtime.run_turn(task, mode, QUERY)
                self.assertEqual(result["state"]["requirement_state"], empty_state(task))
                self.assertTrue(result["state"]["requirement_state_error"])
                self.assertTrue(all(not h["accepted"] for h in result["state"]["requirement_state_history"]))
                self.assertEqual(len(FakeClient.calls), 1)
                self.assertEqual(FakeClient.calls[0]["payload"], {"task_id": task, "sql": SQL})
                self.assertEqual(result["state"]["budget_remaining"], 9. if mode == "a-interact" else 12.)
                self.assertEqual(len(self.model._requests), before + (2 if mode == "a-interact" else 1))

    async def test_business_arguments_still_follow_original_adk(self):
        await self.session()
        self.model._steps = [(INITIAL, ("get_schema", {"unused": "filtered by FunctionTool"})), ([], "Done")]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(result["state"]["budget_remaining"], 11.)
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertEqual(FakeClient.calls[0]["payload"], {"task_id": "smoke"})

    async def test_task_mode_isolation_reset_and_original_submit_batch(self):
        first = await self.session("one")
        self.model._steps = [(INITIAL, "Ready")]
        one = await self.runtime.run_turn("one", "a-interact", QUERY)
        self.assertEqual(one["state"]["task_id"], "one")
        await self.session("two")
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "two")]
        two = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(two.state["requirement_state"], empty_state("two"))
        await self.session("one", "c-interact")
        self.model._steps = [(INITIAL, [("submit_sql", {"sql": SQL}), ("submit_sql", {"sql": SQL})])]
        before = len(self.model._requests)
        c = await self.runtime.run_turn("one", "c-interact", QUERY)
        self.assertEqual(len(self.model._requests), before + 1)
        self.assertEqual(len(c["state"]["tool_trajectory"]), 2)  # Original ADK batch policy.
        self.assertTrue(c["state"]["_submitted_this_phase"])
        self.assertEqual(c["state"]["budget_remaining"], 12.)
        self.model._steps = [([], "New run")]
        again = await self.runtime.run_turn("one", "c-interact", "Recheck")
        self.assertFalse(again["state"]["_submitted_this_phase"])
        reset = await self.session("one", reset=True)
        self.assertNotEqual(first["session_id"], reset["session_id"])


if __name__ == "__main__":
    unittest.main()
