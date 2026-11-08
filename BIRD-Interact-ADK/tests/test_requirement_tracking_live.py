"""Opt-in live-model smoke with synthetic HTTP fixtures; no real DB evaluation.

REQUIREMENT_LIVE_SMOKE=1 python -m unittest discover -s tests -p '*live.py' -v
May incur provider token charges; no environment service is contacted.
"""

import asyncio
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from system_agent.adk_runtime import AdkRuntime
from test_requirement_tracking import FakeClient, QUERY


class LiveClient(FakeClient):
    def post(self, url, json):
        if url.endswith("/submit"):
            self.calls.append({"url": url, "payload": json})
            return type("Response", (), {"status_code": 200, "json": lambda self: {
                "passed": True, "phase_completed": 1, "has_follow_up": False,
                "reward": 0, "message": "Synthetic submission accepted; SQL correctness not evaluated.",
            }})()
        return super().post(url, json)


@unittest.skipUnless(os.environ.get("REQUIREMENT_LIVE_SMOKE") == "1", "opt-in live model test")
class LiveSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_live_model_with_fixture_environment(self):
        LiveClient.calls, LiveClient.asks = [], 0
        runtime = AdkRuntime()
        self.assertTrue(runtime.available, runtime.error)
        await runtime.init_session("live-requirement-smoke", "a-interact", {
            "db_name": "synthetic", "budget_remaining": 16., "initial_budget": 16.,
        })
        with patch("system_agent.tools.httpx.Client", LiveClient):
            result = await asyncio.wait_for(runtime.run_turn(
                "live-requirement-smoke", "a-interact", QUERY,
            ), timeout=240)
        path = os.environ.get("REQUIREMENT_LIVE_ARTIFACT", "/tmp/requirement_tracking_live.json")
        Path(path).write_text(json.dumps({
            "kind": "live configured model + real ADK; synthetic HTTP fixtures; no SQL correctness evaluation",
            "query": QUERY, "result": result, "http_calls": LiveClient.calls,
        }, ensure_ascii=False, indent=2) + "\n")
        state = result["state"]
        self.assertFalse(state["requirement_state_error"], path)
        self.assertTrue(state.get("task_done"), path)
        tools = [t["tool"] for t in state["tool_trajectory"]]
        self.assertTrue({"get_knowledge_definition", "get_all_knowledge_definitions"}.intersection(tools))
        self.assertIn("ask_user", tools)
        self.assertIn("submit_sql", tools)
        self.assertGreaterEqual(LiveClient.asks, 2, "Partial answer must trigger another clarification")
        items = state["requirement_state"]["requirements"]
        self.assertTrue(any("0.8" in r["value"] and r["status"] == "resolved" for r in items))
        self.assertTrue(any("10" in r["value"] and r["priority"] == 0 for r in items))
        self.assertGreater(len(state["requirement_state_history"]), 2)


if __name__ == "__main__":
    unittest.main()
