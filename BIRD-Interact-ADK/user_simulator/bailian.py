"""Qwen simulator transport using Bailian's OpenAI-compatible HTTP API.

Kept independent of shared.llm to isolate endpoints, credentials and Qwen-only
parameters from the system agent. No SDK or new dependency is required.
"""

import logging

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)


def is_qwen_simulator(model: str) -> bool:
    name = model.rsplit("/", 1)[-1]
    return name == "qwen3.7-plus" or name.startswith("qwen3.7-plus-")


def call_bailian(messages: list, max_tokens: int = 1024) -> str:
    """Return final content only; never substitute reasoning or a canned answer."""
    if not settings.user_sim_api_key.strip():
        raise ValueError("Set USER_SIM_API_KEY in .env before calling the Qwen simulator")
    if not settings.user_sim_api_base.strip():
        raise ValueError("USER_SIM_API_BASE must point to Bailian's compatible-mode/v1 endpoint")
    thinking = settings.user_sim_enable_thinking
    payload = {
        "model": settings.user_sim_model.rsplit("/", 1)[-1],
        "messages": messages,
        "temperature": 0,
        "stream": False,
        "enable_thinking": thinking,
        # This parameter includes reasoning AND final output tokens.
        "max_completion_tokens": max_tokens + (
            settings.user_sim_thinking_budget if thinking else 0
        ),
    }
    if thinking:
        payload["thinking_budget"] = settings.user_sim_thinking_budget
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
    if finish != "stop":
        raise ValueError(f"Bailian simulator did not finish normally (finish_reason={finish!r})")
    content = (choice.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Bailian simulator returned empty final content")
    return content.strip()
