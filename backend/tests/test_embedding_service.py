"""Unit tests for Voyage embedding service (mocked client — no real API)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services import embedding_service


def test_embed_texts_requires_voyage_api_key(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "VOYAGE_API_KEY", None)
    with pytest.raises(RuntimeError, match="VOYAGE_API_KEY"):
        embedding_service.embed_texts(["hello"])


def test_embed_texts_batches_and_uses_document_input_type(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "VOYAGE_API_KEY", "pa-test")
    monkeypatch.setattr(embedding_service.settings, "VOYAGE_EMBEDDING_MODEL", "voyage-4-lite")

    fake_client = MagicMock()
    fake_client.embed.return_value = MagicMock(embeddings=[[0.1, 0.2], [0.3, 0.4]])

    with patch.object(embedding_service, "_client", return_value=fake_client):
        vectors = embedding_service.embed_texts(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    fake_client.embed.assert_called_once()
    kwargs = fake_client.embed.call_args.kwargs
    assert kwargs["model"] == "voyage-4-lite"
    assert kwargs["input_type"] == "document"
    assert kwargs["output_dimension"] == 1024


def test_embed_texts_empty_returns_empty(monkeypatch):
    monkeypatch.setattr(embedding_service.settings, "VOYAGE_API_KEY", "pa-test")
    assert embedding_service.embed_texts([]) == []
