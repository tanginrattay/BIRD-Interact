"""Offline smoke: real ADK Runner/runtime/callbacks/tools, controlled model+HTTP.

Run: /home/nimir/miniconda3/envs/bird-interact/bin/python -m unittest discover -s tests -v
"""

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
from system_agent.requirement_tracking import TRACKING_INSTRUCTION, DECISION_INSTRUCTION, extract_update


QUERY = "Find the top 10 suspicious chains ordered by TCR descending. Return chain_id and TCR."
SCHEMA = "CREATE TABLE chains(chain_id integer, total numeric, capacity numeric);"


def row(i, text, category="user_semantics", status="unresolved", value="", priority=3):
    return dict(id=f"r{i}", requirement=text, category=category, status=status,
                value=value, priority=priority, reason="Compared all visible evidence with prior answer.")


INITIAL = [
    row(1, "Return 10 chains", status="resolved", value="10 (source: user)", priority=0),
    row(2, "Define suspicious chains"),
    row(3, "Determine TCR formula", "knowledge"),
    row(4, "Sort by TCR descending", status="resolved", value="TCR DESC (source: user)", priority=0),
    row(5, "Map chain identifiers and formula inputs", "schema"),
    row(6, "Return chain_id and TCR columns", status="resolved", value="chain_id, TCR (source: user)", priority=0),
]
SCHEMA_UPDATE = row(5, INITIAL[4]["requirement"], "schema", "resolved",
                    "chains(chain_id,total,capacity); no joins (source: get_schema)", 0)
KB_UPDATE = row(3, INITIAL[2]["requirement"], "knowledge", "candidate",
                "TCR = total/capacity; applicability unconfirmed (source: KB)", 3)
PARTIAL_UPDATE = row(2, INITIAL[1]["requirement"], "user_semantics", "candidate",
                     "TCR above a threshold, numeric threshold missing (source: user)", 3)
FINAL_UPDATES = [
    row(2, INITIAL[1]["requirement"], "user_semantics", "resolved", "TCR > 0.8 (source: user)", 0),
    row(3, INITIAL[2]["requirement"], "user_semantics", "resolved",
        "TCR = total/NULLIF(capacity,0); confirmed KB applicability (source: user & KB)", 0),
]
SQL = "SELECT chain_id, total/NULLIF(capacity,0) AS tcr FROM chains WHERE total/NULLIF(capacity,0)>0.8 ORDER BY tcr DESC LIMIT 10"


class ScriptModel(BaseLlm):
    model: str = "requirement-smoke-script"
    _patches: list = PrivateAttr(default_factory=list)
    _actions: list = PrivateAttr(default_factory=list)
    _requests: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        is_tracking = llm_request.config.system_instruction == TRACKING_INSTRUCTION
        if is_tracking:
            data = json.loads(llm_request.contents[0].parts[0].text)
            self._requests.append({"kind": "tracking", "input": data})
            payload = self._patches.pop(0)
            if isinstance(payload, list):
                payload = {"upserts": payload}
            content = types.Content(role="model", parts=[types.Part.from_text(text=payload if isinstance(payload, str) else json.dumps(payload))])
        else:
            self._requests.append({"kind": "decision", "system": llm_request.config.system_instruction})
            action = self._actions.pop(0)
            if isinstance(action, str):
                content = types.Content(role="model", parts=[types.Part.from_text(text=action)])
            elif isinstance(action, dict):
                content = types.Content(role="model", parts=[types.Part.from_function_call(name=n, args=a)
                                                             for n, a in action["calls"]])
            else:
                content = types.Content(role="model", parts=[types.Part.from_function_call(name=action[0], args=action[1])])
        yield LlmResponse(content=content)


class FakeClient:
    calls = []
    asks = 0

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def post(self, url, json):
        self.calls.append({"url": url, "payload": json})
        if url.endswith("/schema"):
            data = {"schema": SCHEMA}
        elif url.endswith("/knowledge"):
            data = {"knowledge": "TCR = total/capacity (generic definition; confirm task applicability)."}
        elif url.endswith("/knowledge_names"):
            data = {"names": ["TCR"]}
        elif url.endswith("/execute"):
            data = {"success": True, "result": "chain_id | tcr\n1 | 0.9"}
        elif url.endswith("/ask"):
            type(self).asks += 1
            data = {"answer": "Suspicious means TCR above a threshold." if self.asks == 1 else
                    "Use TCR > 0.8. TCR means total/capacity here; exclude zero capacity."}
        elif url.endswith("/submit"):
            data = {"passed": False, "message": "Fixture records submission; no SQL evaluator was run."}
        else:
            raise AssertionError(url)
        return type("Response", (), {"status_code": 200, "json": lambda self: data})()


