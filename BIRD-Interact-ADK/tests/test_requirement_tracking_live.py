"""Opt-in native-tools smoke; real model, synthetic environment HTTP.

REQUIREMENT_LIVE_SMOKE=1 python -m unittest discover -s tests -p '*live.py' -v
No additional state inference or changes to provider tools/history/JSON mode.
"""

import asyncio
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLLMClient
from pydantic import PrivateAttr

from shared.config import settings
from shared.llm import build_adk_model
from system_agent.adk_runtime import AdkRuntime
from system_agent.requirement_tracking import STATE_MARKER
from test_requirement_tracking import FakeClient, QUERY

LIVE_QUERY = QUERY + (
    " Suspicious uses my personal numeric threshold, which I have not given. "
    "TCR is my custom metric; confirm its exact formula and the threshold with me."
)


class CountingModel(BaseLlm):
    delegate: BaseLlm
    _requests: list = PrivateAttr(default_factory=list)
    _responses: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        snapshot = json.loads(llm_request.config.system_instruction.rsplit(STATE_MARKER, 1)[1])
        self._requests.append({"state": snapshot, "native_tools_enabled": bool(llm_request.config.tools),
                               "response_schema": llm_request.config.response_schema,
                               "contents": [c.model_dump(mode="json", exclude_none=True) for c in llm_request.contents]})
        async for response in self.delegate.generate_content_async(llm_request, stream=stream):
            self._responses.append(response.model_dump(mode="json", exclude_none=True))
            yield response


class RecordingClient(LiteLLMClient):
    def __init__(self, delegate):
        self.delegate = delegate
        self.requests = []
        self.responses = []

    async def acompletion(self, *args, **kwargs):
        self.requests.append({k: copy.deepcopy(kwargs.get(k)) for k in
                              ("model", "messages", "tools", "response_format", "tool_choice")})
        response = await self.delegate.acompletion(*args, **kwargs)
        self.responses.append({"choices": [{"finish_reason": c.finish_reason,
             "message": c.message.model_dump(mode="json", include={"role", "content", "tool_calls"})}
             for c in response.choices]})
        return response


class LiveClient(FakeClient):
    def post(self, url, json):
        if url.endswith("/submit"):
            type(self).calls.append({"url": url, "payload": json})
            return type("Response", (), {"status_code": 200, "json": lambda self: {
                "passed": True, "phase_completed": 1, "has_follow_up": False,
                "reward": 0, "message": "Synthetic acceptance; SQL correctness not evaluated.",
            }})()
        return super().post(url, json)


@unittest.skipUnless(os.environ.get("REQUIREMENT_LIVE_SMOKE") == "1", "opt-in real model test")
class LiveSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_native_calls_and_state_in_same_real_response(self):
        LiveClient.calls, LiveClient.asks, LiveClient.observer = [], 0, None
        model = CountingModel(model=settings.system_agent_model,
                              delegate=build_adk_model(settings.system_agent_model))
        transport = RecordingClient(model.delegate.llm_client)
        model.delegate.llm_client = transport
        with patch("system_agent.agent._build_model", return_value=model):
            runtime = AdkRuntime()
            self.assertTrue(runtime.available, runtime.error)
            await runtime.init_session("native-smoke", "a-interact", {
                "db_name": "synthetic", "budget_remaining": 16., "initial_budget": 16.,
            })
        result = None
        try:
            with patch("system_agent.tools.httpx.Client", LiveClient):
                result = await asyncio.wait_for(runtime.run_turn("native-smoke", "a-interact", LIVE_QUERY), timeout=180)
        finally:
            runner, _ = await runtime._get_runner("a-interact")
            ref = runtime._session_refs[("a-interact", "native-smoke")]
            saved = await runner.session_service.get_session(app_name=ref.app_name, user_id=ref.user_id, session_id=ref.session_id)
            path = os.environ.get("REQUIREMENT_LIVE_ARTIFACT", "/tmp/requirement_native_live.json")
            Path(path).write_text(json.dumps({
                "kind": "native tools + State text; real model, synthetic HTTP; SQL correctness not evaluated",
                "model": settings.system_agent_model, "query": LIVE_QUERY, "result": result,
                "saved_state": saved.state, "model_requests": model._requests,
                "raw_adk_model_responses": model._responses, "provider_client_requests": transport.requests,
                "litellm_responses": transport.responses, "http_calls": LiveClient.calls,
                "additional_state_model_calls": 0,
            }, ensure_ascii=False, indent=2) + "\n")
        state = result["state"]
        self.assertFalse(state["requirement_state_error"], path)
        self.assertTrue(state.get("task_done"), path)
        self.assertEqual(len(model._requests), len(state["requirement_state_history"]))
        self.assertEqual(len(transport.requests), len(model._requests))
        self.assertTrue(all(h["accepted"] for h in state["requirement_state_history"]))
        self.assertTrue(all(r["tools"] and r["response_format"] is None and r["tool_choice"] is None
                            for r in transport.requests))
        for response in model._responses:
            parts = response.get("content", {}).get("parts", [])
            if any("function_call" in p for p in parts):
                self.assertTrue(any(p.get("text") for p in parts))
                self.assertTrue(all(p["function_call"].get("id") for p in parts if "function_call" in p))
        self.assertTrue(any(m["role"] == "tool" for r in transport.requests for m in r["messages"]))
        self.assertTrue(any(m.get("tool_calls") for r in transport.requests for m in r["messages"]))
        self.assertEqual(saved.state["requirement_state"], state["requirement_state"])
        tools = [t["tool"] for t in state["tool_trajectory"]]
        self.assertTrue({"get_knowledge_definition", "get_all_knowledge_definitions"}.intersection(tools))
        self.assertIn("ask_user", tools)
        self.assertIn("submit_sql", tools)
        self.assertGreaterEqual(LiveClient.asks, 2, "partial answer must not invent a numeric threshold")
        self.assertTrue(any("0.8" in r["value"] and r["status"] == "resolved"
                            for r in state["requirement_state"]["requirements"]))
        self.assertEqual([r["state"]["revision"] for r in model._requests[1:]],
                         [h["revision"] for h in state["requirement_state_history"][:-1]])


if __name__ == "__main__":
    unittest.main()
