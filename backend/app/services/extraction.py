"""Text extraction and metadata enrichment helpers for ingestion."""

from __future__ import annotations

import io
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Final
from uuid import UUID

from docx import Document as DocxDocument
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.storage import StorageError, download_fileobj, upload_bytes
from app.models import Document
from app.services.ingestion import IngestionJobContext, IngestionProcessorError


_PDF_CREATION_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^D:(?P<year>\d{4})(?P<month>\d{2})?(?P<day>\d{2})?"
    r"(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?"
)


@dataclass(frozen=True)
class ExtractedDocument:
    """Normalized extraction result and safe metadata for downstream stages."""

    artifact_key: str
    text: str
    title: str | None
    published_at: datetime | None
    mime_type: str
    character_count: int


def _normalize_text(text: str) -> str:
    """Normalize extracted text into a stable UTF-8 friendly form."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized_lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(normalized_lines).strip()


def _parse_pdf_creation_date(raw_value: str | None) -> datetime | None:
    """Parse a PDF creation date if metadata includes one."""

    if raw_value is None:
        return None
    match = _PDF_CREATION_DATE_PATTERN.match(raw_value.strip())
    if match is None:
        return None

    parts = match.groupdict(default="01")
    try:
        return datetime(
            int(parts["year"]),
            int(parts["month"]),
            int(parts["day"]),
            int(parts["hour"] if parts["hour"] != "01" else "0"),
            int(parts["minute"] if parts["minute"] != "01" else "0"),
            int(parts["second"] if parts["second"] != "01" else "0"),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def _extract_text_from_txt(fileobj: BinaryIO) -> tuple[str, str | None, datetime | None]:
    """Extract normalized text from a UTF-8 text file."""

    return fileobj.read().decode("utf-8"), None, None


def _extract_text_from_pdf(fileobj: BinaryIO) -> tuple[str, str | None, datetime | None]:
    """Extract text and lightweight metadata from a PDF payload."""

    reader = PdfReader(fileobj)
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    metadata = reader.metadata or {}
    title = None
    if metadata.get("/Title"):
        title = str(metadata["/Title"]).strip() or None
    published_at = _parse_pdf_creation_date(metadata.get("/CreationDate"))
    return text, title, published_at


def _extract_text_from_docx(fileobj: BinaryIO) -> tuple[str, str | None, datetime | None]:
    """Extract text and lightweight metadata from a DOCX payload."""

    document = DocxDocument(fileobj)
    text = "\n\n".join(
        paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
    )

    raw_title = document.core_properties.title
    title = None
    if raw_title is not None:
        title = raw_title.strip() or None
    published_at = document.core_properties.created
    if published_at is not None and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    return text, title, published_at


def extract_text_from_file(
    fileobj: BinaryIO,
    *,
    mime_type: str,
) -> tuple[str, str | None, datetime | None]:
    """Extract text and optional metadata from a supported payload."""

    if mime_type == "text/plain":
        return _extract_text_from_txt(fileobj)
    if mime_type == "application/pdf":
        return _extract_text_from_pdf(fileobj)
    if (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _extract_text_from_docx(fileobj)

    raise IngestionProcessorError(
        "UNSUPPORTED_EXTRACTION_MIME_TYPE",
        f"Unsupported document mime type for extraction: {mime_type}.",
    )


def derive_extracted_text_key(object_key: str) -> str:
    """Derive the storage key used for normalized extracted text."""

    if "/source/" in object_key:
        prefix, _ = object_key.split("/source/", maxsplit=1)
        return f"{prefix}/artifacts/extracted/text.txt"
    return f"{object_key}.extracted.txt"


def _filename_stem_from_object_key(object_key: str) -> str:
    """Return the filename stem encoded in the source object key."""

    return Path(object_key).stem.strip()


def _resolve_enriched_title(
    *,
    current_title: str | None,
    candidate_title: str | None,
    object_key: str,
) -> str | None:
    """Decide whether extraction metadata should replace the stored title."""

    normalized_candidate = (candidate_title or "").strip()
    if not normalized_candidate:
        return current_title

    normalized_current = (current_title or "").strip()
    filename_stem = _filename_stem_from_object_key(object_key)
    if not normalized_current or normalized_current in {
        "Untitled document",
        filename_stem,
    }:
        return normalized_candidate
    return current_title


async def extract_document_artifact(
    context: IngestionJobContext,
) -> ExtractedDocument:
    """Extract normalized text from the source object and write a derived artifact."""

    with tempfile.TemporaryFile() as tmp_file:
        try:
            await download_fileobj(context.object_key, tmp_file)
        except StorageError as exc:
            raise IngestionProcessorError(
                "SOURCE_DOWNLOAD_FAILED",
                "Failed to stream uploaded source file from storage.",
            ) from exc

        tmp_file.seek(0)
        try:
            extracted_text, extracted_title, published_at = await run_in_threadpool(
                extract_text_from_file,
                tmp_file,
                mime_type=context.mime_type,
            )
        except UnicodeDecodeError as exc:
            raise IngestionProcessorError(
                "TEXT_DECODE_FAILED",
                "Failed to decode the uploaded text document as UTF-8.",
            ) from exc

    normalized_text = _normalize_text(extracted_text)
    if not normalized_text:
        raise IngestionProcessorError(
            "EMPTY_EXTRACTION",
            "Document extraction produced no usable text.",
        )

    artifact_key = derive_extracted_text_key(context.object_key)
    try:
        await upload_bytes(
            artifact_key,
            normalized_text.encode("utf-8"),
            content_type="text/plain",
            metadata={
                "tenant_id": str(context.tenant_id),
                "document_id": str(context.document_id),
                "source_object_key": context.object_key,
                "mime_type": context.mime_type,
            },
        )
    except StorageError as exc:
        raise IngestionProcessorError(
            "EXTRACTION_ARTIFACT_UPLOAD_FAILED",
            "Failed to store normalized extracted text.",
        ) from exc

    return ExtractedDocument(
        artifact_key=artifact_key,
        text=normalized_text,
        title=_resolve_enriched_title(
            current_title=context.title,
            candidate_title=extracted_title,
            object_key=context.object_key,
        ),
        published_at=published_at,
        mime_type=context.mime_type,
        character_count=len(normalized_text),
    )


async def persist_enriched_document_metadata(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    extracted_document: ExtractedDocument,
) -> Document:
    """Persist metadata learned during extraction onto the document record."""

    statement = select(Document).where(
        Document.tenant_id == tenant_id,
        Document.doc_id == document_id,
    )
    result = await session.execute(statement)
    document = result.scalar_one_or_none()
    if document is None:
        raise IngestionProcessorError(
            "DOCUMENT_NOT_FOUND",
            "Document record could not be loaded for metadata enrichment.",
        )

    if extracted_document.title is not None:
        document.title = extracted_document.title
    if document.published_at is None and extracted_document.published_at is not None:
        document.published_at = extracted_document.published_at

    await session.commit()
    await session.refresh(document)
    return document
