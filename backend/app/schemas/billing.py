"""Billing API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import BillingSubscriptionStatus, SubscriptionPlan

_PLAN_FEATURES: dict[SubscriptionPlan, list[str]] = {
    SubscriptionPlan.FREE: [
        "Up to 3 agents",
        "100 queries / month",
        "1 namespace",
        "Community support",
    ],
    SubscriptionPlan.PRO: [
        "Up to 20 agents",
        "10,000 queries / month",
        "10 namespaces",
        "Email support",
        "Thinking mode",
    ],
    SubscriptionPlan.BUSINESS: [
        "Unlimited agents",
        "100,000 queries / month",
        "Unlimited namespaces",
        "Priority support",
        "All execution modes",
        "Team members",
        "Audit logs",
    ],
    SubscriptionPlan.ENTERPRISE: [
        "Everything in Business",
        "Custom query limits",
        "SSO / SAML",
        "Role-based access",
        "SLA guarantee",
        "Dedicated support",
    ],
}


class BillingSubscriptionResponse(BaseModel):
    """Billing subscription resource returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    subscription_id: UUID
    plan: SubscriptionPlan
    status: BillingSubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    features: list[str]

    @classmethod
    def from_model(cls, sub: object) -> "BillingSubscriptionResponse":
        from app.models.billing_subscription import BillingSubscription  # avoid circular

        assert isinstance(sub, BillingSubscription)
        return cls(
            subscription_id=sub.subscription_id,
            plan=sub.plan,
            status=sub.status,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            features=_PLAN_FEATURES.get(sub.plan, []),
        )


class BillingPortalResponse(BaseModel):
    """Response for Stripe billing portal redirect (stub)."""

    portal_url: str | None
    message: str
