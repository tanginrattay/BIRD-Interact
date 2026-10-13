"""Unified LLM call interface.

Release: uses LiteLlm (supports any provider).
Local override: place _local_provider.py in this directory (gitignored)
to use a custom backend.
"""

import logging

from shared.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


def _transport_kwargs(model_name: str) -> dict:
    """Keep DeepSeek on its official endpoint with its own credentials."""
    if model_name.startswith("deepseek/"):
        if not settings.deepseek_api_key.strip():
            raise ValueError("DEEPSEEK_API_KEY is empty; fill it in .env before running the agent")
        return {
            "api_base": settings.deepseek_api_base,
            "api_key": settings.deepseek_api_key,
            # ADK's conversation history does not preserve reasoning_content.
            # DeepSeek requires that field for tool loops in thinking mode.
            "extra_body": {"thinking": {"type": "disabled"}},
        }
    kwargs = {}
    if settings.litellm_api_base:
        kwargs["api_base"] = settings.litellm_api_base
    if settings.litellm_api_key:
        kwargs["api_key"] = settings.litellm_api_key
    return kwargs


# Try local override first (gitignored, not in release)
try:
    from shared._local_provider import call_llm, build_adk_model
except ImportError:
    # Default: LiteLlm
    def call_llm(messages: list, model_name: str = None, temperature: float = 0,
                 max_tokens: int = 1024, reasoning_effort: str = None) -> str:
        """Call LLM via LiteLlm. Retries on rate limit / transient errors."""
        import litellm
        model_name = model_name or settings.system_agent_model
        kwargs = dict(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            num_retries=MAX_RETRIES,
        )
        kwargs.update(_transport_kwargs(model_name))
        # K3 defaults to max server-side; keep its default cost bounded.
        # Preserve explicit overrides and other models' existing behavior.
        if reasoning_effort is None and model_name.split("/")[-1] == "kimi-k3":
            reasoning_effort = "low"
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        resp = litellm.completion(**kwargs)
        return resp.choices[0].message.content.strip()

    def build_adk_model(model_name: str = None):
        """Build ADK-compatible model via LiteLlm with retry config."""
        from google.adk.models.lite_llm import LiteLlm
        model_name = model_name or settings.system_agent_model
        kwargs = dict(
            model=model_name,
            max_tokens=4096,
            num_retries=MAX_RETRIES,
        )
        if model_name.split("/")[-1] == "kimi-k3":
            kwargs["reasoning_effort"] = "low"
        kwargs.update(_transport_kwargs(model_name))
        return LiteLlm(**kwargs)
