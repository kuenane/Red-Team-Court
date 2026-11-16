"""Thin async wrapper around Qwen (DashScope compatible-mode OpenAI SDK).

Each specialist agent is conceptually a `qwen_agent.Assistant` persona
(system prompt + model config); here we call the model directly via the
OpenAI-compatible client for simplicity and to keep the parallel-async
fan-out explicit. Swap `chat_json` internals for `qwen_agent.Agent.run()`
if you need built-in tool-calling per agent later.
"""
import json
import logging
from openai import AsyncOpenAI
from ..config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Built lazily so the app can start (and tests can import it) without an API key."""
    global _client
    if _client is None:
        if not settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not set")
        _client = AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
    return _client


async def chat_json(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> dict:
    """Calls Qwen expecting a strict JSON response. Returns {"ok": bool, "data"|"error": ...}."""
    try:
        response = await get_client().chat.completions.create(
            model=settings.qwen_model,
            max_tokens=max_tokens,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        return {"ok": True, "data": json.loads(text)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Qwen call failed")
        return {"ok": False, "error": str(exc)}
