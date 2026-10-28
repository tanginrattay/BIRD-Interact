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
            settings, user_sim_model="qwen3.7-plus", user_sim_pipeline="two_stage",
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
            answer = server._call_llm("question", 1024)
        self.assertEqual(answer, "Weather conditions.")
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://bailian.test/compatible-mode/v1/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer fake-simulator-key")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "qwen3.7-plus")
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])
        self.assertFalse(body["enable_thinking"])
        self.assertFalse(body["stream"])
        self.assertEqual(body["max_completion_tokens"], 1024)
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("extra_body", body)
        self.assertNotIn("thinking_budget", body)

    def test_thinking_preserves_reference_total_limit(self):
        with patch.object(settings, "user_sim_enable_thinking", True):
            bailian.call_bailian([])
        body = json.loads(self.requests[0].content)
        self.assertTrue(body["enable_thinking"])
        self.assertNotIn("thinking_budget", body)
        self.assertEqual(body["max_completion_tokens"], 1024)

    def test_all_account_models_use_bailian_and_fixed_budgets(self):
        for model in bailian.BAILIAN_MODELS:
            with self.subTest(model=model), patch.object(settings, "user_sim_model", model):
                self.assertTrue(bailian.is_bailian_simulator(model))
                self.assertEqual(server._call_llm("question", 200), "Weather conditions.")
                body = json.loads(self.requests[-1].content)
                self.assertEqual(body["model"], model)
                self.assertEqual(body.get("max_completion_tokens", body.get("max_tokens")), 200)
                self.assertNotIn("reasoning_effort", body)
                self.assertNotIn("thinking_budget", body)
                if model == "qwen-max":
                    self.assertNotIn("enable_thinking", body)
                else:
                    self.assertEqual(body["enable_thinking"], model in bailian.THINKING_ONLY_MODELS)
        self.assertFalse(bailian.is_bailian_simulator("deepseek/deepseek-flash"))
        self.assertFalse(bailian.is_bailian_simulator("moonshot/kimi-k3"))

    def test_missing_key_never_falls_back(self):
        with patch.object(settings, "user_sim_api_key", ""), self.assertRaisesRegex(ValueError, "USER_SIM_API_KEY"):
            bailian.call_bailian([{"role": "user", "content": "question"}])
        self.assertEqual(self.requests, [])

    def test_finish_reason_does_not_discard_reference_content(self):
        for finish, content in [("length", "partial"), ("stop", ""), ("content_filter", "partial")]:
            with self.subTest(finish=finish, content=content):
                self.response["choices"][0].update(finish_reason=finish, message={
                    "content": content, "reasoning_content": "not an answer"})
                self.assertEqual(bailian.call_bailian([]), content.strip())
        self.response["choices"][0]["message"]["content"] = None
        self.assertEqual(server._call_llm("question"), "")
        self.response = {"choices": []}
        with self.assertRaisesRegex(ValueError, "no choices"):
            bailian.call_bailian([])

    def test_http_failure_surfaces_without_retry_or_fallback(self):
        self.status = 401
        self.response = {"error": {"message": "invalid key"}}
        with self.assertRaises(httpx.HTTPStatusError):
            bailian.call_bailian([])
        self.assertEqual(len(self.requests), 1)

    def test_qwen_uses_two_original_stages(self):
        state = object()
        with patch.object(server, "_parse_action", return_value="action") as parse, \
             patch.object(server, "_generate_response", return_value="two-stage") as generate:
            self.assertEqual(server._ask_sync(state, "q"), "two-stage")
            parse.assert_called_once_with(state, "q")
            generate.assert_called_once_with(state, "q", "action")
        with patch.object(settings, "user_sim_model", "moonshot/kimi-k2.6"), \
             patch("shared.llm.call_llm", return_value="legacy answer") as legacy:
            self.assertEqual(server._call_llm("q"), "legacy answer")
            self.assertNotIn("reasoning_effort", legacy.call_args.kwargs)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
