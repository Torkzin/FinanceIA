from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CostCenter, Invoice, Supplier


async def get_supplier_or_404(
    session: AsyncSession, company_id: UUID, supplier_id: UUID
) -> Supplier:
    supplier = await session.scalar(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == company_id)
    )
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


async def get_cost_center_or_404(
    session: AsyncSession, company_id: UUID, cost_center_id: UUID
) -> CostCenter:
    cost_center = await session.scalar(
        select(CostCenter).where(
            CostCenter.id == cost_center_id,
            CostCenter.company_id == company_id,
        )
    )
    if not cost_center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center not found")
    return cost_center


async def get_invoice_or_404(session: AsyncSession, company_id: UUID, invoice_id: UUID) -> Invoice:
    invoice = await session.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.company_id == company_id)
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


async def validate_invoice_references(
    session: AsyncSession,
    company_id: UUID,
    supplier_id: UUID,
    cost_center_id: UUID | None,
) -> None:
    await get_supplier_or_404(session, company_id, supplier_id)
    if cost_center_id:
        await get_cost_center_or_404(session, company_id, cost_center_id)
