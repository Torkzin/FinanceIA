from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CostCenter, Invoice, Supplier


def decimal_value(value: Decimal | None) -> float:
    return float(value or 0)


async def get_upcoming_payments(
    session: AsyncSession, company_id: UUID, days: int = 15
) -> dict[str, Any]:
    days = max(1, min(days, 90))
    today = date.today()
    end_date = today + timedelta(days=days)
    rows = await session.execute(
        select(Invoice, Supplier.name)
        .join(Supplier, Invoice.supplier_id == Supplier.id)
        .where(
            Invoice.company_id == company_id,
            Invoice.due_date.between(today, end_date),
            Invoice.status.in_(["pending", "approved"]),
        )
        .order_by(Invoice.due_date)
        .limit(50)
    )
    items = [
        {
            "invoice_number": invoice.invoice_number,
            "supplier": supplier,
            "due_date": invoice.due_date.isoformat(),
            "amount": decimal_value(invoice.amount),
        }
        for invoice, supplier in rows
    ]
    return {
        "days": days,
        "count": len(items),
        "total": sum(item["amount"] for item in items),
        "items": items,
    }


async def get_overdue_invoices(session: AsyncSession, company_id: UUID) -> dict[str, Any]:
    rows = await session.execute(
        select(Invoice, Supplier.name)
        .join(Supplier, Invoice.supplier_id == Supplier.id)
        .where(
            Invoice.company_id == company_id,
            Invoice.due_date < date.today(),
            Invoice.status.in_(["pending", "approved", "overdue"]),
        )
        .order_by(Invoice.due_date)
        .limit(50)
    )
    items = [
        {
            "invoice_number": invoice.invoice_number,
            "supplier": supplier,
            "due_date": invoice.due_date.isoformat(),
            "amount": decimal_value(invoice.amount),
        }
        for invoice, supplier in rows
    ]
    return {
        "count": len(items),
        "total": sum(item["amount"] for item in items),
        "items": items,
    }


async def get_expenses_by_period(
    session: AsyncSession,
    company_id: UUID,
    date_from: date,
    date_to: date,
    category: str | None = None,
) -> dict[str, Any]:
    if date_to < date_from or (date_to - date_from).days > 366:
        raise ValueError("The requested period must be between 0 and 366 days")
    filters = [
        Invoice.company_id == company_id,
        Invoice.issue_date.between(date_from, date_to),
        Invoice.status != "rejected",
    ]
    if category:
        normalized_category = category.strip().lower()
        if normalized_category in {"tecnologia", "technology"}:
            filters.append(
                Invoice.category.in_(["Cloud", "Software", "Telecom", "Technology", "Tecnologia"])
            )
        else:
            filters.append(Invoice.category.ilike(f"%{category.strip()}%"))
    count, total = (
        await session.execute(
            select(func.count(Invoice.id), func.sum(Invoice.amount)).where(*filters)
        )
    ).one()
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "category": category,
        "count": count,
        "total": decimal_value(total),
    }


async def get_top_suppliers(
    session: AsyncSession, company_id: UUID, limit: int = 5
) -> dict[str, Any]:
    limit = max(1, min(limit, 10))
    rows = await session.execute(
        select(Supplier.name, func.count(Invoice.id), func.sum(Invoice.amount))
        .join(Invoice, Invoice.supplier_id == Supplier.id)
        .where(Invoice.company_id == company_id, Invoice.status != "rejected")
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.sum(Invoice.amount).desc())
        .limit(limit)
    )
    return {
        "limit": limit,
        "items": [
            {"supplier": name, "count": count, "total": decimal_value(total)}
            for name, count, total in rows
        ],
    }


async def get_cost_center_summary(session: AsyncSession, company_id: UUID) -> dict[str, Any]:
    rows = await session.execute(
        select(CostCenter.name, func.count(Invoice.id), func.sum(Invoice.amount))
        .join(Invoice, Invoice.cost_center_id == CostCenter.id)
        .where(Invoice.company_id == company_id, Invoice.status != "rejected")
        .group_by(CostCenter.id, CostCenter.name)
        .order_by(func.sum(Invoice.amount).desc())
    )
    return {
        "items": [
            {"cost_center": name, "count": count, "total": decimal_value(total)}
            for name, count, total in rows
        ]
    }


async def compare_monthly_expenses(session: AsyncSession, company_id: UUID) -> dict[str, Any]:
    today = date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    current_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    current = await get_expenses_by_period(session, company_id, current_start, current_end)
    previous = await get_expenses_by_period(session, company_id, previous_start, previous_end)
    difference = current["total"] - previous["total"]
    percentage = difference / previous["total"] * 100 if previous["total"] else None
    return {
        "current": current,
        "previous": previous,
        "difference": difference,
        "percentage_change": percentage,
    }
