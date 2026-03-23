"""Workspace API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreateRequest(BaseModel):
    """Request used to create one workspace for the authenticated tenant."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class WorkspaceUpdateRequest(BaseModel):
    """Patch request for tenant-scoped workspace updates."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class WorkspaceResponse(BaseModel):
    """Workspace resource returned by the product-shell API."""

    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime
