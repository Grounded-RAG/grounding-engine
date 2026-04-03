"""OpenAI-compatible embedding helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from app.config import get_settings
from app.core.embeddings import DenseEmbedding, EmbeddingError


class OpenAICompatibleEmbeddingError(EmbeddingError):
    """Raised when the OpenAI-compatible embedding backend cannot return vectors."""


async def embed_texts_openai_compatible(texts: list[str]) -> list[DenseEmbedding]:
    """Embed a batch of texts using an OpenAI-compatible embeddings endpoint."""

    settings = get_settings()
    if not settings.openai_api_key:
        raise OpenAICompatibleEmbeddingError("OPENAI_API_KEY is not configured.")
    if not texts:
        return []

    request_payload = {
        "model": settings.openai_embedding_model,
        "input": texts,
        "dimensions": settings.dense_embedding_dimensions,
    }
    base_url = str(settings.openai_base_url).rstrip("/")
    request = urllib.request.Request(
        url=f"{base_url}/embeddings",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    def _perform_request() -> str:
        with urllib.request.urlopen(
            request,
            timeout=settings.openai_timeout_seconds,
        ) as response:
            return response.read().decode("utf-8")

    try:
        raw_body = await asyncio.to_thread(_perform_request)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise OpenAICompatibleEmbeddingError(
            f"OpenAI-compatible embeddings failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenAICompatibleEmbeddingError(
            "OpenAI-compatible embedding request failed."
        ) from exc

    try:
        response_payload = json.loads(raw_body)
        data = response_payload["data"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OpenAICompatibleEmbeddingError(
            "OpenAI-compatible embeddings returned invalid JSON."
        ) from exc

    if not isinstance(data, list) or len(data) != len(texts):
        raise OpenAICompatibleEmbeddingError(
            "OpenAI-compatible embeddings returned an unexpected number of vectors."
        )

    embeddings: list[DenseEmbedding] = []
    expected_dimensions = settings.dense_embedding_dimensions
    for item, text in zip(data, texts):
        if not isinstance(item, dict):
            raise OpenAICompatibleEmbeddingError(
                "OpenAI-compatible embeddings returned a malformed item."
            )
        vector = item.get("embedding")
        if not isinstance(vector, list) or not all(isinstance(value, (int, float)) for value in vector):
            raise OpenAICompatibleEmbeddingError(
                "OpenAI-compatible embeddings returned a malformed vector."
            )
        if len(vector) != expected_dimensions:
            raise OpenAICompatibleEmbeddingError(
                f"Embedding dimension mismatch: expected {expected_dimensions}, got {len(vector)}."
            )
        embeddings.append(
            DenseEmbedding(
                text=text,
                vector=[float(value) for value in vector],
            )
        )

    return embeddings
