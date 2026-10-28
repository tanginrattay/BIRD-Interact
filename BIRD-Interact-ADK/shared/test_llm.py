"""Offline checks: no API requests or credentials are used by the mocked clients."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from shared.llm import build_adk_model, call_llm
from shared.config import settings


class ReasoningConfigTests(unittest.TestCase):
    def test_bailian_agent_uses_bailian_endpoint_and_key(self):
        with patch.object(settings, "user_sim_api_key", "test-bailian-key"), \
             patch.object(settings, "user_sim_api_base", "https://bailian.example/v1"), \
             patch("google.adk.models.lite_llm.LiteLlm") as model:
            build_adk_model("openai/deepseek-v4.1-flash-1017")
        kwargs = model.call_args.kwargs
        self.assertEqual(kwargs["api_base"], "https://bailian.example/v1")
        self.assertEqual(kwargs["api_key"], "test-bailian-key")
        self.assertEqual(kwargs["extra_body"], {"enable_thinking": False})
        self.assertEqual(kwargs["max_tokens"], 4096)

    def test_deepseek_transport_is_independent_and_non_thinking(self):
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
        with patch.object(settings, "deepseek_api_key", "test-deepseek-key"), \
             patch.object(settings, "litellm_api_base", "https://proxy.example"), \
             patch.object(settings, "litellm_api_key", "test-proxy-key"), \
             patch("google.adk.models.lite_llm.LiteLlm") as model, \
             patch("litellm.completion", return_value=response) as completion:
            for name in ("deepseek/deepseek-flash", "deepseek/deepseek-v4-flash"):
                build_adk_model(name)
                self.assertEqual(call_llm([], model_name=name), "ok")
                for kwargs in (model.call_args.kwargs, completion.call_args.kwargs):
                    self.assertEqual(kwargs["model"], name)
                    self.assertEqual(kwargs["api_base"], "https://api.deepseek.com")
                    self.assertEqual(kwargs["api_key"], "test-deepseek-key")
                    self.assertEqual(kwargs["extra_body"], {"thinking": {"type": "disabled"}})
                    self.assertNotIn("reasoning_effort", kwargs)
                self.assertEqual(model.call_args.kwargs["max_tokens"], 4096)

    def test_deepseek_empty_key_fails_before_request(self):
        with patch.object(settings, "deepseek_api_key", ""), \
             patch("google.adk.models.lite_llm.LiteLlm") as model, \
             patch("litellm.completion") as completion:
            for call in (build_adk_model, lambda name: call_llm([], model_name=name)):
                with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                    call("deepseek/deepseek-flash")
            model.assert_not_called()
            completion.assert_not_called()

    def test_adk_k3_low_only(self):
        with patch("google.adk.models.lite_llm.LiteLlm") as model:
            for name in ("moonshot/kimi-k3", "openai/kimi-k3", "kimi-k3"):
                build_adk_model(name)
                self.assertEqual(model.call_args.kwargs["reasoning_effort"], "low")
                self.assertEqual(model.call_args.kwargs["max_tokens"], 4096)
            for name in ("moonshot/kimi-k2.6", "anthropic/claude-sonnet-4-20250514"):
                build_adk_model(name)
                self.assertNotIn("reasoning_effort", model.call_args.kwargs)

    def test_direct_defaults_and_explicit_override(self):
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
        with patch("litellm.completion", return_value=response) as completion:
            call_llm([], model_name="moonshot/kimi-k3")
            self.assertEqual(completion.call_args.kwargs["reasoning_effort"], "low")
            call_llm([], model_name="moonshot/kimi-k3", reasoning_effort="high")
            self.assertEqual(completion.call_args.kwargs["reasoning_effort"], "high")
            call_llm([], model_name="moonshot/kimi-k2.6", reasoning_effort="none")
            self.assertEqual(completion.call_args.kwargs["reasoning_effort"], "none")
            call_llm([], model_name="moonshot/kimi-k2.6")
            self.assertNotIn("reasoning_effort", completion.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
