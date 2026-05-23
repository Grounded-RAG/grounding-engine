"""Billing service — subscription lookup and stub portal."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry import get_logger
from app.models.billing_subscription import BillingSubscription
from app.models.enums import BillingSubscriptionStatus, SubscriptionPlan

logger = get_logger("app.billing")


class BillingServiceError(RuntimeError):
    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


async def get_or_create_subscription(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> BillingSubscription:
    result = await session.execute(
        select(BillingSubscription).where(BillingSubscription.tenant_id == tenant_id)
    )
    sub = result.scalar_one_or_none()
    if sub is not None:
        return sub

    sub = BillingSubscription(
        subscription_id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan=SubscriptionPlan.FREE,
        status=BillingSubscriptionStatus.ACTIVE,
    )
    session.add(sub)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise BillingServiceError(
            "Failed to initialise billing subscription.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc
    await session.refresh(sub)
    return sub
