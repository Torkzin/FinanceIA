from datetime import date
from decimal import Decimal

import pytest

from app.integrations.erp import MockERPAdapter, validate_snapshot
from app.main import app
from app.schemas.erp import ERPInvoice, ERPSnapshot, ERPVendor


@pytest.mark.asyncio
async def test_mock_erp_exposes_valid_replaceable_snapshot() -> None:
    snapshot = await MockERPAdapter().fetch_snapshot()

    assert snapshot.source == "mock-erp-v1"
    assert len(snapshot.vendors) == 4
    assert len(snapshot.invoices) == 5
    assert {invoice.vendor_external_id for invoice in snapshot.invoices} <= {
        vendor.external_id for vendor in snapshot.vendors
    }
    assert all(invoice.amount > 0 for invoice in snapshot.invoices)


def test_snapshot_rejects_unknown_vendor_reference() -> None:
    snapshot = ERPSnapshot(
        source="invalid",
        generated_at="2026-09-30T12:00:00Z",
        vendors=[
            ERPVendor(
                external_id="V-1",
                name="Fornecedor de teste",
                document_number="DOC-0001",
            )
        ],
        invoices=[
            ERPInvoice(
                external_id="I-1",
                vendor_external_id="missing",
                invoice_number="INV-1",
                description="Fatura inválida",
                category="Test",
                issue_date=date(2026, 9, 1),
                due_date=date(2026, 9, 10),
                amount=Decimal("10.00"),
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown vendors"):
        validate_snapshot(snapshot)


def test_phase_12_routes_are_registered() -> None:
    paths = set(app.openapi()["paths"])

    assert "/external-api/vendors" in paths
    assert "/external-api/invoices" in paths
    assert "/api/v1/integrations/erp/preview" in paths
    assert "/api/v1/integrations/erp/sync" in paths
    assert "/api/v1/integrations/erp/runs" in paths
