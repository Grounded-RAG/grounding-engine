"""Product capability resolution for the current Grounded backend state."""

from __future__ import annotations

from app.api.deps import TenantContext
from app.models.enums import ExecutionTier, SubscriptionPlan, UserFacingMode
from app.schemas.capabilities import (
    CapabilitiesResponse,
    FeatureCapabilityResponse,
    ModeCapabilityResponse,
)


_MODE_LABELS: dict[UserFacingMode, str] = {
    UserFacingMode.AUTO: "Auto",
    UserFacingMode.INSTANT: "Instant",
    UserFacingMode.THINKING: "Thinking",
    UserFacingMode.VERIFIED: "Verified",
}

_MODE_DESCRIPTIONS: dict[UserFacingMode, str] = {
    UserFacingMode.AUTO: "Recommended mode that follows the current Standard path.",
    UserFacingMode.INSTANT: "Fast grounded answers for everyday document questions.",
    UserFacingMode.THINKING: "Deeper retrieval for harder questions.",
    UserFacingMode.VERIFIED: "Highest-assurance path for sensitive work.",
}

_PLAN_MODE_ACCESS: dict[SubscriptionPlan, set[UserFacingMode]] = {
    SubscriptionPlan.FREE: {
        UserFacingMode.AUTO,
        UserFacingMode.INSTANT,
    },
    SubscriptionPlan.PRO: {
        UserFacingMode.AUTO,
        UserFacingMode.INSTANT,
        UserFacingMode.THINKING,
    },
    SubscriptionPlan.BUSINESS: set(UserFacingMode),
    SubscriptionPlan.ENTERPRISE: set(UserFacingMode),
}

_MODE_BACKING_TIERS: dict[UserFacingMode, ExecutionTier | None] = {
    UserFacingMode.AUTO: None,
    UserFacingMode.INSTANT: ExecutionTier.STANDARD,
    UserFacingMode.THINKING: ExecutionTier.ENTERPRISE,
    UserFacingMode.VERIFIED: ExecutionTier.CRITICAL,
}

_IMPLEMENTED_MODES: set[UserFacingMode] = {
    UserFacingMode.AUTO,
    UserFacingMode.INSTANT,
}

_TIER_RANK: dict[ExecutionTier, int] = {
    ExecutionTier.STANDARD: 1,
    ExecutionTier.ENTERPRISE: 2,
    ExecutionTier.CRITICAL: 3,
}

_PRODUCT_FEATURES: tuple[tuple[str, bool, str, str | None], ...] = (
    (
        "document_upload",
        True,
        "Upload supported files and start Standard ingestion.",
        None,
    ),
    (
        "ingestion_jobs",
        True,
        "Poll ingestion status until documents are indexed.",
        None,
    ),
    (
        "grounded_query",
        True,
        "Query one dataset through the current Standard grounded path.",
        None,
    ),
    (
        "workspaces",
        False,
        "Workspace APIs for the product shell.",
        "coming_soon",
    ),
    (
        "datasets",
        False,
        "Dataset management APIs built on top of namespaces.",
        "coming_soon",
    ),
    (
        "agents",
        False,
        "Reusable agents attached to one or more datasets.",
        "coming_soon",
    ),
    (
        "conversations",
        False,
        "Conversation history and message persistence inside agents.",
        "coming_soon",
    ),
    (
        "run_history",
        False,
        "Run inspection and answer history over persisted query traces.",
        "coming_soon",
    ),
    (
        "dashboard",
        False,
        "Dashboard summary and recent activity APIs.",
        "coming_soon",
    ),
    (
        "api_key_management",
        False,
        "Managed API key creation and revocation endpoints.",
        "coming_soon",
    ),
)


def _supports_tier(
    *,
    tenant_max_tier: ExecutionTier,
    required_tier: ExecutionTier | None,
) -> bool:
    """Return whether the tenant can reach the mode's backing execution tier."""

    if required_tier is None:
        return True
    return _TIER_RANK[tenant_max_tier] >= _TIER_RANK[required_tier]


def _build_mode_capability(
    *,
    mode: UserFacingMode,
    tenant_context: TenantContext,
) -> ModeCapabilityResponse:
    """Build one user-facing mode capability from plan and implementation state."""

    plan_modes = _PLAN_MODE_ACCESS[tenant_context.subscription_plan]
    backing_tier = _MODE_BACKING_TIERS[mode]

    if mode not in plan_modes:
        enabled = False
        availability_reason = "plan_restricted"
    elif not _supports_tier(
        tenant_max_tier=tenant_context.max_execution_tier,
        required_tier=backing_tier,
    ):
        enabled = False
        availability_reason = "tier_restricted"
    elif mode not in _IMPLEMENTED_MODES:
        enabled = False
        availability_reason = "coming_soon"
    else:
        enabled = True
        availability_reason = None

    return ModeCapabilityResponse(
        mode=mode,
        label=_MODE_LABELS[mode],
        enabled=enabled,
        backing_tier=backing_tier,
        description=_MODE_DESCRIPTIONS[mode],
        availability_reason=availability_reason,
    )


def _build_feature_capabilities() -> list[FeatureCapabilityResponse]:
    """Return the current product capability list for the backend."""

    return [
        FeatureCapabilityResponse(
            key=key,
            enabled=enabled,
            description=description,
            availability_reason=availability_reason,
        )
        for key, enabled, description, availability_reason in _PRODUCT_FEATURES
    ]


def build_capabilities_response(
    *,
    tenant_context: TenantContext,
) -> CapabilitiesResponse:
    """Return the current product and mode availability for one tenant."""

    ordered_modes = [
        UserFacingMode.AUTO,
        UserFacingMode.INSTANT,
        UserFacingMode.THINKING,
        UserFacingMode.VERIFIED,
    ]

    return CapabilitiesResponse(
        subscription_plan=tenant_context.subscription_plan,
        max_execution_tier=tenant_context.max_execution_tier,
        default_mode=UserFacingMode.AUTO,
        manual_mode_override_allowed=True,
        modes=[
            _build_mode_capability(mode=mode, tenant_context=tenant_context)
            for mode in ordered_modes
        ],
        features=_build_feature_capabilities(),
    )
