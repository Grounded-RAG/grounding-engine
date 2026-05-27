"""Invitation acceptance routes."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.models.enums import WorkspaceMemberStatus
from app.models.workspace_member import WorkspaceMember
from app.schemas.team_members import TeamMemberResponse

router = APIRouter()


@router.post(
    "/invitations/{token}/accept",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_invitation_route(
    token: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> TeamMemberResponse:
    """Accept one pending workspace invitation."""

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.tenant_id == tenant_context.tenant_id,
            WorkspaceMember.invitation_token_hash == token_hash,
            WorkspaceMember.status == WorkspaceMemberStatus.PENDING,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already accepted.",
        )

    member.status = WorkspaceMemberStatus.ACTIVE
    member.joined_at = datetime.now(UTC)
    member.invitation_token_hash = None

    await session.commit()
    await session.refresh(member)
    return TeamMemberResponse.model_validate(member)
