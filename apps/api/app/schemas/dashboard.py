from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Metric(BaseModel):
    count: int
    amount: Decimal


class BreakdownItem(BaseModel):
    label: str
    amount: Decimal
    count: int


class MonthlyTotal(BaseModel):
    month: date
    amount: Decimal


class UpcomingInvoice(BaseModel):
    id: str
    invoice_number: str
    supplier_name: str
    due_date: date
    amount: Decimal


class DashboardResponse(BaseModel):
    month_spend: Decimal
    pending: Metric
    overdue: Metric
    upcoming: list[UpcomingInvoice]
    by_category: list[BreakdownItem]
    by_cost_center: list[BreakdownItem]
    top_suppliers: list[BreakdownItem]
    monthly_evolution: list[MonthlyTotal]
    anomaly_count: int
    insights: list[str]
