"""Extended unit tests for the external fallback service.

Covers:
- source_class disclosure present in every result
- real retrieval path (mocked httpx) returns snippets and labels them correctly
- fallback gracefully degrades when HTTP call fails
- fallback uses the correct allowlisted provider name
- result is non-silent: provider_fallback_used is always True when used
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.query import CitationResponse, GroundedAnswerResponse
from app.services.external_fallback import (
    _ALLOWLISTED_SOURCE_PROVIDERS,
    resolve_external_fallback_policy,
    run_allowlisted_external_fallback,
)


def _degraded_response() -> GroundedAnswerResponse:
    doc_id = uuid.uuid4()
    return GroundedAnswerResponse(
        answer="Internal evidence was insufficient.",
        citations=[
            CitationResponse(
                citation_id="E001",
                chunk_id="chunk-1",
                document_id=doc_id,
                chunk_index=0,
                quote="stub",
            )
        ],
        confidence_score=0.2,
        confidence_label="low",
        support_summary="insufficient",
        verification_status="degraded",
        degraded_reasons=["UNSUPPORTED_CLAIMS"],
        generator_provider="local-grounded-v1",
        provider_backend="local_grounded_v1",
        provider_model=None,
        provider_fallback_used=False,
        provider_fallback_from=None,
    )


def _allowed_namespace():
    return type("NS", (), {"allow_web_fallback": True})()


def _blocked_namespace():
    return type("NS", (), {"allow_web_fallback": False})()


# ---------------------------------------------------------------------------
# Policy gate
# ---------------------------------------------------------------------------

def test_policy_disabled_returns_not_attempted() -> None:
    result = resolve_external_fallback_policy(namespace=_blocked_namespace())
    assert result.allowed is False
    assert result.reason == "policy_disabled"
    assert result.attempted is False


def test_policy_enabled_returns_allowed() -> None:
    result = resolve_external_fallback_policy(namespace=_allowed_namespace())
    assert result.allowed is True
    assert result.reason == "allowlisted_policy_enabled"


# ---------------------------------------------------------------------------
# Source class disclosure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_source_class_disclosed_when_policy_blocked() -> None:
    """Even when blocked, result must carry sources_consulted=() (no silent browse)."""
    result = await run_allowlisted_external_fallback(
        namespace=_blocked_namespace(),
        degraded_response=_degraded_response(),
        query_text="test query",
    )
    assert result.attempted is False
    assert result.sources_consulted == ()


@pytest.mark.asyncio
async def test_source_class_disclosed_in_result_when_used() -> None:
    """sources_consulted must contain the allowlisted provider name when used."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "AbstractText": "DuckDuckGo says the answer is here.",
        "RelatedTopics": [],
    }
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.external_fallback.httpx.AsyncClient", return_value=mock_client):
        result = await run_allowlisted_external_fallback(
            namespace=_allowed_namespace(),
            degraded_response=_degraded_response(),
            query_text="what is grounded",
        )

    assert result.attempted is True
    assert result.used is True
    assert len(result.sources_consulted) > 0
    assert result.sources_consulted[0] in _ALLOWLISTED_SOURCE_PROVIDERS
    assert result.response is not None
    assert result.response.provider_fallback_used is True
    assert result.response.provider_backend in _ALLOWLISTED_SOURCE_PROVIDERS
    assert "[External source:" in result.response.answer


@pytest.mark.asyncio
async def test_source_class_disclosed_even_when_no_snippets() -> None:
    """When HTTP call returns no snippets, result must still disclose the attempt."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.json.return_value = {"AbstractText": "", "RelatedTopics": []}
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.external_fallback.httpx.AsyncClient", return_value=mock_client):
        result = await run_allowlisted_external_fallback(
            namespace=_allowed_namespace(),
            degraded_response=_degraded_response(),
            query_text="obscure query",
        )

    assert result.attempted is True
    assert result.used is False
    assert result.reason == "allowlisted_external_fallback_no_snippets"
    assert result.sources_consulted == (_ALLOWLISTED_SOURCE_PROVIDERS[0],)


@pytest.mark.asyncio
async def test_graceful_degradation_on_http_failure() -> None:
    """When the HTTP call raises an exception, fallback must not propagate the error."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))

    with patch("app.services.external_fallback.httpx.AsyncClient", return_value=mock_client):
        result = await run_allowlisted_external_fallback(
            namespace=_allowed_namespace(),
            degraded_response=_degraded_response(),
            query_text="query that fails",
        )

    assert result.attempted is True
    assert result.used is False
    # No snippets retrieved due to network failure — must degrade cleanly.
    assert result.reason in {
        "allowlisted_external_fallback_no_snippets",
        "allowlisted_external_snippets_retrieved",
    }


@pytest.mark.asyncio
async def test_empty_query_text_does_not_call_http() -> None:
    """When query_text is empty, no HTTP call should be made."""
    with patch("app.services.external_fallback._fetch_duckduckgo_snippets") as mock_fetch:
        mock_fetch.return_value = []
        result = await run_allowlisted_external_fallback(
            namespace=_allowed_namespace(),
            degraded_response=_degraded_response(),
            query_text="",
        )
    mock_fetch.assert_not_called()
    assert result.attempted is True
    assert result.used is False


@pytest.mark.asyncio
async def test_provider_fallback_from_preserves_original_provider() -> None:
    """provider_fallback_from must carry the original provider name."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "AbstractText": "Some answer from external.",
        "RelatedTopics": [],
    }
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    degraded = _degraded_response()
    with patch("app.services.external_fallback.httpx.AsyncClient", return_value=mock_client):
        result = await run_allowlisted_external_fallback(
            namespace=_allowed_namespace(),
            degraded_response=degraded,
            query_text="test",
        )

    assert result.response is not None
    assert result.response.provider_fallback_from == degraded.generator_provider
