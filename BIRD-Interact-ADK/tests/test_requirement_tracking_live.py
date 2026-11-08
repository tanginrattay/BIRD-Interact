"""Opt-in real-model one-call smoke; all environment HTTP uses fixtures.

REQUIREMENT_LIVE_SMOKE=1 python -m unittest discover -s tests -p '*live.py' -v
This incurs normal model token charges; there is no separate state model call.
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
from test_requirement_tracking import FakeClient, QUERY


class CountingModel(BaseLlm):
    delegate: BaseLlm
    _requests: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        snapshot = json.loads(llm_request.config.system_instruction.rsplit(
            "Current Requirement State (runtime validated):\n", 1)[1])
        self._requests.append({"state": snapshot, "native_tools_enabled": bool(llm_request.config.tools)})
        async for response in self.delegate.generate_content_async(llm_request, stream=stream):
            yield response


class RecordingClient(LiteLLMClient):
    """Record safe request fields without changing provider messages/output."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.requests = []

    async def acompletion(self, *args, **kwargs):
        self.requests.append({k: copy.deepcopy(kwargs.get(k)) for k in
                              ("model", "messages", "tools", "response_format")})
        return await self.delegate.acompletion(*args, **kwargs)


class LiveClient(FakeClient):
    def post(self, url, json):
        if url.endswith("/submit"):
            type(self).calls.append({"url": url, "payload": json})
            return type("Response", (), {"status_code": 200, "json": lambda self: {
                "passed": True, "phase_completed": 1, "has_follow_up": False,
                "reward": 0, "message": "Synthetic acceptance; SQL correctness not evaluated.",
            }})()
        return super().post(url, json)


@unittest.skipUnless(os.environ.get("REQUIREMENT_LIVE_SMOKE") == "1", "opt-in live-model test")
class LiveSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_live_single_response_state_and_action(self):
        LiveClient.calls, LiveClient.asks, LiveClient.observer = [], 0, None
        model = CountingModel(model=settings.system_agent_model,
                              delegate=build_adk_model(settings.system_agent_model))
        transport = RecordingClient(model.delegate.llm_client)
        model.delegate.llm_client = transport
        with patch("system_agent.agent._build_model", return_value=model):
            runtime = AdkRuntime()
            self.assertTrue(runtime.available, runtime.error)
            await runtime.init_session("live-one-call", "a-interact", {
                "db_name": "synthetic", "budget_remaining": 16., "initial_budget": 16.,
            })
        with patch("system_agent.tools.httpx.Client", LiveClient):
            result = await asyncio.wait_for(runtime.run_turn("live-one-call", "a-interact", QUERY), timeout=240)
        path = os.environ.get("REQUIREMENT_LIVE_ARTIFACT", "/tmp/requirement_tracking_1call_live.json")
        Path(path).write_text(json.dumps({
            "kind": "one-call real model + real ADK; environment fixtures; SQL correctness not evaluated",
            "model": settings.system_agent_model, "query": QUERY, "result": result,
            "model_requests": model._requests, "http_calls": LiveClient.calls,
            "additional_state_model_calls": 0,
            "provider_requests": transport.requests,
        }, ensure_ascii=False, indent=2) + "\n")
        state = result["state"]
        self.assertFalse(state["requirement_state_error"], path)
        self.assertTrue(state.get("task_done"), path)
        history = state["requirement_state_history"]
        self.assertEqual(len(model._requests), len(history))
        self.assertEqual(len(transport.requests), len(model._requests))
        self.assertTrue(all(r["response_format"] == {"type": "json_object"} for r in transport.requests))
        self.assertTrue(all(h["accepted"] for h in history))
        self.assertTrue(all(not r["native_tools_enabled"] for r in model._requests))
        tools = [t["tool"] for t in state["tool_trajectory"]]
        self.assertTrue({"get_knowledge_definition", "get_all_knowledge_definitions"}.intersection(tools))
        self.assertIn("ask_user", tools)
        self.assertIn("submit_sql", tools)
        self.assertGreaterEqual(LiveClient.asks, 2, "partial reply must not invent a threshold")
        items = state["requirement_state"]["requirements"]
        self.assertTrue(any("0.8" in r["value"] and r["status"] == "resolved" for r in items))
        self.assertTrue(any("10" in r["value"] and r["priority"] == 0 for r in items))
        self.assertTrue(any(c["after"]["status"] == "candidate" for h in history for c in h["changes"]))
        # Every model after the first reads precisely the state committed by
        # the preceding response (revision may stay unchanged on empty patches).
        self.assertEqual([r["state"]["revision"] for r in model._requests[1:]],
                         [h["revision"] for h in history[:-1]])


if __name__ == "__main__":
    unittest.main()
