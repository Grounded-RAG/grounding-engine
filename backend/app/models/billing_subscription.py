"""BillingSubscription persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import BillingSubscriptionStatus, SubscriptionPlan, sqlalchemy_enum


class BillingSubscription(Base):
    """Tracks the active billing subscription for one tenant."""

    __tablename__ = "billing_subscriptions"
    __table_args__ = (
        Index("ix_billing_subscriptions_tenant_id", "tenant_id"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        sqlalchemy_enum(SubscriptionPlan, name="subscriptionplan"),
        nullable=False,
        default=SubscriptionPlan.FREE,
    )
    status: Mapped[BillingSubscriptionStatus] = mapped_column(
        sqlalchemy_enum(BillingSubscriptionStatus, name="billingsubscriptionstatus"),
        nullable=False,
        default=BillingSubscriptionStatus.ACTIVE,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
