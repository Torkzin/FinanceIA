from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from app.schemas.erp import ERPInvoice, ERPSnapshot, ERPVendor


class ERPAdapter(Protocol):
    name: str

    async def fetch_snapshot(self) -> ERPSnapshot: ...


MOCK_VENDORS = [
    ERPVendor(
        external_id="VEN-1001",
        name="Nexa Office Suprimentos",
        document_number="90.111.222/0001-30",
        email="financeiro@nexa-office.demo",
        category="Office",
    ),
    ERPVendor(
        external_id="VEN-1002",
        name="Atlas Segurança Digital",
        document_number="90.111.222/0002-10",
        email="billing@atlas-security.demo",
        category="Software",
    ),
    ERPVendor(
        external_id="VEN-1003",
        name="Vertex Logística Integrada",
        document_number="90.111.222/0003-00",
        email="contas@vertex-log.demo",
        category="Logistics",
    ),
    ERPVendor(
        external_id="VEN-1004",
        name="Lumen Energia Corporativa",
        document_number="90.111.222/0004-91",
        email="faturamento@lumen-energy.demo",
        category="Utilities",
    ),
]

MOCK_INVOICES = [
    ERPInvoice(
        external_id="INV-ERP-5001",
        vendor_external_id="VEN-1001",
        cost_center_code="OPS",
        invoice_number="ERP-2026-5001",
        description="Materiais de escritório do trimestre",
        category="Office",
        issue_date=date(2026, 9, 25),
        due_date=date(2026, 10, 10),
        amount=Decimal("2840.50"),
        status="approved",
    ),
    ERPInvoice(
        external_id="INV-ERP-5002",
        vendor_external_id="VEN-1002",
        cost_center_code="TEC",
        invoice_number="ERP-2026-5002",
        description="Licenças de segurança e monitoramento",
        category="Software",
        issue_date=date(2026, 9, 26),
        due_date=date(2026, 10, 15),
        amount=Decimal("12750.00"),
        status="pending",
    ),
    ERPInvoice(
        external_id="INV-ERP-5003",
        vendor_external_id="VEN-1003",
        cost_center_code="OPS",
        invoice_number="ERP-2026-5003",
        description="Operação logística regional",
        category="Logistics",
        issue_date=date(2026, 9, 28),
        due_date=date(2026, 10, 20),
        amount=Decimal("6380.90"),
        status="approved",
    ),
    ERPInvoice(
        external_id="INV-ERP-5004",
        vendor_external_id="VEN-1004",
        cost_center_code="OPS",
        invoice_number="ERP-2026-5004",
        description="Consumo de energia da unidade administrativa",
        category="Utilities",
        issue_date=date(2026, 9, 29),
        due_date=date(2026, 10, 8),
        amount=Decimal("4195.75"),
        status="pending",
    ),
    ERPInvoice(
        external_id="INV-ERP-5005",
        vendor_external_id="VEN-1002",
        cost_center_code="TEC",
        invoice_number="ERP-2026-5005",
        description="Avaliação anual de vulnerabilidades",
        category="Professional Services",
        issue_date=date(2026, 9, 30),
        due_date=date(2026, 10, 30),
        amount=Decimal("8900.00"),
        status="pending",
    ),
]


def validate_snapshot(snapshot: ERPSnapshot) -> None:
    vendor_ids = [vendor.external_id for vendor in snapshot.vendors]
    invoice_ids = [invoice.external_id for invoice in snapshot.invoices]
    if len(vendor_ids) != len(set(vendor_ids)):
        raise ValueError("ERP snapshot contains duplicate vendor IDs")
    if len(invoice_ids) != len(set(invoice_ids)):
        raise ValueError("ERP snapshot contains duplicate invoice IDs")
    known_vendors = set(vendor_ids)
    if missing := {
        invoice.vendor_external_id
        for invoice in snapshot.invoices
        if invoice.vendor_external_id not in known_vendors
    }:
        raise ValueError(f"ERP invoices reference unknown vendors: {', '.join(sorted(missing))}")


class MockERPAdapter:
    name = "mock-erp-v1"

    async def fetch_snapshot(self) -> ERPSnapshot:
        snapshot = ERPSnapshot(
            source=self.name,
            generated_at=datetime.now(UTC),
            vendors=[vendor.model_copy(deep=True) for vendor in MOCK_VENDORS],
            invoices=[invoice.model_copy(deep=True) for invoice in MOCK_INVOICES],
        )
        validate_snapshot(snapshot)
        return snapshot
