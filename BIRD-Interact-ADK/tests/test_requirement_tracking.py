"""One-call protocol smoke using real ADK, controlled model and HTTP fixtures."""

import asyncio
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from system_agent.adk_runtime import AdkRuntime
from system_agent.requirement_state import apply_update, empty_state

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


class ScriptModel(BaseLlm):
    model: str = "requirement-one-call-smoke"
    _steps: list = PrivateAttr(default_factory=list)
    _requests: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        snapshot = json.loads(llm_request.config.system_instruction.rsplit(
            "Current Requirement State (runtime validated):\n", 1)[1])
        assert llm_request.config.tools is None and llm_request.config.tool_config is None
        assert llm_request.config.response_schema == {"type": "json_object"}
        self._requests.append({"state": snapshot, "contents": [
            c.model_dump(mode="json", exclude_none=True) for c in llm_request.contents],
            "tools": list(llm_request.tools_dict), "native_tools_enabled": False})
        assert self._steps, "unexpected extra model call"
        step = self._steps.pop(0)
        if isinstance(step, dict) and "native" in step:
            content = types.Content(role="model", parts=[types.Part.from_function_call(
                name="get_schema", args={})])
        else:
            if isinstance(step, dict) and "raw" in step:
                raw = step["raw"]
            else:
                upserts, action = step
                calls = [] if isinstance(action, str) else [
                    {"name": n, "args": a} for n, a in (action if isinstance(action, list) else [action])]
                raw = json.dumps({"state_update": {"base_revision": snapshot["revision"], "upserts": upserts},
                                  "tool_calls": calls, "response": action if isinstance(action, str) else ""})
            content = types.Content(role="model", parts=[types.Part.from_text(text=raw)])
        yield LlmResponse(content=content)


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
    def test_optional_audit_reason_keeps_exact_requirement_fields(self):
        patch_rows = [{k: v for k, v in r.items() if k != "reason"} for r in INITIAL]
        state, audit = apply_update(empty_state("a"), {"base_revision": 0, "upserts": patch_rows}, "a")
        self.assertEqual(set(state["requirements"][0]),
                         {"id", "requirement", "category", "status", "value", "priority"})
        self.assertEqual(audit[0]["reason"], "")

    def test_atomic_validation_and_conflict_reopening(self):
        state, _ = apply_update(empty_state("a"), {"base_revision": 0, "upserts": INITIAL}, "a")
        before = copy.deepcopy(state)
        invalids = [
            {"base_revision": 0, "upserts": []},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "category": "invalid"}]},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "status": "resolved", "priority": 3}]},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "priority": True}]},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "source": "KB"}]},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "id": "r7", "requirement": INITIAL[0]["requirement"]}]},
            {"base_revision": 1, "upserts": [KB_UPDATE, KB_UPDATE]},
            {"base_revision": 1, "upserts": [{**KB_UPDATE, "requirement": "rename"}]},
        ]
        for payload in invalids:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                apply_update(state, payload, "a")
            self.assertEqual(state, before)
        with self.assertRaises(ValueError):
            apply_update(state, {"base_revision": 1, "upserts": []}, "another-task")
        for change in [KB_UPDATE, FINAL_UPDATES[1],
                       {**KB_UPDATE, "status": "conflict", "value": "formula A (source: KB) | formula B (source: user)"},
                       {**FINAL_UPDATES[1], "value": "formula B; user explicitly rejects A (source: user)"}, FINAL_UPDATES[2]]:
            state, _ = apply_update(state, {"base_revision": state["revision"], "upserts": [change]}, "a")
        self.assertEqual(len(state["requirements"]), 7)
        self.assertEqual(state["requirements"][0], before["requirements"][0])


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

    async def session(self, task="smoke", mode="a-interact"):
        return await self.runtime.init_session(task, mode, {
            "task_id": "untrusted-task-id", "budget_remaining": 12., "initial_budget": 12.,
            "db_name": "synthetic", "db_schema": SCHEMA if mode == "c-interact" else "",
            "external_kg": "", "max_turn": 4,
        })

    async def test_full_smoke_one_call_per_decision_and_persistence(self):
        await self.session()
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "smoke")]
        observed = []

        def observe_saved_state():
            saved = runner.session_service.sessions[ref.app_name][ref.user_id][ref.session_id]
            observed.append(copy.deepcopy(saved.state["requirement_state"]))

        FakeClient.observer = observe_saved_state
        self.model._steps = [
            (INITIAL, ("get_schema", {})), ([SCHEMA_UPDATE], ("get_knowledge_definition", {"knowledge_name": "TCR"})),
            ([KB_UPDATE], ("ask_user", {"question": "What makes a chain suspicious and does KB TCR apply?"})),
            ([PARTIAL_UPDATE], ("ask_user", {"question": "What threshold, formula and zero-capacity rule should apply?"})),
            (FINAL_UPDATES, ("submit_sql", {"sql": SQL})), ([], "Finished smoke."),
        ]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        state = result["state"]
        self.assertEqual(len(self.model._requests), 6)  # No separate tracking requests.
        self.assertEqual(len(state["requirement_state_history"]), 6)
        self.assertEqual([s["revision"] for s in observed], [1, 2, 3, 4, 5])
        self.assertEqual(state["requirement_state"]["revision"], 5)
        self.assertEqual(len(state["requirement_state"]["requirements"]), 7)
        self.assertTrue(all(r["status"] == "resolved" and r["priority"] == 0
                            for r in state["requirement_state"]["requirements"]))
        self.assertEqual(state["budget_remaining"], 3.5)
        self.assertEqual([t["tool"] for t in state["tool_trajectory"]],
                         ["get_schema", "get_knowledge_definition", "ask_user", "ask_user", "submit_sql"])
        self.assertEqual(self.model._requests[1]["state"]["revision"], 1)
        self.assertEqual(self.model._requests[4]["state"]["requirements"][1]["status"], "candidate")
        saved = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(saved.state["requirement_state"], state["requirement_state"])
        self.assertEqual(saved.state["adk_events"], state["adk_events"])
        self.model._steps = [([], "Rechecked saved state.")]
        later = await self.runtime.run_turn("smoke", "a-interact", "Recheck all saved constraints.")
        self.assertEqual(self.model._requests[-1]["state"], state["requirement_state"])
        self.assertEqual(later["state"]["requirement_state"], state["requirement_state"])
        self.assertEqual(len(self.model._requests), 7)
        history_parts = [p for e in later["state"]["adk_events"] if e["type"] == "adk_event"
                         for p in e["content"]["parts"]]
        call_ids = [p.get("id") for p in history_parts if p["type"] == "function_call"]
        result_ids = [p.get("id") for p in history_parts if p["type"] == "function_response"]
        self.assertEqual(len(call_ids), 5)
        self.assertTrue(all(call_ids))
        self.assertEqual(len(set(call_ids)), 5)
        self.assertEqual(set(call_ids), set(result_ids))
        request_parts = [p for c in self.model._requests[-1]["contents"] for p in c.get("parts", [])]
        self.assertFalse(any("function_call" in p or "function_response" in p for p in request_parts))
        self.assertTrue(any("Tool result (evidence):" in p.get("text", "") for p in request_parts))
        self.assertTrue(any('"state_update"' in p.get("text", "") for p in request_parts))
        if os.environ.get("REQUIREMENT_SMOKE_ARTIFACT"):
            Path(os.environ["REQUIREMENT_SMOKE_ARTIFACT"]).write_text(json.dumps({
                "kind": "one-call protocol; real ADK; scripted model and HTTP; SQL correctness not evaluated",
                "query": QUERY, "first_run": result, "later_run": later,
                "model_requests": self.model._requests, "http_calls": FakeClient.calls,
                "persisted_state_observed_before_tool_execution": observed,
            }, ensure_ascii=False, indent=2) + "\n")

    async def test_invalid_response_keeps_state_and_executes_no_tools(self):
        await self.session()
        self.model._steps = [(INITIAL, "Initialized.")]
        good = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        invalid = {"state_update": {"base_revision": 1, "upserts": [SCHEMA_UPDATE]},
                   "tool_calls": [{"name": "get_schema", "args": {}}], "response": ""}
        payloads = ["not JSON", json.dumps({"tool_calls": [], "response": "missing state_update"}),
                    json.dumps({**invalid, "state_update": {"base_revision": 0, "upserts": []}}),
                    json.dumps({**invalid, "tool_calls": [{"name": "not_a_tool", "args": {}}]}),
                    json.dumps({**invalid, "tool_calls": [{"name": "ask_user", "args": {}}]}),
                    json.dumps({**invalid, "tool_calls": [{"name": "get_schema", "args": {"task_id": "other"}}]}),
                    json.dumps({**invalid, "tool_calls": [{"name": "submit_sql", "args": {"sql": SQL}},
                                                          {"name": "get_schema", "args": {}}]}),
                    '{"response":"a","response":"b"}']
        for raw in payloads:
            with self.subTest(raw=raw):
                before_calls = len(self.model._requests)
                self.model._steps = [{"raw": raw}]
                bad = await self.runtime.run_turn("smoke", "a-interact", "New evidence")
                self.assertEqual(len(self.model._requests), before_calls + 1)
                self.assertEqual(bad["state"]["requirement_state"], good["state"]["requirement_state"])
                self.assertTrue(bad["state"]["requirement_state_error"])
                self.assertEqual(bad["state"]["budget_remaining"], 12.)
                self.assertEqual(FakeClient.calls, [])

    async def test_native_response_cannot_bypass_state_protocol(self):
        await self.session()
        self.model._steps = [{"native": True}]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(result["state"]["requirement_state"], empty_state("smoke"))
        self.assertTrue(result["state"]["requirement_state_error"])
        self.assertEqual(FakeClient.calls, [])

    async def test_task_mode_isolation_reset_and_cinteract(self):
        first = await self.session("one")
        self.model._steps = [(INITIAL, "Ready.")]
        one = await self.runtime.run_turn("one", "a-interact", QUERY)
        self.assertEqual(one["state"]["task_id"], "one")
        self.assertEqual(one["state"]["requirement_state"]["task_id"], "one")
        two = await self.session("two")
        self.assertNotEqual(first["session_id"], two["session_id"])
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "two")]
        fresh = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(fresh.state["requirement_state"], empty_state("two"))
        await self.session("one", "c-interact")
        self.model._steps = [(INITIAL, ("submit_sql", {"sql": SQL}))]
        before_calls = len(self.model._requests)
        c = await self.runtime.run_turn("one", "c-interact", QUERY)
        self.assertEqual(len(self.model._requests), before_calls + 1)
        self.assertTrue(c["state"]["_submitted_this_phase"])
        self.assertEqual(c["state"]["budget_remaining"], 12.)
        self.model._steps = [([], "Next turn sees saved state.")]
        c2 = await self.runtime.run_turn("one", "c-interact", "Recheck")
        self.assertFalse(c2["state"]["_submitted_this_phase"])
        self.assertEqual(c["state"]["requirement_state"], c2["state"]["requirement_state"])
        reset = await self.runtime.init_session("one", "a-interact", reset=True)
        self.assertNotEqual(first["session_id"], reset["session_id"])

    async def test_same_session_concurrent_turns_are_serialized(self):
        await self.session()
        self.model._steps = [(INITIAL, "First"), ([], "Second")]
        results = await asyncio.gather(self.runtime.run_turn("smoke", "a-interact", QUERY),
                                       self.runtime.run_turn("smoke", "a-interact", "Keep constraints"))
        self.assertEqual(len(self.model._requests), 2)
        self.assertEqual(len(results[1]["state"]["requirement_state_history"]), 2)
        self.assertEqual(results[1]["state"]["requirement_state"]["revision"], 1)

    async def test_query_batch_uses_unique_ids_and_original_budget(self):
        await self.session()
        self.model._steps = [(INITIAL, [("get_schema", {}), ("get_all_external_knowledge_names", {})]),
                             ([SCHEMA_UPDATE], "Done with schema and names.")]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(len(self.model._requests), 2)
        self.assertEqual(result["state"]["budget_remaining"], 10.5)
        events = result["state"]["adk_events"]
        ids = [p["id"] for e in events if e["type"] == "adk_event"
               for p in e["content"]["parts"] if p["type"] == "function_call"]
        self.assertEqual(len(set(ids)), 2)
        self.assertTrue(all(i.startswith("call_req_") for i in ids))

    async def test_litellm_adapter_forwards_json_object_format(self):
        from google.adk.models.lite_llm import _get_completion_inputs
        from google.adk.models.llm_request import LlmRequest
        from types import SimpleNamespace
        from system_agent.requirement_tracking import requirement_callbacks

        async def original_before(callback_context, llm_request):
            return None

        before, _ = requirement_callbacks(original_before, [])
        request = LlmRequest(model="deepseek/deepseek-flash", contents=[
            types.Content(role="user", parts=[types.Part.from_text(text=QUERY)])])
        await before(SimpleNamespace(state={"task_id": "adapter-test"}), request)
        _, tools, response_format, _, _ = await _get_completion_inputs(request, request.model)
        self.assertIsNone(tools)
        self.assertEqual(response_format, {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
