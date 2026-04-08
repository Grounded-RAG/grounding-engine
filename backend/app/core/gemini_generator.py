"""Gemini grounded generation helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import build_query_profile, query_focus_hints
from app.pipeline.contracts import EvidencePackage, GroundedAnswerDraft
from app.core.provider_retry import run_with_retries


class GeminiGenerationError(RuntimeError):
    """Raised when the Gemini generation backend cannot return a draft."""


@dataclass(frozen=True)
class GeminiResult:
    """Parsed grounded result returned by Gemini."""

    answer_text: str
    cited_evidence_ids: list[str]
    citation_snippets: dict[str, str]


def _build_schema() -> dict[str, object]:
    """Return the structured JSON schema expected from Gemini."""

    return {
        "type": "OBJECT",
        "properties": {
            "answer_text": {"type": "STRING"},
            "cited_evidence_ids": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "citation_snippets": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "chunk_id": {"type": "STRING"},
                        "snippet": {"type": "STRING"},
                    },
                    "required": ["chunk_id", "snippet"],
                },
            },
        },
        "required": [
            "answer_text",
            "cited_evidence_ids",
            "citation_snippets",
        ],
    }


def _build_prompt(*, query_text: str, evidence_package: EvidencePackage) -> str:
    """Render a grounded instruction block for Gemini."""

    profile = build_query_profile(query_text)
    evidence_sections: list[str] = []
    for item in evidence_package.items:
        evidence_sections.append(
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
            "You are a grounded answer generator.",
            "Use only the supplied evidence.",
            "Do not use outside knowledge.",
            "Answer only the user's actual question, not every retrieved fact.",
            "Prefer the single chunk or small set of chunks that directly answer the question.",
            "If the question asks for a specific field like a name, degree, skill set, role, company, email, or date, extract only that field.",
            "Do not concatenate unrelated bullets just because they were retrieved.",
            "If support is weak, say that briefly but still remain grounded.",
            "Return JSON with keys: answer_text, cited_evidence_ids, citation_snippets.",
            "citation_snippets must be an array of objects with keys: chunk_id and snippet.",
            "Return strict JSON only.",
            f"query={query_text}",
            f"query_kind={profile.query_kind}",
            f"semantic_tags={','.join(sorted(profile.semantic_tags)) or 'none'}",
            f"attribute_terms={','.join(sorted(profile.attribute_terms)) or 'none'}",
            "focus_hints:",
            "\n".join(query_focus_hints(profile)) or "none",
            "evidence:",
            "\n\n".join(evidence_sections),
        ]
    )


def _extract_text_from_candidate(payload: dict[str, object]) -> str:
    """Extract plain text content from the first Gemini candidate."""

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiGenerationError("Gemini returned no candidates.")
    first = candidates[0]
    if not isinstance(first, dict):
        raise GeminiGenerationError("Gemini returned a malformed candidate.")
    content = first.get("content")
    if not isinstance(content, dict):
        raise GeminiGenerationError("Gemini returned no candidate content.")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GeminiGenerationError("Gemini returned no content parts.")

    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"].strip())
    rendered = "\n".join(text for text in texts if text)
    if not rendered:
        raise GeminiGenerationError("Gemini returned empty text content.")
    return rendered


def _parse_result(payload: dict[str, object]) -> GeminiResult:
    """Validate Gemini JSON output into the internal grounded result format."""

    answer_text = str(payload.get("answer_text", "")).strip()
    if not answer_text:
        raise GeminiGenerationError("Gemini returned an empty answer_text.")

    cited_raw = payload.get("cited_evidence_ids", [])
    if not isinstance(cited_raw, list) or not all(isinstance(item, str) and item.strip() for item in cited_raw):
        raise GeminiGenerationError("Gemini returned invalid cited_evidence_ids.")

    snippets_raw = payload.get("citation_snippets", [])
    snippet_map: dict[str, str] = {}
    if isinstance(snippets_raw, dict):
        snippet_map = {
            key.strip(): value.strip()
            for key, value in snippets_raw.items()
            if isinstance(key, str)
            and key.strip()
            and isinstance(value, str)
            and value.strip()
        }
    elif isinstance(snippets_raw, list):
        for item in snippets_raw:
            if not isinstance(item, dict):
                raise GeminiGenerationError("Gemini returned invalid citation_snippets.")
            chunk_id = item.get("chunk_id")
            snippet = item.get("snippet")
            if not (
                isinstance(chunk_id, str)
                and chunk_id.strip()
                and isinstance(snippet, str)
                and snippet.strip()
            ):
                raise GeminiGenerationError("Gemini returned invalid citation_snippets.")
            snippet_map[chunk_id.strip()] = snippet.strip()
    else:
        raise GeminiGenerationError("Gemini returned invalid citation_snippets.")

    if not snippet_map:
        raise GeminiGenerationError("Gemini returned invalid citation_snippets.")

    return GeminiResult(
        answer_text=answer_text,
        cited_evidence_ids=[item.strip() for item in cited_raw],
        citation_snippets=snippet_map,
    )


async def generate_gemini_draft(
    *,
    query_text: str,
    evidence_package: EvidencePackage,
) -> GroundedAnswerDraft:
    """Generate a grounded draft using the Gemini API."""

    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiGenerationError("GEMINI_API_KEY is not configured.")

    model_name = settings.gemini_model
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"
    encoded_model = urllib.parse.quote(model_name, safe="/")
    base_url = str(settings.gemini_base_url).rstrip("/")
    url = f"{base_url}/{encoded_model}:generateContent?key={urllib.parse.quote(settings.gemini_api_key, safe='')}"

    request_payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": _build_prompt(
                            query_text=query_text,
                            evidence_package=evidence_package,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _build_schema(),
        },
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
        raise GeminiGenerationError(
            f"Gemini generation failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GeminiGenerationError("Gemini generation request failed.") from exc

    try:
        response_payload = json.loads(raw_body)
        content_text = _extract_text_from_candidate(response_payload)
        parsed = _parse_result(json.loads(content_text))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GeminiGenerationError("Gemini generation returned invalid JSON.") from exc

    used_items = [
        item for item in evidence_package.items if item.chunk_id in set(parsed.cited_evidence_ids)
    ]
    support_coverage = min(len(used_items) / max(len(evidence_package.items), 1), 1.0)
    source_diversity = len({source for item in used_items for source in item.sources})

    return GroundedAnswerDraft(
        answer_text=parsed.answer_text,
        cited_evidence_ids=parsed.cited_evidence_ids,
        citation_snippets=parsed.citation_snippets,
        generator_provider=f"gemini:{settings.gemini_model}",
        support_coverage=round(support_coverage, 4),
        source_diversity=source_diversity,
    )
