"""Standard query routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.models import ExecutionTier
from app.schemas.query import GroundedAnswerResponse, QueryRequest
from app.services.query import (
    QueryServiceError,
    execute_standard_query,
    process_async_verified_query,
    queue_async_verified_query,
)


router = APIRouter()


@router.post("/query", response_model=GroundedAnswerResponse)
async def query_documents(
    query_request: QueryRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> GroundedAnswerResponse:
    """Run the Phase 1 Standard query path for one tenant namespace."""

    try:
        if query_request.prefer_async and query_request.requested_tier is ExecutionTier.CRITICAL:
            result = await queue_async_verified_query(
                session=session,
                tenant_context=tenant_context,
                query_request=query_request,
            )
            background_tasks.add_task(
                process_async_verified_query,
                trace_id=result.trace_id,
                tenant_context=tenant_context,
                query_request=query_request,
            )
            response.status_code = status.HTTP_202_ACCEPTED
            response.headers["X-Run-Id"] = str(result.trace_id)
            response.headers["X-Trace-Id"] = str(result.trace_id)
            return result.response
        result = await execute_standard_query(
            session=session,
            tenant_context=tenant_context,
            query_request=query_request,
        )
    except QueryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    response.headers["X-Trace-Id"] = str(result.trace_id)
    return result.response
