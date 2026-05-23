"""OpenAI-compatible grounded generation helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import build_query_profile, query_focus_hints
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft
from app.core.provider_retry import run_with_retries


class OpenAICompatibleGenerationError(RuntimeError):
    """Raised when the OpenAI-compatible generation backend cannot return a draft."""


@dataclass(frozen=True)
class OpenAICompatibleResult:
    """Parsed result from the OpenAI-compatible generation backend."""

    answer_text: str
    cited_evidence_ids: list[str]
    citation_snippets: dict[str, str]


def _build_system_prompt() -> str:
    """Return the grounded-system instructions for external generation."""

    return (
        "You are a grounded answer generator. "
        "Answer only from the supplied evidence. "
        "Do not invent claims or use outside knowledge. "
        "Answer only the user's actual question, not every retrieved fact. "
        "If the question asks for a specific field like a name, degree, skill set, role, company, email, phone, or date, extract only that field. "
        "Do not concatenate unrelated evidence. "
        "If the evidence is insufficient, return a short answer that says so. "
        "Return strict JSON with keys: answer_text, cited_evidence_ids, citation_snippets. "
        "Each cited_evidence_id must be one of the provided chunk ids. "
        "citation_snippets must map cited chunk ids to short grounded snippets from the evidence."
    )


def _build_user_prompt(*, query_text: str, evidence_package: EvidencePackage) -> str:
    """Render the grounded evidence payload for the OpenAI-compatible backend."""

    profile = build_query_profile(query_text)
    evidence_lines: list[str] = []
    for item in evidence_package.items:
        evidence_lines.append(
            "\n".join(
                [
                    f"citation_id={item.citation_id}",
                    f"chunk_id={item.chunk_id}",
                    f"document_id={item.document_id}",
                    f"chunk_index={item.chunk_index}",
                    f"sources={','.join(item.sources)}",
                    f"text={item.text}",
                ]
            )
        )

    return "\n\n".join(
        [
            f"query={query_text}",
            f"query_kind={profile.query_kind}",
            f"semantic_tags={','.join(sorted(profile.semantic_tags)) or 'none'}",
            f"attribute_terms={','.join(sorted(profile.attribute_terms)) or 'none'}",
            "focus_hints:",
            "\n".join(query_focus_hints(profile)) or "none",
            "evidence:",
            "\n\n".join(evidence_lines),
        ]
    )


def _parse_generation_payload(payload: dict[str, object]) -> OpenAICompatibleResult:
    """Validate the OpenAI-compatible JSON payload."""

    answer_text = str(payload.get("answer_text", "")).strip()
    if not answer_text:
        raise OpenAICompatibleGenerationError("Provider returned an empty answer_text.")

    cited_evidence_ids_raw = payload.get("cited_evidence_ids", [])
    if not isinstance(cited_evidence_ids_raw, list) or not all(
        isinstance(item, str) and item.strip()
        for item in cited_evidence_ids_raw
    ):
        raise OpenAICompatibleGenerationError(
            "Provider returned invalid cited_evidence_ids."
        )

    citation_snippets_raw = payload.get("citation_snippets", {})
    if not isinstance(citation_snippets_raw, dict) or not all(
        isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip()
        for key, value in citation_snippets_raw.items()
    ):
        raise OpenAICompatibleGenerationError(
            "Provider returned invalid citation_snippets."
        )

    return OpenAICompatibleResult(
        answer_text=answer_text,
        cited_evidence_ids=[item.strip() for item in cited_evidence_ids_raw],
        citation_snippets={key.strip(): value.strip() for key, value in citation_snippets_raw.items()},
    )


def _extract_message_content(response_payload: dict[str, object]) -> str:
    """Extract assistant content from the OpenAI-compatible response body."""

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenAICompatibleGenerationError("Provider returned no choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise OpenAICompatibleGenerationError("Provider returned a malformed choice.")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise OpenAICompatibleGenerationError("Provider returned no assistant message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OpenAICompatibleGenerationError("Provider returned empty message content.")
    return content


async def generate_openai_compatible_draft(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a grounded draft using an OpenAI-compatible chat-completions API."""

    settings = get_settings()
    if not settings.openai_api_key:
        raise OpenAICompatibleGenerationError("OPENAI_API_KEY is not configured.")

    request_payload = {
        "model": settings.openai_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _build_system_prompt()},
            {
                "role": "user",
                "content": _build_user_prompt(
                    query_text=query_text,
                    evidence_package=evidence_package,
                ),
            },
        ],
    }

    base_url = str(settings.openai_base_url).rstrip("/")
    request = urllib.request.Request(
        url=f"{base_url}/chat/completions",
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
        raw_body = await run_with_retries(
            lambda: asyncio.to_thread(_perform_request),
            max_retries=settings.provider_max_retries,
            backoff_ms=settings.provider_retry_backoff_ms,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise OpenAICompatibleGenerationError(
            f"OpenAI-compatible generation failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenAICompatibleGenerationError(
            "OpenAI-compatible generation request failed."
        ) from exc

    try:
        response_payload = json.loads(raw_body)
        content = _extract_message_content(response_payload)
        parsed = _parse_generation_payload(json.loads(content))
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        raise OpenAICompatibleGenerationError(
            "OpenAI-compatible generation returned invalid JSON."
        ) from exc

    used_items = [
        item
        for item in evidence_package.items
        if item.chunk_id in set(parsed.cited_evidence_ids)
    ]
    support_coverage = min(
        len(used_items) / max(len(evidence_package.items), 1),
        1.0,
    )
    source_diversity = len({source for item in used_items for source in item.sources})

    usage = response_payload.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))

    return GroundedAnswerDraft(
        answer_text=parsed.answer_text,
        cited_evidence_ids=parsed.cited_evidence_ids,
        citation_snippets=parsed.citation_snippets,
        generator_provider=f"openai-compatible:{settings.openai_model}",
        support_coverage=round(support_coverage, 4),
        source_diversity=source_diversity,
        token_usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": int(usage.get("total_tokens", prompt_tokens + completion_tokens)),
        },
    )
