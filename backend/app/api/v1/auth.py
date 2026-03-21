"""Authentication routes."""

from fastapi import APIRouter, Depends

from app.api.deps import TenantContext, get_tenant_context
from app.schemas.auth import AuthSmokeResponse

router = APIRouter()


@router.get("/auth/smoke", response_model=AuthSmokeResponse)
async def auth_smoke(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> AuthSmokeResponse:
    """Return a small authenticated response proving tenant resolution."""

    return AuthSmokeResponse(
        status="authenticated",
        tenant_id=tenant_context.tenant_id,
        tenant_name=tenant_context.tenant_name,
        subscription_plan=tenant_context.subscription_plan,
        max_execution_tier=tenant_context.max_execution_tier,
        api_key_id=tenant_context.api_key_id,
        api_key_label=tenant_context.api_key_label,
    )
