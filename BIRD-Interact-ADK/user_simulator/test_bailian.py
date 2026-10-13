"""Offline HTTP and routing tests; all requests use a mock transport."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from shared.config import settings
from user_simulator import bailian, server


class BailianTests(unittest.TestCase):
    def setUp(self):
        config = patch.multiple(
            settings, user_sim_model="qwen3.7-plus", user_sim_pipeline="single_stage",
            user_sim_api_base="https://bailian.test/compatible-mode/v1",
            user_sim_api_key="fake-simulator-key", user_sim_enable_thinking=False,
            user_sim_thinking_budget=2048,
        )
        config.start()
        self.addCleanup(config.stop)
        self.requests = []
        self.response = {"choices": [{"finish_reason": "stop", "message": {
            "content": "Weather conditions.", "reasoning_content": "PRIVATE REASONING",
        }}], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}
        self.status = 200
        real_client = httpx.Client

        def handler(request):
            self.requests.append(request)
            return httpx.Response(self.status, json=self.response)

        mock_client = patch.object(bailian.httpx, "Client", side_effect=lambda **kw:
                                   real_client(transport=httpx.MockTransport(handler), **kw))
        mock_client.start()
        self.addCleanup(mock_client.stop)

    def test_wire_format_and_isolated_credentials(self):
        with patch.object(settings, "litellm_api_key", "fake-system-key"):
            answer = server._call_llm("question", 1024, system_prompt="instructions")
        self.assertEqual(answer, "Weather conditions.")
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://bailian.test/compatible-mode/v1/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer fake-simulator-key")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "qwen3.7-plus")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertFalse(body["enable_thinking"])
        self.assertFalse(body["stream"])
        self.assertEqual(body["max_completion_tokens"], 1024)
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("extra_body", body)
        self.assertNotIn("thinking_budget", body)

    def test_optional_bounded_thinking(self):
        with patch.object(settings, "user_sim_enable_thinking", True):
            bailian.call_bailian([])
        body = json.loads(self.requests[0].content)
        self.assertTrue(body["enable_thinking"])
        self.assertEqual(body["thinking_budget"], 2048)
        self.assertEqual(body["max_completion_tokens"], 3072)

    def test_missing_key_never_falls_back(self):
        with patch.object(settings, "user_sim_api_key", ""), self.assertRaisesRegex(ValueError, "USER_SIM_API_KEY"):
            server._call_llm("question")
        self.assertEqual(self.requests, [])

    def test_truncated_or_empty_response_is_not_a_user_answer(self):
        for finish, content in [("length", "partial"), ("stop", ""), ("stop", None), ("content_filter", None)]:
            with self.subTest(finish=finish, content=content):
                self.response["choices"][0].update(finish_reason=finish, message={
                    "content": content, "reasoning_content": "not an answer"})
                with self.assertRaises(ValueError):
                    bailian.call_bailian([])
        self.response = {"choices": []}
        with self.assertRaisesRegex(ValueError, "no choices"):
            bailian.call_bailian([])

    def test_http_failure_surfaces_without_retry_or_fallback(self):
        self.status = 401
        self.response = {"error": {"message": "invalid key"}}
        with self.assertRaises(httpx.HTTPStatusError):
            bailian.call_bailian([])
        self.assertEqual(len(self.requests), 1)

    def test_real_lite_context_uses_single_stage(self):
        root = Path(__file__).resolve().parent.parent
        tasks = {t["instance_id"]: t for t in map(json.loads,
                 (root / "bird-interact-lite/bird_interact_data.jsonl").read_text().splitlines())}
        for task_id in ("alien_1", "gaming_7", "cybermarket_2"):
            with self.subTest(task_id=task_id), patch.object(server, "_parse_action") as parser:
                history = [{"role": "user", "content": "earlier clarification"}]
                server._ask_sync(server.TaskSimState(tasks[task_id]), "current question", history)
                parser.assert_not_called()
                body = json.loads(self.requests[-1].content)
                context = body["messages"][1]["content"]
                for value in (task_id, tasks[task_id]["query"], tasks[task_id]["amb_user_query"],
                              "current question", "earlier clarification", tasks[task_id]["sol_sql"][0]):
                    self.assertIn(value, context)

    def test_protocol_selection_and_non_qwen_legacy_transport(self):
        state = object()
        with patch.object(server, "_ask_direct", return_value="direct") as direct, \
             patch.object(server, "_parse_action", return_value="action") as parse, \
             patch.object(server, "_generate_response", return_value="two-stage"):
            with patch.object(settings, "user_sim_pipeline", "auto"):
                self.assertEqual(server._ask_sync(state, "q"), "direct")
            with patch.object(settings, "user_sim_pipeline", "two_stage"):
                self.assertEqual(server._ask_sync(state, "q"), "two-stage")
            direct.assert_called_once()
            parse.assert_called_once()
        with patch.object(settings, "user_sim_model", "moonshot/kimi-k2.6"), \
             patch("shared.llm.call_llm", return_value="legacy answer") as legacy:
            self.assertEqual(server._call_llm("q", reasoning_effort="none"), "legacy answer")
            self.assertEqual(legacy.call_args.kwargs["reasoning_effort"], "none")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
