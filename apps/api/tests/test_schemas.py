from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.invoice import InvoiceCreate


def test_invoice_rejects_due_date_before_issue_date() -> None:
    with pytest.raises(ValidationError):
        InvoiceCreate(
            supplier_id="1fdf037f-75df-43e2-b96d-606a9ebf703a",
            invoice_number="INV-1",
            description="Test invoice",
            category="Software",
            issue_date=date(2026, 9, 20),
            due_date=date(2026, 9, 19),
            amount="100.00",
        )


def test_invoice_normalizes_currency() -> None:
    invoice = InvoiceCreate(
        supplier_id="1fdf037f-75df-43e2-b96d-606a9ebf703a",
        invoice_number="INV-2",
        description="Test invoice",
        category="Software",
        issue_date=date(2026, 9, 20),
        due_date=date(2026, 9, 30),
        amount="100.00",
        currency="brl",
    )

    assert invoice.currency == "BRL"
