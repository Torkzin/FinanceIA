from datetime import date
from decimal import Decimal

from app.db.models import CostCenter, Invoice, Supplier
from app.db.models.enums import InvoiceStatus
from app.db.seed import build_invoices, stable_id


def test_company_owned_tables_have_tenant_constraints() -> None:
    supplier_constraints = {constraint.name for constraint in Supplier.__table__.constraints}
    cost_center_constraints = {constraint.name for constraint in CostCenter.__table__.constraints}
    invoice_constraints = {constraint.name for constraint in Invoice.__table__.constraints}

    assert "uq_suppliers_company_id_document_number" in supplier_constraints
    assert "uq_cost_centers_company_id_code" in cost_center_constraints
    assert "uq_invoices_company_id_supplier_id_invoice_number" in invoice_constraints


def test_demo_invoice_factory_is_deterministic_and_includes_overdue_data() -> None:
    company_id = stable_id("test/company")
    suppliers = [
        Supplier(
            id=stable_id(f"test/supplier/{index}"),
            company_id=company_id,
            name=f"Supplier {index}",
            document_number=f"DOC-{index}",
        )
        for index in range(20)
    ]
    cost_centers = [
        CostCenter(
            id=stable_id(f"test/cost-center/{index}"),
            company_id=company_id,
            name=f"Cost center {index}",
            code=f"CC{index}",
        )
        for index in range(5)
    ]

    first = build_invoices(company_id, suppliers, cost_centers, date(2026, 9, 30))
    second = build_invoices(company_id, suppliers, cost_centers, date(2026, 9, 30))

    assert len(first) == 100
    assert [invoice.amount for invoice in first] == [invoice.amount for invoice in second]
    assert any(invoice.status == InvoiceStatus.OVERDUE for invoice in first)
    assert all(invoice.amount > Decimal("0") for invoice in first)
