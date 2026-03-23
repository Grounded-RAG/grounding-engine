"""Unit tests for text extraction helpers."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from docx import Document as DocxDocument

from app.services.extraction import (
    derive_extracted_text_key,
    extract_text_from_payload,
)


def _build_simple_pdf_bytes(text: str) -> bytes:
    """Build a minimal single-page PDF that pypdf can read back."""

    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped}) Tj\nET".encode("latin-1")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n"
        ),
        (
            b"4 0 obj\n<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    header = b"%PDF-1.4\n"
    offsets: list[int] = []
    cursor = len(header)
    body = b""
    for obj in objects:
        offsets.append(cursor)
        body += obj
        cursor += len(obj)

    xref_offset = len(header) + len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets
    )
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF\n"
    )
    return header + body + xref + trailer


def test_extract_text_from_plain_text_payload() -> None:
    """Plain text extraction should return the original decoded body."""

    text, title, published_at = extract_text_from_payload(
        b"hello grounded",
        mime_type="text/plain",
    )

    assert text == "hello grounded"
    assert title is None
    assert published_at is None


def test_extract_text_from_pdf_payload() -> None:
    """PDF extraction should read text from a simple single-page document."""

    text, title, published_at = extract_text_from_payload(
        _build_simple_pdf_bytes("Hello PDF"),
        mime_type="application/pdf",
    )

    assert "Hello PDF" in text
    assert title is None
    assert published_at is None


def test_extract_text_from_docx_payload() -> None:
    """DOCX extraction should return paragraph text and metadata."""

    document = DocxDocument()
    document.add_paragraph("Hello DOCX")
    document.core_properties.title = "DOCX Title"
    document.core_properties.created = datetime(2025, 4, 1, 12, 0, tzinfo=UTC)
    buffer = io.BytesIO()
    document.save(buffer)

    text, title, published_at = extract_text_from_payload(
        buffer.getvalue(),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert text == "Hello DOCX"
    assert title == "DOCX Title"
    assert published_at == datetime(2025, 4, 1, 12, 0, tzinfo=UTC)


def test_derive_extracted_text_key_uses_artifact_path() -> None:
    """Extraction artifacts should land under the document artifact prefix."""

    assert derive_extracted_text_key(
        "tenants/t1/namespaces/n1/documents/d1/source/manual.txt"
    ) == "tenants/t1/namespaces/n1/documents/d1/artifacts/extracted/text.txt"
