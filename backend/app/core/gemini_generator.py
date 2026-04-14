"""Gemini grounded generation helpers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import (
    build_query_profile,
    is_exact_qa_mode,
    query_focus_hints,
)
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


def _answer_mode(profile) -> str:
    """Return the high-level answer mode for provider prompting."""

    return "exact_qa" if is_exact_qa_mode(profile) else "summary_list"


def _build_prompt(*, query_text: str, evidence_package: EvidencePackage) -> str:
    """Render a grounded instruction block for Gemini."""

    profile = build_query_profile(query_text)
    answer_mode = _answer_mode(profile)
    answer_style_instructions = _answer_style_instructions(
        query_kind=profile.query_kind,
        answer_mode=answer_mode,
    )
    evidence_sections: list[str] = []
    for item in evidence_package.items:
        rendered_text = item.text.strip()
        if answer_mode != "exact_qa" and item.section_title:
            rendered_text = f"[section: {item.section_title}]\n{rendered_text}"
        evidence_sections.append(
            "\n".join(
                [
                    f"citation_id={item.citation_id}",
                    f"chunk_id={item.chunk_id}",
                    f"text={rendered_text}",
                ]
            )
        )

    return "\n\n".join(
        [
            *(
                [
                    "You are a strict grounded answer extractor.",
                    "Use ONLY the supplied evidence.",
                    "Do not use outside knowledge.",
                    "Answer ONLY the user's actual question.",
                    "If the answer exists explicitly in the evidence, you MUST extract it directly.",
                    "If the question asks for a name, company, date, count, amount, or exact value, answer_text MUST be only that direct answer.",
                    "If the question asks for two exact values, answer_text MUST contain only those requested values in one short answer.",
                    "Do NOT summarize, generalize, or add extra facts.",
                    "Do NOT say the answer is missing if the value appears in the evidence.",
                    "Never use phrases like 'I found relevant', 'not enough structured evidence', 'based on the context', or 'The date is'.",
                    "If the answer is missing, answer_text MUST be exactly: I could not find the answer in the provided context.",
                    "If arithmetic is required, extract the needed numbers from evidence, compute internally, and return only the final result in answer_text.",
                    "You MUST follow the JSON schema exactly.",
                    "answer_text MUST be short and direct.",
                    "citation_snippets must contain short exact supporting snippets, not paraphrases.",
                    "Return strict JSON only.",
                ]
                if answer_mode == "exact_qa"
                else [
                    "You are a grounded answer writer.",
                    "Use ONLY the supplied evidence.",
                    "Do not use outside knowledge.",
                    "Answer ONLY the user's actual question.",
                    "Prefer the smallest number of chunks needed to answer correctly.",
                    "If the answer exists explicitly in the evidence, extract it directly when possible.",
                    "Do NOT copy long paragraphs or include unrelated details.",
                    "Never use phrases like 'I found relevant', 'not enough structured evidence', 'based on the context', or 'The date is'.",
                    "If the answer is missing, answer_text MUST be exactly: I could not find the answer in the provided context.",
                    "You MUST follow the JSON schema exactly.",
                    "answer_text MUST be concise.",
                    "citation_snippets must contain short exact supporting snippets, not paraphrases.",
                    "Return strict JSON only.",
                ]
            ),
            f"query={query_text}",
            f"query_kind={profile.query_kind}",
            f"answer_mode={answer_mode}",
            f"semantic_tags={','.join(sorted(profile.semantic_tags)) or 'none'}",
            f"attribute_terms={','.join(sorted(profile.attribute_terms)) or 'none'}",
            "focus_hints:",
            "\n".join(query_focus_hints(profile)) or "none",
            "answer_style:",
            "\n".join(answer_style_instructions),
            "evidence:",
            "\n\n".join(evidence_sections),
        ]
    )


def _answer_style_instructions(*, query_kind: str, answer_mode: str) -> list[str]:
    """Return short answer-shape instructions tuned to the query kind."""

    if answer_mode == "exact_qa":
        if query_kind == "count":
            return [
                "Return only the count or the count plus unit when the unit is explicit.",
                "Do not explain.",
            ]
        if query_kind == "lookup":
            return [
                "Return only the requested field or exact value.",
                "Use the minimum number of evidence chunks needed.",
            ]
        return [
            "Return only the exact answer supported by the evidence.",
        ]

    if query_kind == "summary":
        return [
            "Write a concise 1-2 sentence summary of what the dataset or document is about.",
            "Prefer the document title, subject, and major sections over generic headings like Introduction or References.",
            "Do not dump raw chunk text.",
        ]
    if query_kind == "list":
        return [
            "Return only the relevant items, methods, tools, features, requirements, or skills.",
            "Prefer short structured items over long paragraphs.",
            "Do not include generic section labels as answer items.",
        ]
    if query_kind == "action":
        return [
            "State the concrete responsibilities, contributions, or actions supported by the evidence.",
            "If the evidence supports a role or company, include that briefly and then the actions.",
        ]
    if query_kind in {"boolean", "comparison", "entity"}:
        return [
            "Start with Yes. or No. when the evidence clearly supports it.",
            "Then give one brief grounded explanation using only the cited evidence.",
            "If arithmetic is needed to answer the comparison, compute it using only the supplied evidence.",
        ]
    if query_kind == "count":
        return [
            "Return only the count or the count plus unit when the unit is explicit.",
            "Do not explain.",
            "Do not say you cannot count when an explicit numeric value appears in the evidence.",
        ]
    if query_kind == "definition":
        return [
            "Only answer if the evidence explicitly defines or explains the concept.",
        ]
    if query_kind == "lookup":
        return [
            "Return only the requested field or exact value.",
            "Do not add extra details.",
        ]
    return [
        "Answer concisely and stay strictly within the cited evidence.",
    ]


def _generation_config_for_mode(answer_mode: str) -> dict[str, object]:
    """Return deterministic generation settings for the requested answer mode."""

    if answer_mode == "exact_qa":
        return {
            "temperature": 0,
            "topP": 0.05,
            "topK": 1,
            "maxOutputTokens": 120,
        }
    return {
        "temperature": 0.2,
        "topP": 0.8,
        "topK": 20,
        "maxOutputTokens": 256,
    }


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
    profile = build_query_profile(query_text)
    answer_mode = _answer_mode(profile)

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
            **_generation_config_for_mode(answer_mode),
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
