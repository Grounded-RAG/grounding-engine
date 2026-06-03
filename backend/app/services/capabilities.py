"""Product capability resolution for the current Grounded backend state."""

from __future__ import annotations

from app.api.deps import TenantContext
from app.models.enums import ExecutionTier, UserFacingMode
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

_MODE_BACKING_TIERS: dict[UserFacingMode, ExecutionTier | None] = {
    UserFacingMode.AUTO: None,
    UserFacingMode.INSTANT: ExecutionTier.STANDARD,
    UserFacingMode.THINKING: ExecutionTier.ENTERPRISE,
    UserFacingMode.VERIFIED: ExecutionTier.CRITICAL,
}

_ORDERED_MODES: tuple[UserFacingMode, ...] = (
    UserFacingMode.AUTO,
    UserFacingMode.INSTANT,
    UserFacingMode.THINKING,
    UserFacingMode.VERIFIED,
)

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
        True,
        "Workspace APIs for the product shell.",
        None,
    ),
    (
        "datasets",
        True,
        "Dataset management APIs built on top of namespaces.",
        None,
    ),
    (
        "agents",
        True,
        "Reusable agents attached to one or more datasets.",
        None,
    ),
    (
        "agent_chat",
        True,
        "Grounded agent chat over one attached dataset through the current Standard path.",
        None,
    ),
    (
        "conversations",
        True,
        "Conversation threads and stored message history inside agents.",
        None,
    ),
    (
        "run_history",
        True,
        "Run inspection and answer history over persisted query traces.",
        None,
    ),
    (
        "dashboard",
        True,
        "Dashboard summary and recent activity APIs.",
        None,
    ),
    (
        "api_key_management",
        True,
        "Managed API key creation and revocation endpoints.",
        None,
    ),
)


def get_current_supported_modes() -> set[UserFacingMode]:
    """Return the currently implemented product-facing modes."""

    return set(_ORDERED_MODES)


def _build_mode_capability(
    *,
    mode: UserFacingMode,
    tenant_context: TenantContext,
) -> ModeCapabilityResponse:
    """Build one user-facing mode capability."""

    backing_tier = _MODE_BACKING_TIERS[mode]

    return ModeCapabilityResponse(
        mode=mode,
        label=_MODE_LABELS[mode],
        enabled=True,
        backing_tier=backing_tier,
        description=_MODE_DESCRIPTIONS[mode],
        availability_reason=None,
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

    return CapabilitiesResponse(
        subscription_plan=tenant_context.subscription_plan,
        max_execution_tier=tenant_context.max_execution_tier,
        default_mode=UserFacingMode.AUTO,
        manual_mode_override_allowed=True,
        modes=[
            _build_mode_capability(mode=mode, tenant_context=tenant_context)
            for mode in _ORDERED_MODES
        ],
        features=_build_feature_capabilities(),
    )
