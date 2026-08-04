"""OpenAI-compatible chat helper that returns parsed JSON."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import settings

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def parse_json_content(content: str) -> Any:
    text = content.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def chat_json(system: str, user: str) -> Any:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.3,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL

    llm = ChatOpenAI(**kwargs)
    result = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = result.content if isinstance(result.content, str) else str(result.content)
    return parse_json_content(content)


async def chat_stream_text(*, system: str, user: str) -> AsyncIterator[str]:
    """Yield text chunks from ChatOpenAI.astream."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.5,
        "streaming": True,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL

    llm = ChatOpenAI(**kwargs)
    async for chunk in llm.astream(
        [SystemMessage(content=system), HumanMessage(content=user)]
    ):
        text = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
        if text:
            yield text
