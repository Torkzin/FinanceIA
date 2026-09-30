from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import Supplier, User
from app.db.models.enums import UserRole
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.financial_records import get_supplier_or_404

router = APIRouter()
FinanceWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    current_user: CurrentUser,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    supplier_status: Annotated[str | None, Query(alias="status")] = None,
) -> SupplierListResponse:
    filters = [Supplier.company_id == current_user.company_id]
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Supplier.name.ilike(term), Supplier.document_number.ilike(term)))
    if supplier_status:
        filters.append(Supplier.status == supplier_status)

    total = await session.scalar(select(func.count(Supplier.id)).where(*filters))
    suppliers = await session.scalars(
        select(Supplier)
        .where(*filters)
        .order_by(Supplier.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return SupplierListResponse(
        items=[SupplierResponse.model_validate(item) for item in suppliers],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> SupplierResponse:
    supplier = Supplier(company_id=writer.company_id, **payload.model_dump(mode="json"))
    session.add(supplier)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Supplier document already exists") from exc
    await session.refresh(supplier)
    return SupplierResponse.model_validate(supplier)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID, current_user: CurrentUser, session: SessionDependency
) -> SupplierResponse:
    supplier = await get_supplier_or_404(session, current_user.company_id, supplier_id)
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> SupplierResponse:
    supplier = await get_supplier_or_404(session, writer.company_id, supplier_id)
    for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(supplier, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Supplier document already exists") from exc
    await session.refresh(supplier)
    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    writer: FinanceWriter,
    session: SessionDependency,
) -> Response:
    supplier = await get_supplier_or_404(session, writer.company_id, supplier_id)
    await session.delete(supplier)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Supplier cannot be deleted while invoices reference it",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
