from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import CostCenter, User
from app.db.models.enums import UserRole
from app.schemas.cost_center import (
    CostCenterCreate,
    CostCenterListResponse,
    CostCenterResponse,
    CostCenterUpdate,
)
from app.services.financial_records import get_cost_center_or_404

router = APIRouter()
FinanceWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


@router.get("", response_model=CostCenterListResponse)
async def list_cost_centers(
    current_user: CurrentUser,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> CostCenterListResponse:
    filters = [CostCenter.company_id == current_user.company_id]
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(CostCenter.name.ilike(term), CostCenter.code.ilike(term)))
    total = await session.scalar(select(func.count(CostCenter.id)).where(*filters))
    cost_centers = await session.scalars(
        select(CostCenter)
        .where(*filters)
        .order_by(CostCenter.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return CostCenterListResponse(
        items=[CostCenterResponse.model_validate(item) for item in cost_centers],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    payload: CostCenterCreate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> CostCenterResponse:
    values = payload.model_dump()
    values["code"] = payload.code.upper()
    cost_center = CostCenter(company_id=writer.company_id, **values)
    session.add(cost_center)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Cost center code already exists") from exc
    await session.refresh(cost_center)
    return CostCenterResponse.model_validate(cost_center)


@router.get("/{cost_center_id}", response_model=CostCenterResponse)
async def get_cost_center(
    cost_center_id: UUID, current_user: CurrentUser, session: SessionDependency
) -> CostCenterResponse:
    item = await get_cost_center_or_404(session, current_user.company_id, cost_center_id)
    return CostCenterResponse.model_validate(item)


@router.patch("/{cost_center_id}", response_model=CostCenterResponse)
async def update_cost_center(
    cost_center_id: UUID,
    payload: CostCenterUpdate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> CostCenterResponse:
    item = await get_cost_center_or_404(session, writer.company_id, cost_center_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("code"):
        values["code"] = values["code"].upper()
    for field, value in values.items():
        setattr(item, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Cost center code already exists") from exc
    await session.refresh(item)
    return CostCenterResponse.model_validate(item)


@router.delete("/{cost_center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(
    cost_center_id: UUID,
    writer: FinanceWriter,
    session: SessionDependency,
) -> Response:
    item = await get_cost_center_or_404(session, writer.company_id, cost_center_id)
    await session.delete(item)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
