from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import Anomaly, Invoice, Supplier, User
from app.db.models.enums import UserRole
from app.schemas.anomaly import (
    AnomalyAnalysisResponse,
    AnomalyDetectionResponse,
    AnomalyListResponse,
    AnomalyResponse,
)
from app.services.anomalies import analyze_anomaly, scan_company_anomalies

router = APIRouter()
AnomalyWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    current_user: CurrentUser,
    session: SessionDependency,
    severity: Annotated[Literal["low", "medium", "high"] | None, Query()] = None,
    anomaly_status: Annotated[
        Literal["open", "reviewed", "dismissed"] | None, Query(alias="status")
    ] = None,
) -> AnomalyListResponse:
    filters = [Anomaly.company_id == current_user.company_id]
    if severity:
        filters.append(Anomaly.severity == severity)
    if anomaly_status:
        filters.append(Anomaly.status == anomaly_status)
    total = await session.scalar(select(func.count(Anomaly.id)).where(*filters))
    anomalies = await session.scalars(
        select(Anomaly)
        .where(*filters)
        .order_by(
            Anomaly.detected_at.desc(),
            Anomaly.severity.desc(),
        )
        .limit(200)
    )
    return AnomalyListResponse(
        items=[AnomalyResponse.model_validate(item) for item in anomalies], total=total or 0
    )


@router.post("/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    writer: AnomalyWriter, session: SessionDependency
) -> AnomalyDetectionResponse:
    return await scan_company_anomalies(session, writer.company_id)


@router.post("/{anomaly_id}/analyze", response_model=AnomalyAnalysisResponse)
async def generate_anomaly_analysis(
    anomaly_id: UUID,
    current_user: CurrentUser,
    session: SessionDependency,
) -> AnomalyAnalysisResponse:
    row = (
        await session.execute(
            select(Anomaly, Invoice, Supplier.name)
            .join(Invoice, Invoice.id == Anomaly.related_invoice_id)
            .join(Supplier, Supplier.id == Invoice.supplier_id)
            .where(
                Anomaly.id == anomaly_id,
                Anomaly.company_id == current_user.company_id,
                Invoice.company_id == current_user.company_id,
                Supplier.company_id == current_user.company_id,
            )
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anomaly, invoice, supplier_name = row
    try:
        return await analyze_anomaly(session, anomaly, invoice, supplier_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
