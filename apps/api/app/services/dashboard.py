from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CostCenter, Invoice, Supplier
from app.schemas.dashboard import (
    BreakdownItem,
    DashboardResponse,
    Metric,
    MonthlyTotal,
    UpcomingInvoice,
)


def shift_month(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


async def build_dashboard(session: AsyncSession, company_id: UUID) -> DashboardResponse:
    today = datetime.now(UTC).date()
    month_start = today.replace(day=1)
    next_month = shift_month(month_start, 1)
    six_month_start = shift_month(month_start, -5)
    active_status = Invoice.status != "rejected"

    month_spend = await session.scalar(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.company_id == company_id,
            Invoice.issue_date >= month_start,
            Invoice.issue_date < next_month,
            active_status,
        )
    )

    async def metric_for(condition) -> Metric:
        row = (
            await session.execute(
                select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)).where(
                    Invoice.company_id == company_id, condition
                )
            )
        ).one()
        return Metric(count=row[0], amount=row[1])

    pending = await metric_for(Invoice.status.in_(["pending", "approved"]))
    overdue = await metric_for(
        (Invoice.status == "overdue")
        | and_(Invoice.due_date < today, Invoice.status.in_(["pending", "approved"]))
    )

    upcoming_rows = await session.execute(
        select(Invoice, Supplier.name)
        .join(Supplier, Supplier.id == Invoice.supplier_id)
        .where(
            Invoice.company_id == company_id,
            Invoice.status.in_(["pending", "approved"]),
            Invoice.due_date >= today,
            Invoice.due_date <= today + timedelta(days=15),
        )
        .order_by(Invoice.due_date)
        .limit(8)
    )
    upcoming = [
        UpcomingInvoice(
            id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            supplier_name=supplier_name,
            due_date=invoice.due_date,
            amount=invoice.amount,
        )
        for invoice, supplier_name in upcoming_rows
    ]

    async def breakdown(label_column, join_target=None) -> list[BreakdownItem]:
        query = select(
            label_column,
            func.coalesce(func.sum(Invoice.amount), 0),
            func.count(Invoice.id),
        )
        if join_target is not None:
            query = query.join(join_target)
        rows = await session.execute(
            query.where(
                Invoice.company_id == company_id,
                Invoice.issue_date >= six_month_start,
                active_status,
            )
            .group_by(label_column)
            .order_by(func.sum(Invoice.amount).desc())
            .limit(8)
        )
        return [
            BreakdownItem(label=row[0] or "Unallocated", amount=row[1], count=row[2])
            for row in rows
        ]

    by_category = await breakdown(Invoice.category)
    by_cost_center = await breakdown(CostCenter.name, CostCenter)
    top_suppliers = await breakdown(Supplier.name, Supplier)

    month_expression = func.date_trunc("month", Invoice.issue_date)
    evolution_rows = await session.execute(
        select(month_expression, func.coalesce(func.sum(Invoice.amount), 0))
        .where(
            Invoice.company_id == company_id,
            Invoice.issue_date >= six_month_start,
            active_status,
        )
        .group_by(month_expression)
        .order_by(month_expression)
    )
    monthly_evolution = [MonthlyTotal(month=row[0].date(), amount=row[1]) for row in evolution_rows]

    insights: list[str] = []
    if overdue.count:
        insights.append(f"There are {overdue.count} overdue payments requiring attention.")
    if upcoming:
        insights.append(f"{len(upcoming)} payments are due in the next 15 days.")
    if by_category:
        insights.append(
            f"{by_category[0].label} is the largest expense category in the six-month period."
        )
    if not insights:
        insights.append("No immediate financial exceptions were detected.")

    return DashboardResponse(
        month_spend=Decimal(month_spend),
        pending=pending,
        overdue=overdue,
        upcoming=upcoming,
        by_category=by_category,
        by_cost_center=by_cost_center,
        top_suppliers=top_suppliers,
        monthly_evolution=monthly_evolution,
        anomaly_count=0,
        insights=insights,
    )
