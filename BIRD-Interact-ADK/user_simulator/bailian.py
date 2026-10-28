"""Simulator transport using Bailian's OpenAI-compatible HTTP API.

Kept independent of shared.llm to isolate endpoints, credentials and Qwen-only
parameters from the system agent. No SDK or new dependency is required.
"""

import logging

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)

# Account model IDs supplied by the user. No provider endpoint is inferred.
BAILIAN_MODELS = (
    "deepseek-v4-pro-0813", "deepseek-v4-flash-0731", "deepseek-v4-pro",
    "deepseek-v4.1-flash", "deepseek-v4.1-flash-1017", "glm-5", "glm-5.1", "glm-5.2", "glm-5.3",
    "kimi-k2.7-code", "kimi-k3", "kimi-k2.5", "kimi-k2.6",
    "qwen3.5-122b-a10b", "qwen3.7-plus", "qwen3.5-plus-2026-02-15",
    "qwen-max", "qwen3.7-max-2026-06-08",
)
THINKING_ONLY_MODELS = {"glm-5.3", "kimi-k3", "kimi-k2.7-code"}


def is_bailian_simulator(model: str) -> bool:
    return model in BAILIAN_MODELS or is_qwen_simulator(model)


def is_qwen_simulator(model: str) -> bool:
    name = model.rsplit("/", 1)[-1]
    return name == "qwen3.7-plus" or name.startswith("qwen3.7-plus-")


def call_bailian(messages: list, max_tokens: int = 1024) -> str:
    """Return final content only; never substitute reasoning or a canned answer."""
    if not settings.user_sim_api_key.strip():
        raise ValueError("Set USER_SIM_API_KEY in .env before calling the Qwen simulator")
    if not settings.user_sim_api_base.strip():
        raise ValueError("USER_SIM_API_BASE must point to Bailian's compatible-mode/v1 endpoint")
    payload = build_payload(messages, settings.user_sim_model, max_tokens,
                            settings.user_sim_enable_thinking)
    with httpx.Client(timeout=90.0) as client:
        response = client.post(
            settings.user_sim_api_base.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + settings.user_sim_api_key.strip()},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices")
    if not choices:
        raise ValueError("Bailian simulator response has no choices")
    choice = choices[0]
    finish = choice.get("finish_reason")
    usage = data.get("usage") or {}
    logger.info(
        "Bailian simulator model=%s finish=%s prompt_tokens=%s completion_tokens=%s",
        payload["model"], finish, usage.get("prompt_tokens"), usage.get("completion_tokens"),
    )
    # Match the reference wrapper: finish_reason is diagnostic only.
    content = (choice.get("message") or {}).get("content")
    return content.strip()


def build_payload(messages: list, model: str, max_tokens: int,
                  requested_thinking: bool = False) -> dict:
    """Adapt parameters, preserving the original stage's total output limit.

    Legacy Qwen models accept max_tokens. Modern cloud-hosted families accept
    max_completion_tokens (reasoning plus content). Thinking-only models cannot
    share a non-thinking setting; their unavoidable reasoning is recorded.
    """
    name = model.rsplit("/", 1)[-1]
    thinking = requested_thinking or name in THINKING_ONLY_MODELS
    payload = {
        "model": name,
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    if name == "qwen-max":
        if requested_thinking:
            raise ValueError("qwen-max does not support the thinking toggle")
        payload["max_tokens"] = max_tokens
    elif name == "qwen3.5-122b-a10b":
        if requested_thinking:
            raise ValueError("This fixed-budget profile requires non-thinking Qwen3.5-122B")
        payload.update(enable_thinking=False, max_tokens=max_tokens)
    else:
        payload.update(enable_thinking=thinking, max_completion_tokens=max_tokens)
    return payload
