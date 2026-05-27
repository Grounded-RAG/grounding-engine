"""Billing routes — subscription info and Stripe portal stub."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.billing import BillingPortalResponse, BillingSubscriptionResponse
from app.services.billing import BillingServiceError, get_or_create_subscription


router = APIRouter()


@router.get("/billing/subscription", response_model=BillingSubscriptionResponse)
async def get_subscription_route(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BillingSubscriptionResponse:
    try:
        sub = await get_or_create_subscription(
            session=session, tenant_id=tenant_context.tenant_id
        )
    except BillingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return BillingSubscriptionResponse.from_model(sub)


@router.post("/billing/portal", response_model=BillingPortalResponse)
async def billing_portal_route(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> BillingPortalResponse:
    """Return a Stripe customer portal URL (stub until Stripe is configured)."""
    return BillingPortalResponse(
        portal_url=None,
        message="Stripe billing portal is not yet configured. Contact support to upgrade your plan.",
    )
