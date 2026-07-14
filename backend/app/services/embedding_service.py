"""Voyage AI embedding helpers with batching and rate-limit retries.

Uses voyage-4-lite by default: cheapest Voyage 4 model with free-tier tokens,
good enough for book RAG retrieval. Switch to voyage-4 / voyage-4-large later
if retrieval quality needs a boost (same vector space within the 4 series).
"""

from __future__ import annotations

import logging

import voyageai
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "voyage-4-lite"
EMBEDDING_DIMS = 1024
MAX_BATCH_SIZE = 128  # Voyage allows up to 1000; keep batches modest


def _is_retryable(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "ratelimit" in name or "rate_limit" in name or "rate limit" in message:
        return True
    if "429" in message or "too many requests" in message:
        return True
    return False


def _client() -> voyageai.Client:
    if not settings.VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY is not configured")
    return voyageai.Client(api_key=settings.VOYAGE_API_KEY)


def _model_name() -> str:
    return settings.VOYAGE_EMBEDDING_MODEL or EMBEDDING_MODEL


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _embed_batch(client: voyageai.Client, texts: list[str]) -> list[list[float]]:
    # input_type=document: optimized for indexed corpus chunks (RAG retrieval).
    result = client.embed(
        texts,
        model=_model_name(),
        input_type="document",
        output_dimension=EMBEDDING_DIMS,
    )
    return [list(vector) for vector in result.embeddings]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in batches of up to MAX_BATCH_SIZE via Voyage AI."""
    if not texts:
        return []

    client = _client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[start : start + MAX_BATCH_SIZE]
        logger.info(
            "Embedding batch model=%s size=%s offset=%s",
            _model_name(),
            len(batch),
            start,
        )
        vectors.extend(_embed_batch(client, batch))
    return vectors
