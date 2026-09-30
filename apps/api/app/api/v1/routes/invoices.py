from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import CurrentUser, SessionDependency, require_roles
from app.db.models import Invoice, User
from app.db.models.enums import UserRole
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services.financial_records import (
    get_invoice_or_404,
    validate_invoice_references,
)

router = APIRouter()
FinanceWriter = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.FINANCE))]


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    current_user: CurrentUser,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    invoice_status: Annotated[str | None, Query(alias="status")] = None,
    supplier_id: UUID | None = None,
    cost_center_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> InvoiceListResponse:
    filters = [Invoice.company_id == current_user.company_id]
    if invoice_status:
        filters.append(Invoice.status == invoice_status)
    if supplier_id:
        filters.append(Invoice.supplier_id == supplier_id)
    if cost_center_id:
        filters.append(Invoice.cost_center_id == cost_center_id)
    if date_from:
        filters.append(Invoice.issue_date >= date_from)
    if date_to:
        filters.append(Invoice.issue_date <= date_to)

    total = await session.scalar(select(func.count(Invoice.id)).where(*filters))
    invoices = await session.scalars(
        select(Invoice)
        .where(*filters)
        .order_by(Invoice.due_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(item) for item in invoices],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> InvoiceResponse:
    await validate_invoice_references(
        session, writer.company_id, payload.supplier_id, payload.cost_center_id
    )
    invoice = Invoice(company_id=writer.company_id, **payload.model_dump())
    session.add(invoice)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Invoice already exists or is invalid") from exc
    await session.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID, current_user: CurrentUser, session: SessionDependency
) -> InvoiceResponse:
    invoice = await get_invoice_or_404(session, current_user.company_id, invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    writer: FinanceWriter,
    session: SessionDependency,
) -> InvoiceResponse:
    invoice = await get_invoice_or_404(session, writer.company_id, invoice_id)
    values = payload.model_dump(exclude_unset=True)
    supplier_id = values.get("supplier_id", invoice.supplier_id)
    cost_center_id = values.get("cost_center_id", invoice.cost_center_id)
    await validate_invoice_references(session, writer.company_id, supplier_id, cost_center_id)
    issue_date = values.get("issue_date", invoice.issue_date)
    due_date = values.get("due_date", invoice.due_date)
    if due_date < issue_date:
        raise HTTPException(status_code=422, detail="due_date must be on or after issue_date")
    for field, value in values.items():
        setattr(invoice, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Invoice already exists or is invalid") from exc
    await session.refresh(invoice)
    return InvoiceResponse.model_validate(invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    writer: FinanceWriter,
    session: SessionDependency,
) -> Response:
    invoice = await get_invoice_or_404(session, writer.company_id, invoice_id)
    await session.delete(invoice)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
