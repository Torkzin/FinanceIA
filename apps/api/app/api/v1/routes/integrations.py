from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import IntegrationConnection, IntegrationSyncRun, User
from app.db.models.enums import UserRole
from app.integrations.erp import MockERPAdapter
from app.schemas.erp import (
    ERPPreviewResponse,
    ERPSyncResponse,
    ERPSyncRunListResponse,
    ERPSyncRunResponse,
)
from app.services.erp_sync import preview_erp, sync_erp

router = APIRouter()
FinanceWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


@router.get("/erp/preview", response_model=ERPPreviewResponse)
async def get_erp_preview(
    current_user: CurrentUser, session: SessionDependency
) -> ERPPreviewResponse:
    return await preview_erp(session, current_user.company_id, MockERPAdapter())


@router.post("/erp/sync", response_model=ERPSyncResponse)
async def synchronize_erp(
    writer: FinanceWriter, session: SessionDependency
) -> ERPSyncResponse:
    try:
        return await sync_erp(session, writer.company_id, MockERPAdapter())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ERP synchronization failed; the failed run was recorded",
        ) from exc


@router.get("/erp/runs", response_model=ERPSyncRunListResponse)
async def list_erp_sync_runs(
    current_user: CurrentUser,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> ERPSyncRunListResponse:
    filters = [
        IntegrationSyncRun.company_id == current_user.company_id,
        IntegrationConnection.provider == "erp",
    ]
    total = await session.scalar(
        select(func.count(IntegrationSyncRun.id))
        .join(IntegrationConnection)
        .where(*filters)
    )
    runs = await session.scalars(
        select(IntegrationSyncRun)
        .join(IntegrationConnection)
        .where(*filters)
        .order_by(IntegrationSyncRun.started_at.desc())
        .limit(limit)
    )
    return ERPSyncRunListResponse(
        items=[
            ERPSyncRunResponse(
                id=run.id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                summary=run.summary,
                error_message=run.error_message,
            )
            for run in runs
        ],
        total=total or 0,
    )
