import asyncio
import sys
from types import SimpleNamespace

import pytest

from app.services import llm_client
from app.services.llm_client import chat_stream_text, parse_json_content


def test_parse_json_bo_fence_markdown():
    raw = '```json\n{"questions": []}\n```'
    assert parse_json_content(raw) == {"questions": []}


def test_parse_json_thuan():
    assert parse_json_content('{"a": 1}') == {"a": 1}


def test_chat_stream_text_yields_deltas(monkeypatch):
    chunks = [SimpleNamespace(content="Hello "), SimpleNamespace(content="world")]

    class FakeLLM:
        async def astream(self, messages):
            for chunk in chunks:
                yield chunk

    fake_openai = SimpleNamespace(ChatOpenAI=lambda **kwargs: FakeLLM())
    fake_messages = SimpleNamespace(
        SystemMessage=lambda content: SimpleNamespace(content=content),
        HumanMessage=lambda content: SimpleNamespace(content=content),
    )
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_openai)
    monkeypatch.setitem(sys.modules, "langchain_core.messages", fake_messages)
    monkeypatch.setattr(llm_client.settings, "OPENAI_API_KEY", "test-key")

    async def collect():
        return [token async for token in chat_stream_text(system="sys", user="usr")]

    assert asyncio.run(collect()) == ["Hello ", "world"]


def test_chat_stream_text_requires_api_key(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "OPENAI_API_KEY", "")

    async def consume():
        async for _ in chat_stream_text(system="sys", user="usr"):
            pass

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        asyncio.run(consume())
