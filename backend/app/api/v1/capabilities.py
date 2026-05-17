"""Capability routes for the product shell."""

from fastapi import APIRouter, Depends

from app.api.deps import TenantContext, get_tenant_context
from app.schemas.capabilities import CapabilitiesResponse
from app.services.capabilities import build_capabilities_response


router = APIRouter()


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> CapabilitiesResponse:
    """Return current product and mode availability for the authenticated tenant."""

    return build_capabilities_response(tenant_context=tenant_context)
