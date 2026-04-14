"""Gemini embedding helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request

from app.config import get_settings
from app.core.embeddings import DenseEmbedding, EmbeddingError, EmbeddingPurpose
from app.core.provider_retry import run_with_retries


class GeminiEmbeddingError(EmbeddingError):
    """Raised when the Gemini embedding backend cannot return vectors."""


_GEMINI_TASK_TYPE_BY_PURPOSE: dict[EmbeddingPurpose, str] = {
    "document": "RETRIEVAL_DOCUMENT",
    "query": "RETRIEVAL_QUERY",
    "generic": "SEMANTIC_SIMILARITY",
}


async def _embed_one(text: str, *, purpose: EmbeddingPurpose) -> DenseEmbedding:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiEmbeddingError("GEMINI_API_KEY is not configured.")

    model_name = settings.gemini_embedding_model
    encoded_model = urllib.parse.quote(model_name, safe="/")
    base_url = str(settings.gemini_base_url).rstrip("/")
    url = f"{base_url}/{encoded_model}:embedContent?key={urllib.parse.quote(settings.gemini_api_key, safe='')}"

    request_payload = {
        "model": model_name,
        "content": {
            "parts": [{"text": text}],
        },
        "taskType": _GEMINI_TASK_TYPE_BY_PURPOSE[purpose],
        "outputDimensionality": settings.dense_embedding_dimensions,
    }
    request = urllib.request.Request(
        url=url,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    def _perform_request() -> str:
        with urllib.request.urlopen(
            request,
            timeout=settings.openai_timeout_seconds,
        ) as response:
            return response.read().decode("utf-8")

    try:
        raw_body = await run_with_retries(
            lambda: asyncio.to_thread(_perform_request),
            max_retries=settings.provider_max_retries,
            backoff_ms=settings.provider_retry_backoff_ms,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise GeminiEmbeddingError(
            f"Gemini embeddings failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GeminiEmbeddingError("Gemini embedding request failed.") from exc

    try:
        response_payload = json.loads(raw_body)
        embedding = response_payload["embedding"]["values"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GeminiEmbeddingError("Gemini embeddings returned invalid JSON.") from exc

    if not isinstance(embedding, list) or not all(isinstance(value, (int, float)) for value in embedding):
        raise GeminiEmbeddingError("Gemini embeddings returned a malformed vector.")
    if len(embedding) != settings.dense_embedding_dimensions:
        raise GeminiEmbeddingError(
            f"Embedding dimension mismatch: expected {settings.dense_embedding_dimensions}, got {len(embedding)}."
        )
    return DenseEmbedding(
        text=text,
        vector=[float(value) for value in embedding],
    )


async def embed_texts_gemini(
    texts: list[str],
    *,
    purpose: EmbeddingPurpose = "generic",
) -> list[DenseEmbedding]:
    """Embed texts with Gemini, preserving order."""

    return [await _embed_one(text, purpose=purpose) for text in texts]