class ValidationTests(unittest.TestCase):
    def test_runtime_revision_and_strict_json_recovery(self):
        initial = {"upserts": INITIAL}
        raw = json.dumps(initial)
        for text in [raw, "<broken>" + raw, raw + "</missing>",
                     "Plan:\n```json\n" + raw + "\n``` Done",
                     '<requirement_state_update" >' + raw + '</｜｜DSML｜｜ parameter>',
                     '{"other": true} ' + raw]:
            with self.subTest(text=text):
                self.assertEqual(extract_update(text), initial)
        state, _ = apply_update(empty_state("a"), initial, "a")
        self.assertEqual(state["revision"], 1)
        unchanged, changes = apply_update(state, initial, "a")
        self.assertEqual(unchanged, state)
        self.assertEqual(changes, [])
        unchanged, changes = apply_update(state, {"upserts": []}, "a")
        self.assertEqual(unchanged, state)
        self.assertEqual(changes, [])
        updated, _ = apply_update(state, {"upserts": [KB_UPDATE]}, "a")
        self.assertEqual(updated["revision"], 2)
        quoted = copy.deepcopy(initial)
        quoted["upserts"][0]["value"] = 'braces { } and quote " (source: user)'
        self.assertEqual(extract_update("Text " + json.dumps(quoted) + " End"), quoted)

    def test_outer_recovery_rejects_broken_or_ambiguous_inner_json(self):
        valid = json.dumps({"upserts": INITIAL})
        for raw in [valid[:-1], valid[:-1] + ",}", "{'upserts': []}",
                    '{"upserts":[],"upserts":[]}', '{"upserts":[NaN]}',
                    '{"upserts":[Infinity]}', '{"upserts":/* comment */[]}',
                    '{"wrapper":' + valid + '}', '[' + valid + ']',
                    valid + valid, '{"upserts": broken} ' + valid,
                    '{"upserts":[],"revision":0}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                extract_update("broken wrapper>" + raw + "</bad>")

    def test_atomic_validation_and_transitions(self):
        state, _ = apply_update(empty_state("a"), {"upserts": INITIAL}, "a")
        before = copy.deepcopy(state)
        invalids = [
            {"base_revision": 0, "upserts": []},  # runtime-owned; model field forbidden
            {"revision": 1, "upserts": []},
            {"upserts": [{**KB_UPDATE, "category": "made_up"}]},
            {"upserts": [{**KB_UPDATE, "status": "resolved", "priority": 3}]},
            {"upserts": [{**KB_UPDATE, "priority": True}]},
            {"upserts": [{**KB_UPDATE, "source": "KB"}]},
            {"upserts": [{**KB_UPDATE, "id": "r7", "requirement": INITIAL[0]["requirement"]}]},
            {"upserts": [KB_UPDATE, KB_UPDATE]},
            {"upserts": [{**KB_UPDATE, "requirement": "renamed away"}]},
            {"upserts": [{**KB_UPDATE, "status": "conflict", "value": "only one answer"}]},
        ]
        for payload in invalids:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                apply_update(state, payload, "a")
            self.assertEqual(state, before)
        with self.assertRaises(ValueError):
            apply_update(state, {"upserts": []}, "other")
        for change in [KB_UPDATE, FINAL_UPDATES[1],
                       {**KB_UPDATE, "status": "conflict", "value": "formula A (source: KB) | formula B (source: user)"},
                       {**FINAL_UPDATES[1], "value": "formula B; user explicitly rejects A (source: user)"}]:
            state, _ = apply_update(state, {"upserts": [change]}, "a")
        self.assertEqual(len(state["requirements"]), 6)
        self.assertEqual(state["requirements"][2]["priority"], 0)
        self.assertEqual(state["requirements"][0], before["requirements"][0])
        state, _ = apply_update(state, {"upserts": [
            row(7, "Output format", "user_semantics", "resolved", "SQL query (source: user)", 0),
        ]}, "a")
        self.assertEqual(len(state["requirements"]), 7)


class RuntimeSmoke(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.model = ScriptModel()
        self.model_patch = patch("system_agent.agent._build_model", return_value=self.model)
        self.model_patch.start()
        self.http_patch = patch("system_agent.tools.httpx.Client", FakeClient)
        self.http_patch.start()
        FakeClient.calls, FakeClient.asks = [], 0
        self.runtime = AdkRuntime()
        self.assertTrue(self.runtime.available, self.runtime.error)

    async def asyncTearDown(self):
        self.http_patch.stop()
        self.model_patch.stop()

    async def session(self, task="smoke", mode="a-interact"):
        return await self.runtime.init_session(task, mode, {
            "task_id": "untrusted-input-id", "budget_remaining": 12., "initial_budget": 12.,
            "db_name": "synthetic", "db_schema": SCHEMA if mode == "c-interact" else "",
            "external_kg": "", "max_turn": 4,
        })

    async def test_full_smoke_and_cross_turn_persistence(self):
        # a-interact should retrieve its schema through the charged tool.
        await self.session()
        self.model._patches = [INITIAL, [SCHEMA_UPDATE], [KB_UPDATE], [PARTIAL_UPDATE], FINAL_UPDATES, []]
        self.model._actions = [
            ("get_schema", {}), ("get_knowledge_definition", {"knowledge_name": "TCR"}),
            ("ask_user", {"question": "What makes a chain suspicious, and does KB TCR apply?"}),
            ("ask_user", {"question": "What threshold, exact formula and zero-denominator rule should apply?"}),
            ("submit_sql", {"sql": SQL}), "Finished smoke.",
        ]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        state = result["state"]
        self.assertEqual(state["requirement_state"]["revision"], 5)
        self.assertEqual(len(state["requirement_state"]["requirements"]), 6)
        self.assertTrue(all(r["status"] == "resolved" and r["priority"] == 0
                            for r in state["requirement_state"]["requirements"]))
        self.assertEqual(state["budget_remaining"], 3.5)
        self.assertEqual([t["tool"] for t in state["tool_trajectory"]],
                         ["get_schema", "get_knowledge_definition", "ask_user", "ask_user", "submit_sql"])
        decisions = [r for r in self.model._requests if r["kind"] == "decision"]
        self.assertEqual(len(decisions), 6)
        self.assertNotIn('"revision"', decisions[4]["system"])
        self.assertIn("TCR > 0.8", decisions[4]["system"])
        self.assertIn("numeric threshold missing", decisions[3]["system"])
        # Fresh get_session proves state_delta persistence, not just callback-local data.
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "smoke")]
        saved = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(saved.state["requirement_state"], state["requirement_state"])
        self.assertEqual(saved.state["adk_events"], state["adk_events"])
        old_events = len(state["adk_events"])
        self.model._patches = [[]]
        self.model._actions = ["Rechecked all constraints."]
        later = await self.runtime.run_turn("smoke", "a-interact", "Recheck the saved requirements.")
        self.assertEqual(later["state"]["requirement_state"], state["requirement_state"])
        self.assertGreater(len(later["state"]["adk_events"]), old_events)
        self.assertNotIn('"revision"', self.model._requests[-1]["system"])
        if os.environ.get("REQUIREMENT_SMOKE_ARTIFACT"):
            Path(os.environ["REQUIREMENT_SMOKE_ARTIFACT"]).write_text(json.dumps({
                "kind": "offline real-ADK smoke; scripted model and HTTP fixtures; no database evaluation",
                "query": QUERY, "first_run": result, "later_run": later,
                "model_requests": self.model._requests, "http_calls": FakeClient.calls,
            }, ensure_ascii=False, indent=2) + "\n")

    async def test_task_mode_isolation_reset_and_cinteract(self):
        first = await self.session("one")
        self.model._patches, self.model._actions = [INITIAL], ["Ready."]
        one = await self.runtime.run_turn("one", "a-interact", QUERY)
        self.assertEqual(one["state"]["requirement_state"]["task_id"], "one")
        self.assertEqual(one["state"]["task_id"], "one")
        two = await self.session("two")
        self.assertNotEqual(first["session_id"], two["session_id"])
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "two")]
        untouched = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(untouched.state["requirement_state"], empty_state("two"))
        await self.session("one", "c-interact")
        self.model._patches, self.model._actions = [INITIAL], [("submit_sql", {"sql": SQL})]
        c = await self.runtime.run_turn("one", "c-interact", QUERY)
        self.assertEqual(len(c["state"]["requirement_state"]["requirements"]), 6)
        self.assertEqual(c["state"]["budget_remaining"], 12.)
        self.assertTrue(c["state"]["_submitted_this_phase"])
        self.model._patches, self.model._actions = [[]], ["Next turn sees the same state."]
        c2 = await self.runtime.run_turn("one", "c-interact", "Recheck")
        self.assertFalse(c2["state"]["_submitted_this_phase"])
        reset = await self.runtime.init_session("one", "a-interact", reset=True)
        self.assertNotEqual(first["session_id"], reset["session_id"])
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "one")]
        fresh = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(fresh.state["requirement_state"], empty_state("one"))

    async def test_invalid_update_correction_then_nonblocking_failure(self):
        await self.session()
        self.model._patches = [{"bad": "field"}, INITIAL]
        self.model._actions = ["Ready."]
        good = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(good["state"]["requirement_state"]["revision"], 1)
        self.assertEqual(len(good["state"]["requirement_state_history"][0]["attempts"]), 2)
        self.model._patches = [{"bad": "field"}, {"bad": "field"}, []]
        self.model._actions = [("get_schema", {}), "Continued normally"]
        bad = await self.runtime.run_turn("smoke", "a-interact", "New evidence")
        self.assertEqual(bad["state"]["requirement_state"], good["state"]["requirement_state"])
        failed = bad["state"]["requirement_state_history"][-2]
        self.assertTrue(all(not a["accepted"] for a in failed["attempts"]))
        self.assertEqual(failed["changes"], [])
        self.assertEqual(bad["state"]["budget_remaining"], 11.)
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertFalse(bad["state"]["requirement_state_error"])
        self.assertIn("Continued normally", bad["response"])
        decisions = [r for r in self.model._requests if r["kind"] == "decision"]
        self.assertIn('"Return 10 chains"', decisions[-2]["system"])

    async def test_same_session_concurrent_turns_are_serialized(self):
        import asyncio
        await self.session()
        self.model._patches, self.model._actions = [INITIAL, []], ["First", "Second"]
        results = await asyncio.gather(
            self.runtime.run_turn("smoke", "a-interact", QUERY),
            self.runtime.run_turn("smoke", "a-interact", "Keep all constraints"),
        )
        self.assertEqual(len(results[1]["state"]["requirement_state_history"]), 2)
        self.assertEqual(results[1]["state"]["requirement_state"]["revision"], 1)

    async def test_mixed_submit_batch_uses_original_tools_and_budget(self):
        await self.session()
        self.model._patches = [INITIAL, []]
        self.model._actions = [{"calls": [("ask_user", {"question": "new evidence?"}), ("submit_sql", {"sql": SQL})]}, "Done"]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(result["state"]["requirement_state"]["revision"], 1)
        self.assertFalse(result["state"]["requirement_state_error"])
        self.assertEqual(len(FakeClient.calls), 2)
        self.assertEqual({t["tool"] for t in result["state"]["tool_trajectory"]}, {"ask_user", "submit_sql"})
        self.assertEqual(result["state"]["budget_remaining"], 7.)

    async def test_missing_initial_state_does_not_block_submission_in_both_modes(self):
        for mode in ["a-interact", "c-interact"]:
            with self.subTest(mode=mode):
                task = "missing-" + mode
                await self.session(task, mode)
                FakeClient.calls = []
                self.model._patches = ["No update", "No update"]
                self.model._actions = [("submit_sql", {"sql": SQL})]
                if mode == "a-interact":
                    self.model._patches += ["No update", "No update"]
                    self.model._actions += ["Done"]
                result = await self.runtime.run_turn(task, mode, QUERY)
                self.assertEqual(result["state"]["requirement_state"], empty_state(task))
                self.assertTrue(result["state"]["requirement_state_error"])
                self.assertEqual(len(FakeClient.calls), 1)
                self.assertTrue(FakeClient.calls[0]["url"].endswith("/submit"))
                self.assertEqual(result["state"]["budget_remaining"], 9. if mode == "a-interact" else 12.)
                self.assertTrue(all(not attempt["accepted"] for h in result["state"]["requirement_state_history"] for attempt in h["attempts"]))

    async def test_recovered_json_is_saved_and_visible_without_version_fields(self):
        await self.session()
        self.model._patches = ['<broken>' + json.dumps({"upserts": INITIAL}) + '</｜｜DSML｜｜ parameter>', [SCHEMA_UPDATE]]
        self.model._actions = [("get_schema", {}), "Done"]
        result = await self.runtime.run_turn("smoke", "a-interact", QUERY)
        self.assertEqual(result["state"]["requirement_state"]["revision"], 2)
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertEqual(result["state"]["budget_remaining"], 11.)
        self.assertEqual(len(self.model._requests), 4)
        for request in self.model._requests:
            if request["kind"] == "tracking":
                self.assertEqual(set(request["input"]["current_state"]), {"requirements"})
            else:
                visible = json.JSONDecoder().raw_decode(request["system"].split("Current Requirement State (runtime validated):\n",1)[1])[0]
                self.assertEqual(set(visible), {"requirements"})
        runner, _ = await self.runtime._get_runner("a-interact")
        ref = self.runtime._session_refs[("a-interact", "smoke")]
        saved = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
        self.assertEqual(saved.state["requirement_state"], result["state"]["requirement_state"])



if __name__ == "__main__":
    unittest.main()
