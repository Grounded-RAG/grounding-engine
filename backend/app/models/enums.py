"""Shared SQLAlchemy enums for persisted domain models."""

from __future__ import annotations

from enum import Enum


class PlanTier(str, Enum):
    """Supported tenant and query tiers."""

    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    CRITICAL = "critical"


class SensitivityLevel(str, Enum):
    """Supported namespace sensitivity levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentStatus(str, Enum):
    """Document lifecycle states."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class IngestionJobStatus(str, Enum):
    """Ingestion job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    INDEXED = "indexed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
