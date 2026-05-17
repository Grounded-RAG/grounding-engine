"""Schemas for product capabilities and user-facing mode availability."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ExecutionTier, SubscriptionPlan, UserFacingMode


CapabilityReason = Literal["coming_soon", "plan_restricted", "tier_restricted"]


class ModeCapabilityResponse(BaseModel):
    """One user-facing mode and whether it is currently available."""

    mode: UserFacingMode
    label: str = Field(min_length=1)
    enabled: bool
    backing_tier: ExecutionTier | None = None
    description: str = Field(min_length=1)
    availability_reason: CapabilityReason | None = None


class FeatureCapabilityResponse(BaseModel):
    """One product feature and whether it is currently available."""

    key: str = Field(min_length=1)
    enabled: bool
    description: str = Field(min_length=1)
    availability_reason: CapabilityReason | None = None


class CapabilitiesResponse(BaseModel):
    """Capabilities contract used by the product shell to render availability."""

    subscription_plan: SubscriptionPlan
    max_execution_tier: ExecutionTier
    default_mode: UserFacingMode
    manual_mode_override_allowed: bool
    modes: list[ModeCapabilityResponse]
    features: list[FeatureCapabilityResponse]
