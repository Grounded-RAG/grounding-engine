"""Shared SQLAlchemy enums for persisted domain models."""

from __future__ import annotations

from enum import Enum as PythonEnum
from typing import TypeVar

from sqlalchemy import Enum as SQLAlchemyEnum


EnumType = TypeVar("EnumType", bound=PythonEnum)


def enum_values(enum_cls: type[EnumType]) -> list[str]:
    """Return stable DB values for a Python enum."""

    return [member.value for member in enum_cls]


def sqlalchemy_enum(enum_cls: type[EnumType], *, name: str) -> SQLAlchemyEnum:
    """Build a SQLAlchemy enum that persists enum values, not member names."""

    return SQLAlchemyEnum(
        enum_cls,
        name=name,
        values_callable=enum_values,
        validate_strings=True,
    )


class PlanTier(str, PythonEnum):
    """Supported tenant and query tiers."""

    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    CRITICAL = "critical"


class SensitivityLevel(str, PythonEnum):
    """Supported namespace sensitivity levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentStatus(str, PythonEnum):
    """Document lifecycle states."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class IngestionJobStatus(str, PythonEnum):
    """Ingestion job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    INDEXED = "indexed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
